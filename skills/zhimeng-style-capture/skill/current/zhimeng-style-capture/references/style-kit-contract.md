# Style Kit Contract

## 目标

把一个可复用艺术风格保存成稳定、可审查、可执行的目录。未来 AI 不需要重新理解原站, 只读风格包就能生成同风格的新页面。

## 标准目录

```text
style-kits/<style-slug>/
├── DESIGN.md
├── tokens.css
├── components.html
├── template.html
└── prompt.md
```

## 文件职责

### DESIGN.md

放风格合同:

- source: 参考来源、采集日期、用途声明。
- design summary: 一段高度概括的风格判断。
- use cases: 适用页面。
- anti-use cases: 不适用页面。
- recognition points: 第一眼识别点。
- tokens: 色彩、字体、布局、图片、动效。
- components: hero、nav、card、feature、footer 等组件语法。
- accessibility: 对比度、响应式、动效降级、语义化结构。
- do not copy: 禁止复制项。
- build instructions: 给后续实现者的落地规则。

### tokens.css

放可执行视觉基础:

- CSS custom properties。
- 基础排版、颜色、间距、线条。
- 关键组件 class。
- 响应式规则。
- `prefers-reduced-motion`。

不能放:

- 远程字体。
- 远程图片。
- 原站资源 URL。
- 第三方品牌变量名。

### components.html

放可复制组件片段。要求:

- 只使用本风格包定义的 class。
- 不热链资源。
- 文案用中性占位或用户项目可替换文案。

### template.html

放可直接打开的单文件模板。要求:

- 不依赖网络。
- 不引用原站资源。
- 具备桌面/移动端基础响应式。
- 能展示这个风格的主要结构。

### prompt.md

放可直接复制给 AI 的复用提示词。要求:

- 明确只迁移视觉语言。
- 明确资产替换规则。
- 明确禁区。
- 有验收清单。

## 命名

- `style-slug` 用英文小写和连字符。
- 用艺术风格名, 不用第三方品牌名。
- 来源品牌只出现在 `DESIGN.md` 的 source 中。

## 证据文件

原始证据允许存在, 但只能放:

- `.firecrawl/`
- 系统临时目录
- 用户明确指定且 Git ignore 的缓存目录

不要放:

- vault 根目录
- 风格包目录
- 任何会被 Git 上传的位置

## Accessibility

每个风格包都必须写可访问性约束:

- 文本和背景必须保持足够对比度。
- 大标题在移动端不能溢出视口。
- CTA 和导航必须可键盘访问。
- 动效必须支持 `prefers-reduced-motion`。
- 图片占位需要有语义说明或 `aria-label`。

## 验收命令

```bash
bash scripts/validate-style-kit.sh
```

通过后才能说风格包结构合格。视觉质量仍需浏览器截图或人工审查补充确认。
