import java.nio.file.*;
import java.sql.*;
import javax.sql.DataSource;
/** Uses the immutable application's own SQLite driver/UDF/collation implementations. */
public class OriginalJdbc {
  public static void main(String[] args) throws Exception {
    if(args.length!=4) throw new IllegalArgumentException("mode database input output");
    Path db=Path.of(args[1]).toAbsolutePath();
    String mode=args[0];
    if(!mode.equals("fixture") && !mode.equals("integrity")) throw new IllegalArgumentException("mode");
    if(mode.equals("integrity") && !Files.isRegularFile(db)) throw new IllegalArgumentException("missing_database");
    Class<?> type=Class.forName("org.gotson.komga.infrastructure.datasource.SqliteUdfDataSource");
    Object ds=type.getConstructor().newInstance();
    String url="jdbc:sqlite:"+db;
    if(mode.equals("integrity")) url="jdbc:sqlite:file:"+db.toUri().getRawPath()+"?mode=ro";
    type.getMethod("setUrl",String.class).invoke(ds,url);
    try(Connection c=((DataSource)ds).getConnection(); Statement s=c.createStatement()) {
      if(mode.equals("fixture")) {
        for(String line:Files.readAllLines(Path.of(args[2]))) if(!line.isBlank()) s.execute(line);
        Files.writeString(Path.of(args[3]),"fixture_complete\n");
      } else {
        s.execute("PRAGMA query_only=ON");
        s.execute("BEGIN");
        int rows=0;
        try(ResultSet r=s.executeQuery("PRAGMA integrity_check")) {
          while(r.next()) {if(!"ok".equals(r.getString(1))) throw new IllegalStateException("integrity_failed: "+r.getString(1));rows++;}
        }
        if(rows!=1) throw new IllegalStateException("integrity_result_count");
        try(ResultSet r=s.executeQuery("PRAGMA foreign_key_check")) {if(r.next()) throw new IllegalStateException("foreign_key_violation");}
        String version;
        try(ResultSet r=s.executeQuery("SELECT sqlite_version()")){if(!r.next())throw new IllegalStateException("version_missing");version=r.getString(1);}
        s.execute("ROLLBACK");
        Files.writeString(Path.of(args[3]),"integrity_ok\n"+version+"\n");
      }
    }
  }
}
