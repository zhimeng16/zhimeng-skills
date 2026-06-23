#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const [, , schemaJsonPath, outputHtmlPath] = process.argv;

if (!schemaJsonPath || !outputHtmlPath) {
  console.error("Usage: node generate_er_html.mjs <schema_json> <output_html>");
  process.exit(2);
}

if (outputHtmlPath.includes("归档")) {
  console.error("输出路径包含“归档”，禁止写入归档目录。请指定当前正式目录。");
  process.exit(2);
}

const outputDir = path.dirname(path.resolve(outputHtmlPath));
if (!fs.existsSync(outputDir)) {
  console.error(`输出目录不存在：${outputDir}`);
  process.exit(2);
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function canonicalize(snapshot) {
  return {
    source: {
      host: snapshot.source?.host || "",
      port: snapshot.source?.port || "",
      schemas: snapshot.source?.schemas || [],
      server_version: snapshot.source?.server_version || ""
    },
    tables: [...(snapshot.tables || [])].map((table) => ({
      ...table,
      columns: [...(table.columns || [])].sort((a, b) => a.ordinal - b.ordinal || a.name.localeCompare(b.name)),
      indexes: [...(table.indexes || [])].sort((a, b) => a.name.localeCompare(b.name)),
      physical_fks: [...(table.physical_fks || [])].sort((a, b) => (a.column || "").localeCompare(b.column || "")),
      standard_logical_fks: [...(table.standard_logical_fks || [])].sort((a, b) => (a.column || "").localeCompare(b.column || "")),
      polymorphic_logical_fks: [...(table.polymorphic_logical_fks || [])].sort((a, b) => (a.column || "").localeCompare(b.column || "")),
      weak_comment_relations: [...(table.weak_comment_relations || [])].sort((a, b) => (a.column || "").localeCompare(b.column || ""))
    })).sort((a, b) => `${a.schema}.${a.name}`.localeCompare(`${b.schema}.${b.name}`))
  };
}

function hash(snapshot) {
  return crypto.createHash("sha256").update(JSON.stringify(stable(canonicalize(snapshot)))).digest("hex");
}

function flattenWithSource(snapshot, key) {
  const result = [];
  for (const table of snapshot.tables || []) {
    for (const item of table[key] || []) {
      result.push({
        source_schema: table.schema,
        source_table: table.name,
        ...item
      });
    }
  }
  return result;
}

const raw = JSON.parse(fs.readFileSync(schemaJsonPath, "utf8"));
if (!raw.source?.schemas?.length) {
  console.error("schema JSON 缺少 source.schemas。必须指定库名后才允许生成 ER 图。");
  process.exit(2);
}

const schemaHash = hash(raw);
const shortHash = schemaHash.slice(0, 16);
const tables = raw.tables || [];
const snapshot = {
  source: raw.source,
  summary: {
    database: raw.source.schemas.join(", "),
    source: raw.source,
    mysql_version: raw.source.server_version,
    table_count: tables.length,
    field_count: tables.reduce((sum, table) => sum + (table.columns || []).length, 0),
    index_count: tables.reduce((sum, table) => sum + (table.indexes || []).length, 0),
    physical_fk_count: tables.reduce((sum, table) => sum + (table.physical_fks || []).length, 0),
    physical_fk_anomaly_count: tables.reduce((sum, table) => sum + (table.physical_fks || []).length, 0),
    standard_logical_fk_count: tables.reduce((sum, table) => sum + (table.standard_logical_fks || []).length, 0),
    annotation_logical_fk_count: tables.reduce((sum, table) => sum + (table.standard_logical_fks || []).length, 0),
    polymorphic_logical_fk_count: tables.reduce((sum, table) => sum + (table.polymorphic_logical_fks || []).length, 0),
    weak_comment_relation_count: tables.reduce((sum, table) => sum + (table.weak_comment_relations || []).length, 0),
    nonstandard_relation_comment_count: tables.reduce((sum, table) => sum + (table.weak_comment_relations || []).length, 0),
    schema_hash: shortHash,
    schema_hash_full: schemaHash,
    generated_from: path.resolve(schemaJsonPath)
  },
  tables,
  physical_fks: flattenWithSource(raw, "physical_fks"),
  standard_logical_fks: flattenWithSource(raw, "standard_logical_fks"),
  polymorphic_logical_fks: flattenWithSource(raw, "polymorphic_logical_fks"),
  weak_comment_relations: flattenWithSource(raw, "weak_comment_relations"),
  schema_hash: shortHash,
  schema_hash_full: schemaHash
};

const currentFile = fileURLToPath(import.meta.url);
const skillDir = path.resolve(path.dirname(currentFile), "..");
const templatePath = path.join(skillDir, "assets", "er-template.html");
const template = fs.readFileSync(templatePath, "utf8");
const safeJson = JSON.stringify(snapshot, null, 2).replace(/<\/script/gi, "<\\/script");
const title = `${raw.source.schemas.join(", ")} · 全局 ER 图`;

const html = template
  .replace("__TITLE__", title)
  .replace("__SCHEMA_SNAPSHOT_JSON__", safeJson);

fs.writeFileSync(outputHtmlPath, html);

console.log(JSON.stringify({
  ok: true,
  output_html: path.resolve(outputHtmlPath),
  schemas: raw.source.schemas,
  mysql_version: raw.source.server_version,
  table_count: snapshot.summary.table_count,
  field_count: snapshot.summary.field_count,
  index_count: snapshot.summary.index_count,
  physical_fk_anomaly_count: snapshot.summary.physical_fk_anomaly_count,
  annotation_logical_fk_count: snapshot.summary.annotation_logical_fk_count,
  polymorphic_logical_fk_count: snapshot.summary.polymorphic_logical_fk_count,
  nonstandard_relation_comment_count: snapshot.summary.nonstandard_relation_comment_count,
  schema_hash: shortHash
}, null, 2));
