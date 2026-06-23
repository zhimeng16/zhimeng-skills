# GitHub 高星 Skill 借鉴

## 调研对象

检索时间: 2026-06-03。

### obra/superpowers

- URL: https://github.com/obra/superpowers
- 当前 GitHub 页面显示: 216k stars。
- 定位: 面向 coding agents 的组合式 skills + 软件开发方法论。
- 借鉴点:
  - 技能不是单个大提示词, 而是一组可组合、可触发、可验证的工作流。
  - 强调先澄清、再计划、再执行、再 review、再验证。
  - 明确“证据胜过声称”, 完成前必须验证。
  - `writing-skills` 把写 Skill 看成流程文档的 TDD: 先定义压力场景, 再写 Skill, 再验证是否约束住行为。
  - 描述字段只写触发条件, 不总结完整流程, 避免模型只读 description 就跳过正文。

### anthropics/skills

- URL: https://github.com/anthropics/skills
- 当前 GitHub 页面显示: 146k stars。
- 定位: 官方 Agent Skills 示例、规范和模板。
- 借鉴点:
  - 每个 Skill 是自包含文件夹, 核心是 `SKILL.md`。
  - 必需 frontmatter: `name` 和 `description`。
  - 复杂技能可以包含 scripts、references、assets 等配套资源。
  - 示例仓库用于学习模式, 但仍需在自己的环境中测试后再依赖。

### mattpocock/skills

- URL: https://github.com/mattpocock/skills
- 当前 GitHub 搜索摘要显示: 108k stars。
- 定位: 个人真实工程工作流 Skill 集。
- 借鉴点:
  - Skill 要小、尖、可组合, 不要把所有方法论塞进一个巨型 Skill。
  - 个人工作流可以作为公开资产库, 但每个 Skill 必须能独立复制和适配。

## 同题材补充参考

### bergside/typeui

- URL: https://github.com/bergside/typeui
- 定位: 生成、更新和拉取 `SKILL.md` / `DESIGN.md` 设计系统说明。
- 借鉴点:
  - `DESIGN.md` 是可复用设计系统的核心载体。
  - 设计说明应包含 Mission、Brand、Style Foundations、Accessibility、Do/Don't、Expected Behavior。
  - 风格不是只写颜色和字体, 还要写行为预期和禁区。

### nexu-io/open-design

- URL: https://github.com/nexu-io/open-design
- 定位: 面向设计型 skills 的协议和产物规范。
- 借鉴点:
  - `design-system-skill` 的主产物是 `DESIGN.md`。
  - 从品牌 brief、截图或 URL 分析输入, 再生成设计系统和组件预览。
  - 模板型 skill 与原型型 skill 要区分: 一个重用模板, 一个从设计系统生成新页面。

### garrytan/gstack design skills

- URL: https://github.com/garrytan/gstack
- 定位: 设计审查、浏览器快照、视觉 mockup 和质量门禁。
- 借鉴点:
  - 截图、mockup、比较板等是用户数据, 不能随便污染项目目录。
  - 浏览器/视觉检查要有明确落点和质量门禁。
  - 对本 Skill 的转化: 原站证据进 ignore 缓存, 风格包只放整理后的合同和模板。

## 本 Skill 采用的设计决策

1. 保持一个入口 Skill: `zhimeng-style-capture`。
2. 把每个艺术风格拆成独立 `style-kit`, 避免 Skill 本体膨胀。
3. `SKILL.md` 只放核心边界、模式和入口; 细节放 `references/`。
4. 每个风格包必须有可执行 token、组件片段、模板和复用提示词。
5. 每个 `DESIGN.md` 必须包含 Accessibility/可访问性, 避免纯视觉复刻变成不可用页面。
6. 添加 `scripts/validate-style-kit.sh` 做静态验收, 把能机械检查的约束自动化。
7. 把版权隔离和证据落点写进硬规则: 不提交原站截图、原图、logo、视频、字体文件。

## 未采用的点

- 不采用 Superpowers 的安装/插件分发体系: 用户明确要求只放在 `SKill Creation` 目录下。
- 不引入第三方 installer: 这个资产包不需要安装。
- 不做子 Skill 爆炸: 当前先保留一个捕获/复用入口, 风格差异放在 style-kit 层。
