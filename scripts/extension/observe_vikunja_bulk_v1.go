// Study instrumentation added only as a test file to the upstream checkout.
// Exercises production routes/storage using upstream synthetic fixture helpers.
package webtests

import (
 "encoding/json"
 "fmt"
 "net/http"
 "os"
 "path/filepath"
 "testing"

 "code.vikunja.io/api/pkg/db"
 "github.com/stretchr/testify/require"
)

func studyBulkSnapshot(t *testing.T, ids []int) map[string]any {
 t.Helper()
 s := db.NewSession()
 defer s.Close()
 out := map[string]any{}
 for _, id := range ids {
  tables := map[string]string{
   "tasks": "SELECT * FROM tasks WHERE id = ? ORDER BY id",
   "assignees": "SELECT * FROM task_assignees WHERE task_id = ? ORDER BY id",
   "reminders": "SELECT * FROM task_reminders WHERE task_id = ? ORDER BY id",
   "favorites": "SELECT * FROM favorites WHERE entity_id = ? AND kind = 1 ORDER BY user_id",
  }
  entity := map[string]any{}
  for name, query := range tables {
   rows, err := s.QueryInterface(query, id)
   require.NoError(t, err)
   for _, row := range rows {
    for k, value := range row {
     if b, ok := value.([]byte); ok { row[k] = string(b) }
    }
   }
   if rows == nil { rows = []map[string]interface{}{} }
   entity[name] = rows
  }
  out[fmt.Sprint(id)] = entity
 }
 return out
}

func TestStudyBulkPreservationV1(t *testing.T) {
 cases := []struct{name string; ids []int; fields []string; values map[string]any; single bool}{
  {"priority_relations", []int{1,27,30}, []string{"priority"}, map[string]any{"priority":3}, false},
  {"priority_clean", []int{3}, []string{"priority"}, map[string]any{"priority":3}, false},
  {"clear_assignees", []int{30}, []string{"assignees"}, map[string]any{"assignees":[]any{}}, false},
  {"clear_reminders", []int{27}, []string{"reminders"}, map[string]any{"reminders":[]any{}}, false},
  {"clear_favorite", []int{1}, []string{"is_favorite"}, map[string]any{"is_favorite":false}, false},
  {"single_priority", []int{30}, []string{"priority"}, map[string]any{"priority":3}, true},
 }
 for _, item := range cases {
  for _, channel := range []string{"rest", "mcp"} {
   t.Run(item.name+"_"+channel, func(t *testing.T) {
    e, err := setupTestEnv()
    require.NoError(t, err)
    observation := map[string]any{"case":item.name,"channel":channel,"task_ids":item.ids,"fields":item.fields,"values":item.values,"status":"incomplete"}
    defer func(){
     raw, err := json.MarshalIndent(observation,"","  "); require.NoError(t,err)
     root := os.Getenv("STUDY_OBSERVATIONS"); require.NotEmpty(t,root)
     require.NoError(t,os.MkdirAll(root,0755))
     require.NoError(t,os.WriteFile(filepath.Join(root,item.name+"-"+channel+".json"),append(raw,'\n'),0644))
    }()
    // Both paths use the same upstream synthetic token, actor and permissions.
    token := mcpFullToken
    c:=newMCPClientOn(t,e,token)
    observation["action_schema_response"] = c.callTool("find_action",map[string]any{"action":"tasks_bulk_update"})
    selectedTools:=[]map[string]any{}
    for _, tool := range c.listTools() { if tool["name"]=="do_action" || tool["name"]=="tasks_update" {selectedTools=append(selectedTools,tool)} }
    observation["tool_catalog"] = selectedTools
    before := studyBulkSnapshot(t,item.ids)
    observation["before"] = before
    readbacks := func() map[string]any {
     result := map[string]any{}
     for _, id := range item.ids {
      r := humaRequest(t,e,http.MethodGet,fmt.Sprintf("/api/v2/tasks/%d",id),"",token,"")
      result[fmt.Sprint(id)] = map[string]any{"http_status":r.Code,"body":r.Body.String()}
     }
     return result
    }
    observation["api_before"] = readbacks()
    args := map[string]any{"task_ids":item.ids,"fields":item.fields,"values":item.values}
    if channel == "rest" {
     method,path,body := http.MethodPut,"/api/v2/tasks/bulk",args
     if item.single {method=http.MethodPatch;path=fmt.Sprintf("/api/v2/tasks/%d",item.ids[0]);body=item.values}
     raw,err := json.Marshal(body);require.NoError(t,err)
     observation["input"] = body
     contentType := "application/json"
     if item.single {contentType="application/merge-patch+json"}
     r:=humaRequest(t,e,method,path,string(raw),token,contentType)
     observation["response"] = map[string]any{"http_status":r.Code,"body":r.Body.String()}
     observation["operation_success"] = r.Code>=200 && r.Code<300
    } else {
     name:="do_action"
     payload:=map[string]any{"action":"tasks_bulk_update","arguments":args}
     if item.single {name="tasks_update";payload=map[string]any{"task":item.ids[0],"priority":3}}
     observation["tool"] = name
     observation["input"] = payload
     response:=c.callTool(name,payload)
     observation["response"] = response
     observation["operation_success"] = response["isError"] != true
    }
    observation["after"] = studyBulkSnapshot(t,item.ids)
    observation["api_after"] = readbacks()
    observation["status"] = "observed"
   })
  }
 }
}
