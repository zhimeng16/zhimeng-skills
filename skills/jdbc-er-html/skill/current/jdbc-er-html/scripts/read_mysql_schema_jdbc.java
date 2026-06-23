import java.io.BufferedReader;
import java.io.Console;
import java.io.FileWriter;
import java.io.InputStreamReader;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class ReadMysqlSchemaJdbc {
  private static final Pattern STANDARD_FK = Pattern.compile("FK\\s*->\\s*(?:(\\w+)\\.)?(\\w+)\\.(\\w+)");
  private static final Pattern WEAK_RELATION = Pattern.compile("关联\\s*([a-zA-Z0-9_]+)\\.([a-zA-Z0-9_]+)");
  private static final Pattern POLYMORPHIC_MARKER = Pattern.compile("(?:多态逻辑FK|多态\\s*FK)", Pattern.CASE_INSENSITIVE);
  private static final Pattern POLYMORPHIC_TARGET = Pattern.compile("([^,，;；()]+?)\\s*->\\s*(?:(\\w+)\\.)?(\\w+)\\.(\\w+)");

  public static void main(String[] args) throws Exception {
    if (args.length != 6) {
      System.err.println("Usage: java -cp <mysql-connector.jar> read_mysql_schema_jdbc.java <host> <port> <schemas_csv> <user> <password-or-> <output_json>");
      System.exit(2);
    }

    String host = args[0];
    String port = args[1];
    List<String> schemas = Arrays.stream(args[2].split(","))
      .map(String::trim)
      .filter(s -> !s.isEmpty())
      .toList();
    if (schemas.isEmpty()) {
      throw new IllegalArgumentException("必须指定库名后才允许生成 ER 图。");
    }

    String user = args[3];
    String password = readPassword(args[4]);
    String output = args[5];

    String url = "jdbc:mysql://" + host + ":" + port + "/information_schema"
      + "?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=utf8"
      + "&connectTimeout=8000&socketTimeout=12000";

    Properties props = new Properties();
    props.setProperty("user", user);
    props.setProperty("password", password);
    props.setProperty("readOnly", "true");

    try (Connection conn = DriverManager.getConnection(url, props)) {
      conn.setReadOnly(true);
      String json = buildJson(conn, host, port, schemas);
      try (FileWriter writer = new FileWriter(output)) {
        writer.write(json);
      }
      System.out.println(output);
    }
  }

  private static String readPassword(String raw) throws Exception {
    if (!"-".equals(raw)) return raw;
    Console console = System.console();
    if (console != null) return new String(console.readPassword("Password: "));
    System.err.print("Password: ");
    return new BufferedReader(new InputStreamReader(System.in)).readLine();
  }

  private static String buildJson(Connection conn, String host, String port, List<String> schemas) throws Exception {
    StringBuilder out = new StringBuilder();
    out.append("{\n");
    out.append("  \"source\": {\"host\":\"").append(esc(host)).append("\",\"port\":\"").append(esc(port)).append("\",\"schemas\":")
      .append(stringArray(schemas)).append(",\"server_version\":\"").append(esc(scalar(conn, "select version()"))).append("\"},\n");
    out.append("  \"tables\": [\n");

    boolean firstTable = true;
    for (TableInfo table : loadTables(conn, schemas)) {
      if (!firstTable) out.append(",\n");
      firstTable = false;
      List<ColumnInfo> columns = loadColumns(conn, table.schema, table.name);
      out.append("    {\n");
      out.append("      \"schema\":\"").append(esc(table.schema)).append("\",\n");
      out.append("      \"name\":\"").append(esc(table.name)).append("\",\n");
      out.append("      \"engine\":\"").append(esc(table.engine)).append("\",\n");
      out.append("      \"rows\":").append(table.rows == null ? "null" : table.rows).append(",\n");
      out.append("      \"comment\":\"").append(esc(table.comment)).append("\",\n");
      out.append("      \"columns\": ").append(columnsJson(columns)).append(",\n");
      out.append("      \"indexes\": ").append(indexesJson(loadIndexes(conn, table.schema, table.name))).append(",\n");
      out.append("      \"physical_fks\": ").append(physicalFkJson(loadPhysicalFks(conn, table.schema, table.name))).append(",\n");
      out.append("      \"standard_logical_fks\": ").append(logicalFkJson(parseStandardFks(table, columns))).append(",\n");
      out.append("      \"polymorphic_logical_fks\": ").append(polymorphicFkJson(parsePolymorphicFks(table, columns))).append(",\n");
      out.append("      \"weak_comment_relations\": ").append(logicalFkJson(parseWeakRelations(table, columns))).append("\n");
      out.append("    }");
    }

    out.append("\n  ]\n");
    out.append("}\n");
    return out.toString();
  }

  private static String scalar(Connection conn, String sql) throws Exception {
    try (PreparedStatement ps = conn.prepareStatement(sql); ResultSet rs = ps.executeQuery()) {
      rs.next();
      return clean(rs.getString(1));
    }
  }

  private static List<TableInfo> loadTables(Connection conn, List<String> schemas) throws Exception {
    String sql = "select table_schema, table_name, engine, table_rows, table_comment from tables where table_type = 'BASE TABLE' and table_schema in (" + inClause(schemas) + ") order by table_schema, table_name";
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
      bindSchemas(ps, schemas);
      List<TableInfo> result = new ArrayList<>();
      try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
          result.add(new TableInfo(rs.getString("table_schema"), rs.getString("table_name"), clean(rs.getString("engine")), rs.getString("table_rows"), clean(rs.getString("table_comment"))));
        }
      }
      return result;
    }
  }

  private static List<ColumnInfo> loadColumns(Connection conn, String schema, String table) throws Exception {
    String sql = "select ordinal_position, column_name, column_type, is_nullable, column_key, column_default, extra, column_comment from columns where table_schema = ? and table_name = ? order by ordinal_position";
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
      ps.setString(1, schema);
      ps.setString(2, table);
      List<ColumnInfo> result = new ArrayList<>();
      try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
          result.add(new ColumnInfo(rs.getInt("ordinal_position"), rs.getString("column_name"), clean(rs.getString("column_type")), clean(rs.getString("is_nullable")), clean(rs.getString("column_key")), clean(rs.getString("column_default")), clean(rs.getString("extra")), clean(rs.getString("column_comment"))));
        }
      }
      return result;
    }
  }

  private static List<IndexInfo> loadIndexes(Connection conn, String schema, String table) throws Exception {
    String sql = "select index_name, non_unique, group_concat(column_name order by seq_in_index separator ',') as columns from statistics where table_schema = ? and table_name = ? group by index_name, non_unique order by index_name";
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
      ps.setString(1, schema);
      ps.setString(2, table);
      List<IndexInfo> result = new ArrayList<>();
      try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) result.add(new IndexInfo(rs.getString("index_name"), "0".equals(rs.getString("non_unique")), Arrays.asList(rs.getString("columns").split(","))));
      }
      return result;
    }
  }

  private static List<PhysicalFk> loadPhysicalFks(Connection conn, String schema, String table) throws Exception {
    String sql = "select column_name, referenced_table_schema, referenced_table_name, referenced_column_name from key_column_usage where table_schema = ? and table_name = ? and referenced_table_name is not null order by ordinal_position";
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
      ps.setString(1, schema);
      ps.setString(2, table);
      List<PhysicalFk> result = new ArrayList<>();
      try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) result.add(new PhysicalFk(rs.getString("column_name"), rs.getString("referenced_table_schema"), rs.getString("referenced_table_name"), rs.getString("referenced_column_name")));
      }
      return result;
    }
  }

  private static List<LogicalFk> parseStandardFks(TableInfo table, List<ColumnInfo> columns) {
    List<LogicalFk> result = new ArrayList<>();
    for (ColumnInfo column : columns) {
      Matcher matcher = STANDARD_FK.matcher(column.comment);
      if (matcher.find()) result.add(new LogicalFk(column.name, matcher.group(1) == null ? table.schema : matcher.group(1), matcher.group(2), matcher.group(3), column.comment));
    }
    return result;
  }

  private static List<LogicalFk> parseWeakRelations(TableInfo table, List<ColumnInfo> columns) {
    List<LogicalFk> result = new ArrayList<>();
    for (ColumnInfo column : columns) {
      if (POLYMORPHIC_MARKER.matcher(column.comment).find()) continue;
      Matcher matcher = WEAK_RELATION.matcher(column.comment);
      if (matcher.find()) result.add(new LogicalFk(column.name, table.schema, matcher.group(1), matcher.group(2), column.comment));
    }
    return result;
  }

  private static List<PolymorphicFk> parsePolymorphicFks(TableInfo table, List<ColumnInfo> columns) {
    List<PolymorphicFk> result = new ArrayList<>();
    for (ColumnInfo column : columns) {
      if (!POLYMORPHIC_MARKER.matcher(column.comment).find()) continue;
      List<PolyTarget> targets = new ArrayList<>();
      Matcher matcher = POLYMORPHIC_TARGET.matcher(column.comment);
      while (matcher.find()) {
        targets.add(new PolyTarget(clean(matcher.group(1)), matcher.group(2) == null ? table.schema : matcher.group(2), matcher.group(3), matcher.group(4)));
      }
      if (!targets.isEmpty()) result.add(new PolymorphicFk(column.name, targets, column.comment));
    }
    return result;
  }

  private static String columnsJson(List<ColumnInfo> columns) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < columns.size(); i++) {
      ColumnInfo c = columns.get(i);
      if (i > 0) out.append(",");
      out.append("{\"name\":\"").append(esc(c.name)).append("\",\"ordinal\":").append(c.ordinal)
        .append(",\"type\":\"").append(esc(c.type)).append("\",\"nullable\":\"").append(esc(c.nullable))
        .append("\",\"key\":\"").append(esc(c.key)).append("\",\"default\":\"").append(esc(c.defaultValue))
        .append("\",\"extra\":\"").append(esc(c.extra)).append("\",\"comment\":\"").append(esc(c.comment)).append("\"}");
    }
    return out.append("]").toString();
  }

  private static String indexesJson(List<IndexInfo> indexes) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < indexes.size(); i++) {
      IndexInfo idx = indexes.get(i);
      if (i > 0) out.append(",");
      out.append("{\"name\":\"").append(esc(idx.name)).append("\",\"unique\":").append(idx.unique).append(",\"columns\":").append(stringArray(idx.columns)).append("}");
    }
    return out.append("]").toString();
  }

  private static String physicalFkJson(List<PhysicalFk> fks) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < fks.size(); i++) {
      PhysicalFk fk = fks.get(i);
      if (i > 0) out.append(",");
      out.append("{\"column\":\"").append(esc(fk.column)).append("\",\"target_schema\":\"").append(esc(fk.schema)).append("\",\"target_table\":\"").append(esc(fk.table)).append("\",\"target_column\":\"").append(esc(fk.targetColumn)).append("\"}");
    }
    return out.append("]").toString();
  }

  private static String logicalFkJson(List<LogicalFk> fks) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < fks.size(); i++) {
      LogicalFk fk = fks.get(i);
      if (i > 0) out.append(",");
      out.append("{\"column\":\"").append(esc(fk.column)).append("\",\"target_schema\":\"").append(esc(fk.schema)).append("\",\"target_table\":\"").append(esc(fk.table)).append("\",\"target_column\":\"").append(esc(fk.targetColumn)).append("\",\"comment\":\"").append(esc(fk.comment)).append("\"}");
    }
    return out.append("]").toString();
  }

  private static String polymorphicFkJson(List<PolymorphicFk> fks) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < fks.size(); i++) {
      PolymorphicFk fk = fks.get(i);
      if (i > 0) out.append(",");
      out.append("{\"column\":\"").append(esc(fk.column)).append("\",\"targets\":[");
      for (int j = 0; j < fk.targets.size(); j++) {
        PolyTarget target = fk.targets.get(j);
        if (j > 0) out.append(",");
        out.append("{\"condition\":\"").append(esc(target.condition)).append("\",\"target_schema\":\"").append(esc(target.schema)).append("\",\"target_table\":\"").append(esc(target.table)).append("\",\"target_column\":\"").append(esc(target.targetColumn)).append("\"}");
      }
      out.append("],\"comment\":\"").append(esc(fk.comment)).append("\"}");
    }
    return out.append("]").toString();
  }

  private static String stringArray(List<String> values) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < values.size(); i++) {
      if (i > 0) out.append(",");
      out.append("\"").append(esc(values.get(i))).append("\"");
    }
    return out.append("]").toString();
  }

  private static String inClause(List<String> schemas) {
    return String.join(",", schemas.stream().map(s -> "?").toList());
  }

  private static void bindSchemas(PreparedStatement ps, List<String> schemas) throws Exception {
    for (int i = 0; i < schemas.size(); i++) ps.setString(i + 1, schemas.get(i));
  }

  private static String clean(String value) {
    if (value == null) return "";
    return value.replace('\n', ' ').replace('\r', ' ').trim();
  }

  private static String esc(String value) {
    if (value == null) return "";
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\b", "\\b").replace("\f", "\\f").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
  }

  record TableInfo(String schema, String name, String engine, String rows, String comment) {}
  record ColumnInfo(int ordinal, String name, String type, String nullable, String key, String defaultValue, String extra, String comment) {}
  record IndexInfo(String name, boolean unique, List<String> columns) {}
  record PhysicalFk(String column, String schema, String table, String targetColumn) {}
  record LogicalFk(String column, String schema, String table, String targetColumn, String comment) {}
  record PolyTarget(String condition, String schema, String table, String targetColumn) {}
  record PolymorphicFk(String column, List<PolyTarget> targets, String comment) {}
}
