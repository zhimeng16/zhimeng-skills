# 赛博主神殿古典主义

## Source

- Reference URL: redacted public style source; keep concrete source links in local Harness notes, not in the publishable package.
- Capture date: 2026-06-03
- Purpose: 提炼艺术风格, 不复制品牌、原图、字体文件、原文案或下载链路。

## Design Summary

这个风格像“古典神庙海报被接入赛博终端”: 高纯度电蓝铺满页面, 白色古典衬线字像碑铭一样压住首屏, 铜版画式神话人物和射线构图提供神性与运动感, 细小等宽标签提供技术文档气质。整体不是普通 SaaS 官网, 而是实验室、智能体、研究工具或前沿产品的仪式化发布页。

## 适用场景

- AI agent、研究工具、开发者工具、实验性产品发布页。
- 需要强艺术记忆点的 landing page。
- 想表达“开放、神秘、技术、古典、前沿”的项目。
- 单页展示型 HTML、概念原型、产品发布页 v0。

## 不适用场景

- 管理后台、CRM、数据表格密集页面。
- 公司正式官网的稳重介绍页。
- 长篇阅读报告。
- 需要大量彩色图表或多品牌联合露出的页面。

## 第一眼识别点

- 几乎整页电蓝背景。
- 超大白色古典衬线标题, 分行像碑文。
- 小号等宽大写标签, 字距很大。
- 单色铜版画/蚀刻画视觉资产。
- 白底反相功能区, 仍然只用蓝白两色。
- footer 使用巨大的字标或词块, 接近超宽海报构图。

## Design Tokens

### Colors

| Role | Value | Notes |
|---|---:|---|
| Electric blue | `#0000F2` | 主背景和主色 |
| Paper white | `#F7F7F2` | 白色文字、按钮、反相底 |
| Pure white | `#FFFFFF` | 反相面板 |
| Acid accent | `#EDFF45` | 只在 footer 或高能标记中少量使用 |
| Faded blue | `rgba(0,0,242,.45)` | 叠图、边框、噪点 |
| Hairline | `rgba(247,247,242,.38)` | 蓝底细线 |

### Typography

- Display: 古典高对比衬线。优先用自有授权字体; 无字体时用 `Georgia`, `Times New Roman`, `serif`。
- Mono: 等宽大写小字。优先用 `Courier Prime`, `Courier New`, `monospace`。
- 标题必须轻, 大, 窄行高。不要用粗黑体、圆角科技字体或默认 Inter 风。
- 小标签使用 uppercase、`letter-spacing: .16em - .22em`。

### Layout

- 页面最大宽度 1600px 左右, 外框 gutter 24-32px。
- 首屏使用左右不对称构图: 左侧碑铭标题, 右侧大型神话/雕刻视觉资产。
- 导航居中品牌名, 两侧分散链接, 形成“仪式入口”。
- 中段可插入产品截图或视频 showcase, 像蓝色布景上的玻璃展柜。
- 平台/功能卡用等宽网格, 卡片不圆角或极小圆角。
- 功能区反相成白底蓝字, 使用 3 列 x 2 行网格。
- footer 可用超大词块或背景人物, 形成最后一次视觉冲击。

### Imagery

图像必须是自有、生成或明确授权资产。推荐方向:

- 铜版画、木刻、蚀刻、古典雕塑、星图、神庙、仪器、羽翼、射线。
- 只用蓝白单色或蓝白反相。
- 使用 `mix-blend-mode`, `filter: grayscale(1) contrast(1.2)`, `opacity` 做单色化。
- 可以使用生成图, 但要避免出现来源品牌、真实 logo 或原站角色。

### Motion

- 滚动时轻微 parallax 或 sticky badge。
- hover 以透明度、下划线、细线位移为主。
- 不用弹跳、玻璃拟态、炫彩渐变或大型 3D 旋转。
- 支持 `prefers-reduced-motion`。

### Accessibility

- 蓝白反差强, 但小号等宽字不能低于 11px, 移动端正文建议至少 12px。
- 白底反相区保持蓝字高对比, 不用低透明文字承载关键信息。
- CTA、导航和平台按钮必须可键盘 focus, hover 效果也要有 focus-visible 对应。
- 大标题在移动端允许换行和缩小, 不能横向溢出。
- 视觉资产若为纯装饰可空 alt; 若承载含义, 用 `aria-label` 或周边标题说明。
- 动效必须支持 `prefers-reduced-motion`。

## Components

### Hero

- eyebrow: 等宽小字, 例如 `OPEN SOURCE · LOCAL FIRST`。
- h1: 3 行大标题, 每行 1-3 个词。
- primary CTA: 白底蓝字等宽按钮。
- art: 右侧大幅古典单色图, 可超出容器。

### Showcase

- 大截图或视频放在蓝底舞台上。
- 外层可加轻微白色边框、噪点、低透明叠层。
- 不做现代 SaaS 卡片阴影。

### Platform Cards

- 3 列卡片。
- 背景为蓝底加单色插图。
- 文字居中, 上方小标签, 中间 display 字体, 下方白底按钮。

### Feature Panel

- 白底蓝字。
- 3 列 x 2 行。
- 每个 feature: 编号小标签、两行以内标题、单色图、等宽说明。
- 标题保持古典衬线, 说明保持等宽。

### Footer

- 蓝底。
- 中央一句主标题。
- 大字标作为背景层或底部海报层。
- 只允许少量酸黄作为幽灵字或强调层。

## Content Style

- 文案短, 像碑铭、目录、终端标签。
- 多用名词短语, 少用解释型长段落。
- 标题要有神话感或宣言感, 但不能空泛。
- 功能说明可以技术化, 但每段控制在 1-2 行。

## Do Not Copy

- 不使用来源品牌或原站 logo。
- 不使用原站图片、视频、字体文件。
- 不使用原站下载按钮文案和实际下载链接。
- 不照搬原站完整信息架构。
- 不热链任何来源站点资源。

## Build Instructions

1. 先替换品牌和产品名。
2. 使用 `tokens.css` 作为视觉基础。
3. 如果没有自有图片, 用生成图或 `.art-placeholder` 占位。
4. 保持蓝白双色克制, 不新增彩虹渐变。
5. 桌面端优先形成海报冲击; 移动端改为单列, 标题仍然大但不能溢出。
