---
name: jdbc-er-html
description: 从指定 MySQL 库通过 JDBC 只读读取 information_schema，生成稳定版交互式 ER HTML，并通过第二次 schema 拉取结果校验 HTML 内嵌 schemaSnapshot。适用于生成 ER 图、数据库结构图、MySQL ER HTML、全量表结构可视化、数据库文档 HTML，或执行“必须指定库名 -> 拉取全量 schema -> 生成 HTML -> 二次校验”的稳定流程。
---

# JDBC ER HTML

用于从一个或多个明确指定的 MySQL 库生成经过校验的单文件 ER HTML。Skill 名可以英文；说明、页面文案、校验报告优先中文，只有 `JDBC`、`MySQL`、`information_schema`、`schemaSnapshot`、`schema_hash`、`HTML`、`ER`、`FK` 等专业术语保留英文。

## 硬规则

- 必须指定库名。没有 `schema_names` 时停止，并回复：`必须指定库名后才允许生成 ER 图。`
- 只允许只读连接数据库，禁止执行 DDL / DML。
- 使用 JDBC 直连 `information_schema`，不依赖 DataGrip UI。
- 只读取用户指定库名，不读取未指定业务库生成 ER 图。
- 注释逻辑 FK 只识别字段注释：
  - `字段说明(FK -> 目标表名.目标字段名)`
  - `字段说明(FK -> 库名.目标表名.目标字段名)`
- 多态逻辑 FK 是合法特殊关系，识别字段注释：
  - `字段说明(多态逻辑FK：条件1 -> 目标表1.目标字段, 条件2 -> 目标表2.目标字段)`
  - 多态逻辑 FK 单独统计，详情中列出，不计入“非规范关联注释”，默认不画主关系线，避免误导为普通一对一外键。
- 物理 FK 不作为正常关系展示；如果从数据库读到物理 FK，视为 DDL 异常，校验不得通过。
- 非标准注释如 `关联 table.column` 只能标记为“非规范关联注释”，用于提示补注释，不画关系线，不计为 FK。
- HTML 必须内嵌原始 `schemaSnapshot` JSON，不能用 UI summary 替代原始事实。
- 表、字段、索引、关系线必须来自 `schemaSnapshot`，禁止臆造。
- 输出文件必须落到当前正式目录，不得落到归档目录。写入前后都要用 `ls` 或等价方式确认路径。

## 固定流程

1. 校验输入：host、port、user、password、schema_names、output_html_path、JDBC driver 路径。
2. 校验输出目录存在且不是归档目录。
3. 第一次运行 `scripts/read_mysql_schema_jdbc.java`，只读拉取指定库全量 schema，生成 JSON 快照。
4. 运行 `scripts/generate_er_html.mjs`，使用 `assets/er-template.html` 生成 ER HTML。
5. 第二次运行 `scripts/read_mysql_schema_jdbc.java`，重新拉取同一批库。
6. 运行 `scripts/verify_er_html_schema.mjs`，对比 HTML 内嵌 `schemaSnapshot` 和第二次 schema。
7. 如果不一致，基于第二次 schema 重新生成，最多重试 3 次。
8. 只有校验通过且目标文件真实存在，才输出“生成完成”。

## 推荐命令

```bash
# 第一次拉取 schema
java -cp "<mysql-connector-j.jar>" scripts/read_mysql_schema_jdbc.java \
  <host> <port> <schema_names_csv> <user> - /tmp/schema_1.json

# 生成 HTML
node scripts/generate_er_html.mjs \
  /tmp/schema_1.json <output.html>

# 第二次拉取 schema
java -cp "<mysql-connector-j.jar>" scripts/read_mysql_schema_jdbc.java \
  <host> <port> <schema_names_csv> <user> - /tmp/schema_2.json

# 校验 HTML
node scripts/verify_er_html_schema.mjs \
  <output.html> /tmp/schema_2.json
```

密码参数传 `-` 时必须交互输入，避免把密码写进命令历史或文件。

## HTML 结构

使用 `assets/er-template.html`，不要重新设计布局。

固定结构：

- 左侧固定工具栏
- 右侧大画布
- 右下角选中表详情
- 可拖拽
- 可缩放
- 可搜索
- 不使用信息架构版布局

固定 tab：

- `业务域分区图`
- `数据落点与协作图`
- `演示紧凑图`

## 视觉规则

视觉规格见 `references/visual-spec.md`。

必须继承 `zhimeng-md-html` 的默认审美：

- 米白纸感背景
- 赤陶橙 accent
- 高信息密度
- 克制边框
- 衬线标题
- 等宽代码字体
- 不使用深色主题
- 不使用花哨渐变
- 不重新设计色板

## 数据落点与协作图

必须展示这些职责，但不能伪造不存在的表：

- MySQL：业务真源 / 核心业务表
- PostgreSQL + pgvector：RAG / embedding / 向量检索
- OSS：文件本体 / 附件 / 产物
- ELK：日志 / Trace / 错误排障 / 应用观测
- Redis：Session 运行态 / SSE 中断状态 / pub/sub，不是业务真源

如果当前 schema 只有 MySQL 表，其它组件只能作为边界说明。

## schema_hash 展示

- 右上角状态栏显示短 `schema_hash`。
- 左侧 KPI 不展示大号 `schema_hash`。
- `schemaSnapshot` 必须保留完整 hash：`schema_hash_full`。
- 页面只展示短 `schema_hash`，完整 hash 只放在 `schemaSnapshot` 或详情调试信息里。
- hash 不允许在左侧卡片中断成多行。

## 最终输出

输出：

- HTML 文件路径
- 指定库名
- MySQL 版本
- 表数量
- 字段数量
- 索引数量
- 物理 FK 异常数量
- 注释逻辑 FK 数量
- 多态逻辑 FK 数量
- 非规范关联注释数量
- schema_hash
- 校验结论

如校验未通过，必须列出差异，不得声称完成。

## DDL 静态解析模式

当用户只有 MySQL 5.7 初始化 SQL、尚未连接数据库，且明确要“用 SQL 生成 ER HTML”时，必须仍然指定库名，然后走静态流程：

```bash
node scripts/parse_mysql57_ddl_to_schema_json.mjs \
  <input.sql> <schema_name> /tmp/schema_from_ddl.json

node scripts/generate_er_html.mjs \
  /tmp/schema_from_ddl.json <output.html>

node scripts/verify_er_html_schema.mjs \
  <output.html> /tmp/schema_from_ddl.json

node scripts/verify_er_html_layout.mjs \
  <output.html>
```

DDL 模式只能作为“未连接数据库”的静态预览；页面必须显示静态来源，不能伪装成 JDBC 实测。生成后必须跑布局校验，避免表节点互相重叠或溢出模块。
