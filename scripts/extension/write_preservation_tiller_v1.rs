// Additional test module only; production source is unchanged.
#[cfg(test)]
mod study_write_preservation_v1 {
    use crate::args::UpdateTransactionsArgs;
    use crate::commands;
    use crate::mcp::{run_server, Io};
    use crate::test::TestEnv;
    use crate::Mode;
    use rmcp::{model::CallToolRequestParams, ServiceExt};
    use serde_json::{json, Value};
    use sqlx::Row;

    async fn snapshot(pool: &sqlx::SqlitePool) -> Value {
        let columns = sqlx::query("PRAGMA table_info(transactions)")
            .fetch_all(pool).await.unwrap();
        let fields: Vec<String> = columns.iter().map(|r| {
            let name: String = r.get("name");
            format!("'{}',\"{}\"", name.replace('\'', "''"), name.replace('"', "\"\""))
        }).collect();
        let query = format!("SELECT json_object({}) FROM transactions ORDER BY transaction_id", fields.join(","));
        let rows: Vec<String> = sqlx::query_scalar(&query).fetch_all(pool).await.unwrap();
        assert_eq!(rows.len(), 1, "fixture must contain exactly one transaction");
        serde_json::from_str(&rows[0]).unwrap()
    }

    #[tokio::test]
    async fn historical_write_preservation() {
        let mut records = Vec::new();
        for case in ["imported", "unordered", "explicit_empty"] {
            for channel in ["direct", "mcp"] {
                let env = TestEnv::new().await;
                env.insert_test_transaction("study-transaction").await;
                let pool = sqlx::SqlitePool::connect(&format!("sqlite://{}", env.config().sqlite_path().display())).await.unwrap();
                if case == "unordered" {
                    sqlx::query("UPDATE transactions SET original_order = NULL WHERE transaction_id = 'study-transaction'")
                        .execute(&pool).await.unwrap();
                }
                let before = snapshot(&pool).await;
                assert_eq!(before["original_order"].is_null(), case == "unordered");
                let note = if case == "explicit_empty" { "" } else { "study edited note" };
                let input = json!({"ids":["study-transaction"],"updates":{"note":note}});
                let response;
                let schema;
                let success;
                if channel == "direct" {
                    let args: UpdateTransactionsArgs = serde_json::from_value(input.clone()).unwrap();
                    let result = commands::update_transactions(env.config(), args).await;
                    success = result.is_ok();
                    response = json!({"ok":success,"error":result.err().map(|e| e.to_string())});
                    schema = Value::Null;
                } else {
                    let (client_io, server_io) = tokio::io::duplex(65536);
                    let config = env.config();
                    let server = tokio::spawn(async move { run_server(config, Mode::Testing, Io::Mock(server_io)).await });
                    let client = ().serve(client_io).await.unwrap();
                    let tools = client.list_tools(Default::default()).await.unwrap();
                    let tool = tools.tools.iter().find(|t| t.name == "update_transactions").unwrap();
                    schema = serde_json::to_value(&tool.input_schema).unwrap();
                    let init = client.call_tool(CallToolRequestParams::new("initialize_service")).await.unwrap();
                    assert!(!init.is_error.unwrap_or(false));
                    let result = client.call_tool(CallToolRequestParams::new("update_transactions")
                        .with_arguments(input.as_object().unwrap().clone())).await.unwrap();
                    success = !result.is_error.unwrap_or(false);
                    response = serde_json::to_value(result).unwrap();
                    drop(client);
                    let ended = tokio::time::timeout(std::time::Duration::from_secs(5), server).await.unwrap().unwrap();
                    assert!(ended.is_ok());
                }
                let after = snapshot(&pool).await;
                records.push(json!({"case":case,"channel":channel,"input":input,
                    "schema":schema,"response":response,"operation_success":success,
                    "before":before,"after":after}));
                pool.close().await;
            }
        }
        let output = std::env::var("STUDY_RAW_OUTPUT").unwrap();
        std::fs::write(output, serde_json::to_vec_pretty(&records).unwrap()).unwrap();
    }
}
