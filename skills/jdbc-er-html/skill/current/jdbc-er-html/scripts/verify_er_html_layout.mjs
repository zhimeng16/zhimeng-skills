#!/usr/bin/env node
import fs from "node:fs";

const [, , htmlPath] = process.argv;

if (!htmlPath) {
  console.error("Usage: node verify_er_html_layout.mjs <html_path>");
  process.exit(2);
}

function loadSnapshot(html) {
  const match = html.match(/<script[^>]+id=["']schemaSnapshot["'][^>]*>([\s\S]*?)<\/script>/i);
  if (!match) throw new Error("HTML 缺少 schemaSnapshot");
  return JSON.parse(match[1].trim());
}

function inferDomain(table) {
  const name = table.name.toLowerCase();
  const text = `${table.name} ${table.comment || ""}`.toLowerCase();
  if (/rag|vector|embedding|chunk/.test(text)) return "RAG 与向量";
  if (/artifact|oss|file|attach|产物|文件/.test(name)) return "产物与文件";
  if (/skill|expert|mcp|rel_expert_skill/.test(name)) return "专家与技能";
  if (/chat|message|session_feedback|agent_run/.test(name)) return "对话闭环";
  if (/llm|model|credential|usage/.test(name)) return "模型与调用";
  if (/user|auth|account|profile|notification/.test(name)) return "用户与登录";
  if (/config|feature_flag/.test(name)) return "系统配置";
  return "其他";
}

function domainList(tables) {
  const preferred = ["用户与登录", "对话闭环", "模型与调用", "专家与技能", "产物与文件", "系统配置", "RAG 与向量", "其他"];
  const set = new Set(tables.map((table) => table.domain));
  return preferred.filter((item) => set.has(item));
}

function placeGrid(items, positions, startX, startY, columns, gapX, gapY) {
  items.forEach((item, index) => {
    positions[item.id] = [startX + (index % columns) * gapX, startY + Math.floor(index / columns) * gapY];
  });
}

function makeDomainLayout(tables) {
  const positions = {};
  const blocks = [];
  const nodeW = 240;
  const gapY = 286;
  const blockW = 1040;
  const blockGapX = 70;
  const blockGapY = 56;
  const columnY = [58, 58];
  domainList(tables).forEach((domain) => {
    const items = tables.filter((table) => table.domain === domain);
    const cols = items.length >= 5 ? 3 : Math.min(2, Math.max(1, items.length));
    const rows = Math.max(1, Math.ceil(items.length / cols));
    const height = Math.max(300, 72 + rows * gapY + 54);
    const column = columnY[0] <= columnY[1] ? 0 : 1;
    const x = 60 + column * (blockW + blockGapX);
    const y = columnY[column];
    const gapX = cols <= 1 ? 0 : (blockW - 90 - nodeW) / (cols - 1);
    blocks.push({ domain, x, y, w: blockW, h: height });
    placeGrid(items, positions, x + 45, y + 72, cols, gapX, gapY);
    columnY[column] += height + blockGapY;
  });
  return { positions, blocks };
}

function estimateHeight(table) {
  const visibleFields = Math.min(4, (table.columns || []).length);
  const captionLines = Math.min(2, Math.max(1, Math.ceil(String(table.comment || table.name).length / 15)));
  return 55 + captionLines * 18 + visibleFields * 33 + 30;
}

function overlaps(a, b, padding = 16) {
  return !(
    a.x + a.w + padding <= b.x ||
    b.x + b.w + padding <= a.x ||
    a.y + a.h + padding <= b.y ||
    b.y + b.h + padding <= a.y
  );
}

const html = fs.readFileSync(htmlPath, "utf8");
const snapshot = loadSnapshot(html);
const tables = (snapshot.tables || []).map((table) => ({
  ...table,
  id: `${table.schema}.${table.name}`,
  domain: inferDomain(table)
}));
const { positions, blocks } = makeDomainLayout(tables);
const rects = tables.map((table) => {
  const [x, y] = positions[table.id] || [0, 0];
  return { id: table.id, domain: table.domain, x, y, w: 240, h: estimateHeight(table) };
});
const issues = [];

for (let i = 0; i < rects.length; i++) {
  for (let j = i + 1; j < rects.length; j++) {
    if (rects[i].domain === rects[j].domain && overlaps(rects[i], rects[j])) {
      issues.push(`节点重叠：${rects[i].id} / ${rects[j].id}`);
    }
  }
}

for (const rect of rects) {
  const block = blocks.find((item) => item.domain === rect.domain);
  if (!block) continue;
  if (rect.x < block.x || rect.y < block.y || rect.x + rect.w > block.x + block.w || rect.y + rect.h > block.y + block.h) {
    issues.push(`节点溢出模块：${rect.id} -> ${rect.domain}`);
  }
}

if (issues.length) {
  console.log(JSON.stringify({ ok: false, issues, table_count: tables.length }, null, 2));
  process.exit(1);
}

console.log(JSON.stringify({
  ok: true,
  table_count: tables.length,
  domains: Object.fromEntries(domainList(tables).map((domain) => [domain, tables.filter((table) => table.domain === domain).length])),
  checked: "domain layout rectangles"
}, null, 2));
