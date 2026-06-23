#!/usr/bin/env node
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";

const [, , sqlPath, schemaName, outputJsonPath] = process.argv;

if (!sqlPath || !schemaName || !outputJsonPath) {
  console.error("Usage: node parse_mysql57_ddl_to_schema_json.mjs <input.sql> <schema_name> <output_schema.json>");
  process.exit(2);
}

if (!schemaName.trim()) {
  console.error("必须指定库名后才允许生成 ER 图。");
  process.exit(2);
}

const sql = fs.readFileSync(sqlPath, "utf8");
const sqlHash = crypto.createHash("sha256").update(sql).digest("hex");

function clean(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function unquoteSql(value = "") {
  return value.replace(/''/g, "'");
}

function splitTopLevel(input) {
  const result = [];
  let buf = "";
  let quote = null;
  let depth = 0;
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    const next = input[i + 1];
    if (quote) {
      buf += ch;
      if (ch === quote && next === quote) {
        buf += next;
        i++;
      } else if (ch === quote) {
        quote = null;
      }
      continue;
    }
    if (ch === "'" || ch === "`") {
      quote = ch;
      buf += ch;
      continue;
    }
    if (ch === "(") depth++;
    if (ch === ")") depth = Math.max(0, depth - 1);
    if (ch === "," && depth === 0) {
      if (buf.trim()) result.push(buf.trim());
      buf = "";
      continue;
    }
    buf += ch;
  }
  if (buf.trim()) result.push(buf.trim());
  return result;
}

function parseIndexColumns(input) {
  return splitTopLevel(input).map((item) => item.replace(/`/g, "").trim());
}

function extractType(rest) {
  const match = rest.match(/^(.+?)(?=\s+(?:NOT\s+NULL|NULL|DEFAULT\b|COMMENT\b|ON\s+UPDATE\b|AUTO_INCREMENT|PRIMARY\s+KEY|UNIQUE\b)|$)/i);
  return clean(match ? match[1] : rest);
}

function extractDefault(rest) {
  const match = rest.match(/\bDEFAULT\s+((?:'[^']*(?:''[^']*)*')|[^\s,]+)/i);
  return match ? clean(match[1]) : "";
}

function extractComment(rest) {
  const match = rest.match(/\bCOMMENT\s+'((?:''|[^'])*)'/i);
  return match ? unquoteSql(match[1]) : "";
}

function parseColumn(def, ordinal) {
  const match = def.match(/^`?([a-zA-Z_][\w]*)`?\s+([\s\S]+)$/);
  if (!match) return null;
  const [, name, rest] = match;
  if (/^(PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN)\b/i.test(name)) return null;
  return {
    name,
    ordinal,
    type: extractType(rest),
    nullable: /\bNOT\s+NULL\b/i.test(rest) ? "NO" : "YES",
    key: "",
    default: extractDefault(rest),
    extra: [
      /\bAUTO_INCREMENT\b/i.test(rest) ? "auto_increment" : "",
      /\bON\s+UPDATE\s+CURRENT_TIMESTAMP\b/i.test(rest) ? "on update CURRENT_TIMESTAMP" : ""
    ].filter(Boolean).join(" "),
    comment: extractComment(rest)
  };
}

function parseLogicalFk(table, column) {
  const match = column.comment.match(/FK\s*->\s*(?:(\w+)\.)?(\w+)\.(\w+)/);
  if (!match) return null;
  return {
    column: column.name,
    target_schema: match[1] || table.schema,
    target_table: match[2],
    target_column: match[3],
    comment: column.comment
  };
}

function parseWeakRelation(table, column) {
  if (/FK\s*->/.test(column.comment)) return null;
  if (/(?:多态逻辑FK|多态\s*FK)/i.test(column.comment)) return null;
  const simple = column.comment.match(/关联\s*([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)/);
  if (simple) {
    return {
      column: column.name,
      target_schema: table.schema,
      target_table: simple[1],
      target_column: simple[2],
      comment: column.comment
    };
  }
  return null;
}

function parsePolymorphicFk(table, column) {
  if (!/(?:多态逻辑FK|多态\s*FK)/i.test(column.comment)) return null;
  const targets = [];
  const re = /([^,，;；()]+?)\s*->\s*(?:(\w+)\.)?(\w+)\.(\w+)/g;
  let match;
  while ((match = re.exec(column.comment))) {
    targets.push({
      condition: clean(match[1]),
      target_schema: match[2] || table.schema,
      target_table: match[3],
      target_column: match[4]
    });
  }
  if (!targets.length) return null;
  return {
    column: column.name,
    targets,
    comment: column.comment
  };
}

function parseCreateTables(sqlText) {
  const tables = [];
  const re = /CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?([a-zA-Z_][\w]*)`?\s*\(([\s\S]*?)\)\s*ENGINE\s*=\s*([a-zA-Z0-9_]+)([\s\S]*?)COMMENT\s*=\s*'((?:''|[^'])*)'\s*;/gi;
  let match;
  while ((match = re.exec(sqlText))) {
    const [, name, body, engine, options, comment] = match;
    const parts = splitTopLevel(body);
    const columns = [];
    const indexes = [];
    for (const part of parts) {
      const pk = part.match(/^PRIMARY\s+KEY\s*\(([\s\S]+)\)$/i);
      if (pk) {
        const cols = parseIndexColumns(pk[1]);
        indexes.push({ name: "PRIMARY", unique: true, columns: cols });
        continue;
      }
      const column = parseColumn(part, columns.length + 1);
      if (column) columns.push(column);
    }
    const pkIndex = indexes.find((idx) => idx.name === "PRIMARY");
    if (pkIndex) {
      for (const col of columns) {
        if (pkIndex.columns.includes(col.name)) col.key = "PRI";
      }
    }
    tables.push({
      schema: schemaName,
      name,
      engine: clean(engine),
      rows: null,
      comment: unquoteSql(comment),
      options: clean(options),
      columns,
      indexes,
      physical_fks: [],
      standard_logical_fks: [],
      polymorphic_logical_fks: [],
      weak_comment_relations: []
    });
  }
  return tables;
}

