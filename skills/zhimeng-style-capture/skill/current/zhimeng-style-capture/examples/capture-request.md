# Example: Capture A New Style

用户:

```text
这个网站风格很好: https://example.com
不要复制品牌和原图, 把它的艺术风格 down 下来, 写入本 skill 的 style-kits/。
```

执行:

1. 用浏览器或抓取工具查看桌面/移动端。
2. 把截图和抓取证据放进 `.firecrawl/`。
3. 给风格命名, 例如 `paper-annotation-reading`。
4. 在本 skill 的 `style-kits/` 下创建 `paper-annotation-reading/`。
5. 写 `DESIGN.md`、`tokens.css`、`components.html`、`template.html`、`prompt.md`。
6. 运行 `scripts/validate-style-kit.sh`。
7. 汇报路径、来源、借鉴点和验证结果。

不要:

- 不要把截图放到 vault 根目录。
- 不要把原站图片、logo、字体、视频复制到 style-kit。
- 不要创建 v2 目录逃避修改。
