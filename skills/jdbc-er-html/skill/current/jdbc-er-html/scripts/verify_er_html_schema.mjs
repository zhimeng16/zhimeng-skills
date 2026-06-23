#!/usr/bin/env node
import fs from "node:fs";
import crypto from "node:crypto";

const [, , htmlPath, schemaPath] = process.argv;

if (!htmlPath || !schemaPath) {
  console.error("Usage: node verify_er_html_schema.mjs <html_path> <schema_json_path>");
  process.exit(2);
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function hash(value) {
  return crypto.createHash("sha256").update(JSON.stringify(stable(value))).digest("hex");
}

function loadHtmlSnapshot(html) {
  const match = html.match(/<script[^>]+id=["']schemaSnapshot["'][^>]*>([\s\S]*?)<\/script>/i);
  if (!match) throw new Error("HTML 缺少 <script type=\"application/json\" id=\"schemaSnapshot\">");
  return JSON.parse(match[1].trim());
}

function canonicalize(snapshot) {
  const source = snapshot.source || snapshot.summary?.source || {};
  const copy = {
    source: {
      host: source.host || "",
      port: source.port || "",
      schemas: source.schemas || [],
      server_version: source.server_version || snapshot.summary?.mysql_version || ""
    },
    tables: JSON.parse(JSON.stringify(snapshot.tables || []))
  };

  copy.tables = copy.tables.map((table) => ({
    ...table,
    columns: [...(table.columns || [])].sort((a, b) => a.ordinal - b.ordinal || a.name.localeCompare(b.name)),
    indexes: [...(table.indexes || [])].sort((a, b) => a.name.localeCompare(b.name)),
    physical_fks: [...(table.physical_fks || [])].sort((a, b) => (a.column || "").localeCompare(b.column || "")),
    standard_logical_fks: [...(table.standard_logical_fks || [])].sort((a, b) => (a.column || "").localeCompare(b.column || "")),
    polymorphic_logical_fks: [...(table.polymorphic_logical_fks || [])].sort((a, b) => (a.column || "").localeCompare(b.column || "")),
    weak_comment_relations: [...(table.weak_comment_relations || [])].sort((a, b) => (a.column || "").localeCompare(b.column || ""))
  })).sort((a, b) => `${a.schema}.${a.name}`.localeCompare(`${b.schema}.${b.name}`));

  return copy;
}

function summary(snapshot) {
  const source = snapshot.source || snapshot.summary?.source || {};
  const tables = snapshot.tables || [];
  return {
    schemas: source.schemas || [],
    version: source.server_version || snapshot.summary?.mysql_version || "",
    tableCount: tables.length,
    columnCount: tables.reduce((sum, table) => sum + (table.columns || []).length, 0),
    indexCount: tables.reduce((sum, table) => sum + (table.indexes || []).length, 0),
    physicalFkAnomalyCount: tables.reduce((sum, table) => sum + (table.physical_fks || []).length, 0),
    annotationLogicalFkCount: tables.reduce((sum, table) => sum + (table.standard_logical_fks || []).length, 0),
    polymorphicLogicalFkCount: tables.reduce((sum, table) => sum + (table.polymorphic_logical_fks || []).length, 0),
    nonstandardRelationCommentCount: tables.reduce((sum, table) => sum + (table.weak_comment_relations || []).length, 0)
  };
}

function declaredHash(snapshot) {
  return snapshot.schema_hash_full || snapshot.summary?.schema_hash_full || snapshot.schema_hash || snapshot.summary?.schema_hash || "";
}

const html = fs.readFileSync(htmlPath, "utf8");
const rawHtmlSnapshot = loadHtmlSnapshot(html);
const htmlSnapshot = canonicalize(rawHtmlSnapshot);
const dbSnapshot = canonicalize(JSON.parse(fs.readFileSync(schemaPath, "utf8")));

const htmlHash = hash(htmlSnapshot);
const dbHash = hash(dbSnapshot);
const htmlSummary = summary(htmlSnapshot);
const dbSummary = summary(dbSnapshot);
const htmlDeclaredHash = declaredHash(rawHtmlSnapshot);
const diffs = [];

if (htmlHash !== dbHash) diffs.push(`schema_hash 不一致 html=${htmlHash.slice(0, 16)} db=${dbHash.slice(0, 16)}`);
if (htmlDeclaredHash && !dbHash.startsWith(htmlDeclaredHash)) {
  diffs.push(`HTML 声明 schema_hash 不一致 html=${htmlDeclaredHash} db=${dbHash.slice(0, htmlDeclaredHash.length)}`);
}
if (dbSummary.physicalFkAnomalyCount > 0) {
  diffs.push(`存在物理 FK 异常：${dbSummary.physicalFkAnomalyCount}。项目规范不允许 DDL 创建物理 FK，必须删除后重试。`);
}

for (const key of Object.keys(dbSummary)) {
  if (JSON.stringify(htmlSummary[key]) !== JSON.stringify(dbSummary[key])) {
    diffs.push(`${key} 不一致 html=${JSON.stringify(htmlSummary[key])} db=${JSON.stringify(dbSummary[key])}`);
  }
}

if (diffs.length) {
  console.log(JSON.stringify({ ok: false, htmlSummary, dbSummary, htmlHash, dbHash, diffs }, null, 2));
  process.exit(1);
}

console.log(JSON.stringify({ ok: true, summary: dbSummary, schema_hash: dbHash }, null, 2));