const tables = parseCreateTables(sql);
const tableByName = new Map(tables.map((table) => [table.name, table]));

const indexRe = /ALTER\s+TABLE\s+`?([a-zA-Z_][\w]*)`?\s+ADD\s+(UNIQUE\s+)?(?:INDEX|KEY)\s+`?([a-zA-Z_][\w]*)`?\s*\(([\s\S]*?)\)\s*;/gi;
let indexMatch;
while ((indexMatch = indexRe.exec(sql))) {
  const [, tableName, uniqueRaw, indexName, columnRaw] = indexMatch;
  const table = tableByName.get(tableName);
  if (!table) continue;
  const columns = parseIndexColumns(columnRaw);
  table.indexes.push({ name: indexName, unique: Boolean(uniqueRaw), columns });
  if (uniqueRaw) {
    for (const indexed of columns) {
      const bare = indexed.replace(/\(.+\)$/, "");
      const column = table.columns.find((item) => item.name === bare);
      if (column && column.key !== "PRI") column.key = "UNI";
    }
  }
}

const physicalFkRe = /FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+`?([a-zA-Z_][\w]*)`?\s*\(([^)]+)\)/gi;
let fkMatch;
while ((fkMatch = physicalFkRe.exec(sql))) {
  const [, sourceColumnRaw, targetTable, targetColumnRaw] = fkMatch;
  const sourceColumn = sourceColumnRaw.replace(/[` ]/g, "");
  const targetColumn = targetColumnRaw.replace(/[` ]/g, "");
  const table = tables.find((item) => item.columns.some((column) => column.name === sourceColumn));
  if (table) {
    table.physical_fks.push({
      column: sourceColumn,
      target_schema: schemaName,
      target_table: targetTable,
      target_column: targetColumn
    });
  }
}

for (const table of tables) {
  for (const column of table.columns) {
    const logical = parseLogicalFk(table, column);
    if (logical) table.standard_logical_fks.push(logical);
    const polymorphic = parsePolymorphicFk(table, column);
    if (polymorphic) table.polymorphic_logical_fks.push(polymorphic);
    const weak = parseWeakRelation(table, column);
    if (weak) table.weak_comment_relations.push(weak);
  }
}

const snapshot = {
  source: {
    host: "DDL static parse",
    port: "",
    schemas: [schemaName],
    server_version: "MySQL 5.7 DDL static parse (not connected)",
    sql_file: path.resolve(sqlPath),
    sql_sha256: sqlHash
  },
  tables
};

fs.writeFileSync(outputJsonPath, JSON.stringify(snapshot, null, 2));
console.log(JSON.stringify({
  ok: true,
  output_json: path.resolve(outputJsonPath),
  schema: schemaName,
  sql_sha256: sqlHash.slice(0, 16),
  table_count: tables.length,
  field_count: tables.reduce((sum, table) => sum + table.columns.length, 0),
  index_count: tables.reduce((sum, table) => sum + table.indexes.length, 0),
  annotation_logical_fk_count: tables.reduce((sum, table) => sum + table.standard_logical_fks.length, 0),
  polymorphic_logical_fk_count: tables.reduce((sum, table) => sum + table.polymorphic_logical_fks.length, 0),
  nonstandard_relation_comment_count: tables.reduce((sum, table) => sum + table.weak_comment_relations.length, 0),
  physical_fk_anomaly_count: tables.reduce((sum, table) => sum + table.physical_fks.length, 0)
}, null, 2));
