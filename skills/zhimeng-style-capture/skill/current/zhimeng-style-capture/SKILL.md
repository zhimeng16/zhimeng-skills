---
name: zhimeng-style-capture
description: Use only when the user explicitly asks to reuse a saved/collected style-kit, style pack, template, or previously liked website style, or asks to capture/extract/copy/down/archive a website, screenshot, HTML, or UI art direction into a reusable style-kit. Do not use for ordinary website, HTML, landing page, or frontend requests unless saved-style reuse or style extraction is explicit.
---

# 芝梦 · 艺术网站风格捕获与复用

## 核心原则

复用视觉语言, 不复用第三方身份。

把网站、截图、HTML 或提示词中的艺术方向拆成可维护的 `style-kit`; 用户明确要复用已收藏风格时, 读取对应 `style-kit` 并迁移到用户自己的内容、产品和资产上。

## 触发前判断

只在两种明确意图下使用:

1. **复用已收藏风格**: 用户明确说要复用风格库、风格包、之前喜欢/收藏的模板、某个已保存风格样式、某个 `style-kit`。
2. **提取新网站风格**: 用户明确说要把某个网站、截图、HTML 或 UI 的风格 copy、down、提取、捕获、归档成 `style-kit`。

不触发:

- 用户只是说“帮我做一个网站”“设计一个 landing page”“做一个前端页面”。
- 用户只是说“把这篇 Markdown 转 HTML”“结构化为 HTML”“生成报告 HTML”。
- 用户有现成产品设计系统、代码 UI 或普通前端实现需求, 但没有说要复用已收藏风格或提取新风格。

冲突规避:

- `zhimeng-md-html` 继续负责 Markdown、资料、方案、报告结构化为 HTML; 本 Skill 不介入。
- `web-design-engineer` / `frontend-design` 继续负责普通网站、页面和前端原型设计; 本 Skill 只在明确复用已收藏风格时提供风格包输入。
- `firecrawl-website-design-clone` 可以负责网页证据抓取; 本 Skill 负责把提取结果沉淀成长期 `style-kit`。

## 强制边界

- 不复制品牌、logo、原图、视频、字体文件、原文案和真实下载链路。
- 原站截图和抓取结果只放 `.firecrawl/`、系统临时目录或用户明确指定的 ignore 目录。
- 不在 vault 根目录生成临时截图、HTML 或抓取文件。
- 不自动安装到 `.agents/skills`、`.claude/skills`、`~/.codex/skills`。
- 用户只说“像这个网站”时, 默认执行同风格迁移, 不做 1:1 克隆。

## 工作模式

### A. 捕获新风格

1. 收集证据: 桌面、移动端、主要交互、字体、颜色、布局、图片风格、组件。
2. 归纳风格: 给中性艺术名称, 不用第三方品牌名做目录名。
3. 写入风格包: 按 `references/style-kit-contract.md` 创建 `style-kits/<style-slug>/`。
4. 隔离版权: 不把原始截图、远程图片、logo、字体或视频写进风格包。
5. 验证: 运行 `scripts/validate-style-kit.sh`。

### B. 复用已有风格

1. 如果用户已指定 `style-kit`, 直接读取该风格包。
2. 如果用户只说“复用风格库/风格包/之前收藏的风格”, 先列出现有 `style-kit` 并询问用哪一个。
3. 读取目标风格包的 `DESIGN.md`、`tokens.css`、`components.html`、`template.html`、`prompt.md`。
4. 把用户内容映射到该风格的版式结构, 不照搬来源网站的信息架构。
5. 图片只用三类: 用户自有图片、生成图片、明确占位。
6. 输出 HTML 时优先单文件, 除非用户要求接入项目代码。
7. 交付前做桌面和移动端检查; 浏览器截图只放 ignore 缓存目录。

## 风格包目录

```text
style-kits/<style-slug>/
├── DESIGN.md
├── tokens.css
├── components.html
├── template.html
└── prompt.md
```

## 参考文件

- `references/style-kit-contract.md`: 风格包结构、命名和验收合同。
- `references/github-skill-research.md`: 高星 Skill 仓库借鉴结论。
- `examples/capture-request.md`: 捕获新网站风格的样例。
- `examples/reuse-request.md`: 复用已有风格的样例。
- `scripts/validate-style-kit.sh`: 本地静态验收脚本。

## 当前内置风格

- `cyber-temple-classicism`: 赛博主神殿古典主义。来源参考一个公开实验性 AI agent 页面, 只保留电蓝单色、古典铜版画、纪念碑式标题、紧凑功能网格和实验性产品页节奏。

## 验收

新增或修改风格包后运行:

```bash
bash "10-项目开发/10-个人项目/SKill Creation/艺术网站风格捕获与复用/skill/current/zhimeng-style-capture/scripts/validate-style-kit.sh"
```
