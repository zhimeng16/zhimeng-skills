#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null || (cd "$ROOT/../../../.." && pwd))"
PROJECT_ROOT="$(cd "$ROOT/../../.." && pwd)"
LOCAL_HARNESS_ROOT="${ZHIMENG_STYLE_CAPTURE_HARNESS_ROOT:-"$ROOT/../../.."}"
VALIDATE_LOCAL_HARNESS="${VALIDATE_LOCAL_HARNESS:-0}"
STATUS=0
SOURCE_BRAND_PATTERN="${SOURCE_BRAND_PATTERN:-}"
REMOTE_ASSET_PATTERN="(src|href|srcset|poster)[[:space:]]*=[[:space:]]*['\"]?[[:space:]]*(https?:)?//|@import[[:space:]]+(url\\()?['\"]?[[:space:]]*(https?:)?//|url[[:space:]]*\\([[:space:]]*['\"]?[[:space:]]*(https?:)?//"

fail() {
  printf 'FAIL %s\n' "$1"
  STATUS=1
}

pass() {
  printf 'PASS %s\n' "$1"
}

require_file() {
  local path="$1"
  if [ -f "$path" ]; then
    pass "file exists: ${path#$ROOT/}"
  else
    fail "missing file: ${path#$ROOT/}"
  fi
}

require_grep() {
  local pattern="$1"
  local path="$2"
  local label="$3"
  if grep -Eq "$pattern" "$path"; then
    pass "$label"
  else
    fail "$label"
  fi
}

for path in \
  "$ROOT/SKILL.md" \
  "$ROOT/references/style-kit-contract.md" \
  "$ROOT/references/github-skill-research.md" \
  "$ROOT/examples/capture-request.md" \
  "$ROOT/examples/reuse-request.md"; do
  require_file "$path"
done

require_grep '^---$' "$ROOT/SKILL.md" "SKILL.md has YAML frontmatter fence"
require_grep '^name: zhimeng-style-capture$' "$ROOT/SKILL.md" "SKILL.md has expected name"
require_grep '^description: Use (only )?when ' "$ROOT/SKILL.md" "description starts with trigger condition"
require_grep '不在 vault 根目录生成临时截图' "$ROOT/SKILL.md" "root garbage guard exists"
require_grep 'scripts/validate-style-kit.sh' "$ROOT/SKILL.md" "validation script referenced"
require_grep '复用已收藏风格' "$ROOT/SKILL.md" "saved-style reuse trigger exists"
require_grep '提取新网站风格' "$ROOT/SKILL.md" "new-site style extraction trigger exists"
require_grep '复用风格库|复用风格包|之前喜欢/收藏的模板|某个 `style-kit`' "$ROOT/SKILL.md" "positive reuse trigger words exist"
require_grep 'copy、down、提取、捕获、归档成 `style-kit`' "$ROOT/SKILL.md" "positive extraction trigger words exist"
require_grep '帮我做一个网站|设计一个 landing page|做一个前端页面' "$ROOT/SKILL.md" "ordinary website/frontend requests are excluded"
require_grep '把这篇 Markdown 转 HTML|结构化为 HTML|生成报告 HTML' "$ROOT/SKILL.md" "ordinary markdown/html rendering requests are excluded"
require_grep '先列出现有 `style-kit` 并询问用哪一个' "$ROOT/SKILL.md" "unspecified style-kit asks for template choice"
require_grep 'zhimeng-md-html' "$ROOT/SKILL.md" "zhimeng-md-html conflict boundary exists"
require_grep 'web-design-engineer|frontend-design' "$ROOT/SKILL.md" "frontend design conflict boundary exists"
require_grep 'firecrawl-website-design-clone' "$ROOT/SKILL.md" "firecrawl design clone boundary exists"
require_grep 'style-kits/' "$ROOT/examples/capture-request.md" "capture example points to asset style-kits path"

if [ "$VALIDATE_LOCAL_HARNESS" = "1" ]; then
  DOC_MD="$LOCAL_HARNESS_ROOT/docs/使用说明.md"
  DOC_HTML="$LOCAL_HARNESS_ROOT/docs/使用说明.html"
  PRODUCT_DOC="$LOCAL_HARNESS_ROOT/docs/产品说明.md"
  TEST_METHOD="$LOCAL_HARNESS_ROOT/tests/测试方法.md"
  ACCEPTANCE="$LOCAL_HARNESS_ROOT/tests/验收标准.md"

  require_file "$DOC_MD"
  require_file "$DOC_HTML"
  require_file "$PRODUCT_DOC"
  require_file "$TEST_METHOD"
  require_file "$ACCEPTANCE"

  require_grep '不触发场景' "$DOC_MD" "usage guide has non-trigger scenarios"
  require_grep '不触发场景' "$DOC_HTML" "usage guide HTML has non-trigger scenarios"
  require_grep '不会自动安装到 `.agents/skills`、`.claude/skills` 或 `~/.codex/skills`' "$DOC_MD" "usage guide states asset-only no auto install"
  require_grep '不会自动安装到' "$DOC_HTML" "usage guide HTML states asset-only no auto install"
  require_grep '复用已收藏风格|复用已有风格' "$DOC_HTML" "usage guide HTML has saved-style reuse trigger"
  require_grep '提取新风格|提取新网站风格' "$DOC_HTML" "usage guide HTML has extraction trigger"
  require_grep '帮我做一个网站' "$DOC_HTML" "usage guide HTML excludes ordinary website request"
  require_grep '把这篇 Markdown 转 HTML' "$DOC_HTML" "usage guide HTML excludes markdown to html request"
  require_grep '设计一个 landing page' "$DOC_HTML" "usage guide HTML excludes landing page request"
  require_grep '做一个前端页面' "$DOC_HTML" "usage guide HTML excludes frontend page request"
  require_grep '至少 3 个子 Agent' "$ACCEPTANCE" "multi-agent verification standard exists"
  require_grep 'T1 触发规则' "$TEST_METHOD" "test method has trigger scenario group"
  require_grep 'T4 版权与污染' "$TEST_METHOD" "test method has copyright and pollution group"
  require_grep '风格包 slug 和 `DESIGN.md` 一级标题不能使用来源品牌名' "$TEST_METHOD" "test method covers brand-neutral slug and title"
  require_grep '允许 renderer 自带主题 CSS 和 Mermaid CDN' "$TEST_METHOD" "test method documents docs HTML renderer asset policy"
  require_grep '用户明确要求复用已归档风格做新页面' "$PRODUCT_DOC" "product doc narrows new-page reuse wording"
  require_grep '普通“做网站/做 HTML/做 landing page”不触发' "$PRODUCT_DOC" "product doc excludes ordinary page requests"
else
  pass "local harness checks skipped; set VALIDATE_LOCAL_HARNESS=1 to include this skill project's docs/tests"
fi

BROAD_TRIGGER_PATTERN="$(printf '%s|%s|%s|%s|%s' '设计页''时问' '做网站''时问' '普通设计请求.*询问风格库' '设计.*主动.*风格库' '做网站.*风格库|默认.*style-kit')"
if grep -Eq "$BROAD_TRIGGER_PATTERN" "$ROOT/SKILL.md"; then
  fail "old broad trigger wording remains in runtime package"
elif [ "$VALIDATE_LOCAL_HARNESS" = "1" ] && grep -Eq "$BROAD_TRIGGER_PATTERN" "$DOC_MD" "$DOC_HTML" "$PRODUCT_DOC"; then
  fail "old broad trigger wording remains in local harness"
else
  pass "old broad trigger wording removed"
fi

AMBIGUOUS_CAPTURE_PATTERN="$(printf '%s|%s' '放进''艺术网站风格捕获与复用 Skill' '放进'' Skill')"
if grep -Eq "$AMBIGUOUS_CAPTURE_PATTERN" "$ROOT/examples/capture-request.md"; then
  fail "old ambiguous capture wording remains in runtime package"
elif [ "$VALIDATE_LOCAL_HARNESS" = "1" ] && grep -Eq "$AMBIGUOUS_CAPTURE_PATTERN" "$DOC_MD" "$DOC_HTML"; then
  fail "old ambiguous capture wording remains in local harness"
else
  pass "old ambiguous capture wording removed"
fi

if find "$PROJECT_ROOT" -mindepth 1 -maxdepth 1 \( -type f -o -type d \) ! -name '.*' \( -iname '*screenshot*' -o -iname '*screen*' -o -iname '*capture*' -o -iname '*scrape*' -o -iname '*branding*' -o -iname '*source-brand*' -o -iname '*style-kit*' -o -iname '*style-capture*' -o -iname '*使用说明*' \) | grep -q .; then
  fail "skill project root contains visible temporary style/source files"
else
  pass "skill project root has no visible temporary style/source files"
fi

if grep -Eq '^description: .*DESIGN.md|^description: .*tokens.css|^description: .*components.html|^description: .*template.html' "$ROOT/SKILL.md"; then
  fail "description should not summarize workflow artifacts"
else
  pass "description avoids workflow summary"
fi

for kit in "$ROOT"/style-kits/*; do
  [ -d "$kit" ] || continue
  kit_name="$(basename "$kit")"
  case "$kit_name" in
    *[!a-z0-9-]*)
      fail "style-kit slug is not lowercase kebab-case: $kit_name"
      ;;
    *)
      pass "style-kit slug is lowercase kebab-case: $kit_name"
      ;;
  esac
  if [ -n "$SOURCE_BRAND_PATTERN" ] && printf '%s\n' "$kit_name" | grep -Eiq "$SOURCE_BRAND_PATTERN"; then
    fail "style-kit slug uses source brand: $kit_name"
  elif [ -z "$SOURCE_BRAND_PATTERN" ]; then
    pass "$kit_name slug brand check skipped; set SOURCE_BRAND_PATTERN to enforce source-brand names"
  else
    pass "$kit_name slug is brand-neutral"
  fi

  for file in DESIGN.md tokens.css components.html template.html prompt.md; do
    require_file "$kit/$file"
  done

  require_grep '^# ' "$kit/DESIGN.md" "$kit_name DESIGN.md has title"
  design_title="$(grep -E '^# ' "$kit/DESIGN.md" | head -n 1)"
  if [ -n "$SOURCE_BRAND_PATTERN" ] && printf '%s\n' "$design_title" | grep -Eiq "$SOURCE_BRAND_PATTERN"; then
    fail "$kit_name DESIGN.md title uses source brand"
  elif [ -z "$SOURCE_BRAND_PATTERN" ]; then
    pass "$kit_name DESIGN.md title brand check skipped; set SOURCE_BRAND_PATTERN to enforce source-brand names"
  else
    pass "$kit_name DESIGN.md title is brand-neutral"
  fi
  require_grep '## Do Not Copy|## 禁区|## 禁止' "$kit/DESIGN.md" "$kit_name has copy boundary"
  require_grep 'Accessibility|可访问|无障碍' "$kit/DESIGN.md" "$kit_name DESIGN.md has accessibility guidance"
  require_grep 'prefers-reduced-motion' "$kit/tokens.css" "$kit_name tokens support reduced motion"
  require_grep '<!doctype html>|<!DOCTYPE html>' "$kit/template.html" "$kit_name template is complete HTML"
  require_grep '验收清单|checklist|Checklist' "$kit/prompt.md" "$kit_name prompt has checklist"

  if grep -R -niE "$REMOTE_ASSET_PATTERN" "$kit" >/tmp/zhimeng-style-capture-remote-assets.txt 2>/dev/null; then
    fail "$kit_name contains remote or original site asset references"
    cat /tmp/zhimeng-style-capture-remote-assets.txt
  else
    pass "$kit_name has no remote/original asset references"
  fi

  if find "$kit" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.webp' -o -iname '*.svg' -o -iname '*.ico' -o -iname '*.woff' -o -iname '*.woff2' -o -iname '*.ttf' -o -iname '*.otf' -o -iname '*.mp4' -o -iname '*.webm' -o -iname '*.mov' -o -iname '*.zip' -o -iname '*.dmg' -o -iname '*.pkg' \) | grep -q .; then
    fail "$kit_name contains binary media/font/archive assets"
    find "$kit" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.webp' -o -iname '*.svg' -o -iname '*.ico' -o -iname '*.woff' -o -iname '*.woff2' -o -iname '*.ttf' -o -iname '*.otf' -o -iname '*.mp4' -o -iname '*.webm' -o -iname '*.mov' -o -iname '*.zip' -o -iname '*.dmg' -o -iname '*.pkg' \)
  else
    pass "$kit_name has no binary media/font/archive assets"
  fi

  if grep -niE 'animation|transition|scroll-behavior' "$kit/template.html" >/tmp/zhimeng-style-capture-template-motion.txt 2>/dev/null; then
    if grep -qi 'prefers-reduced-motion' "$kit/template.html"; then
      pass "$kit_name template motion has reduced-motion guard"
    else
      fail "$kit_name template has motion without reduced-motion guard"
      cat /tmp/zhimeng-style-capture-template-motion.txt
    fi
  else
    pass "$kit_name template has no motion requiring reduced-motion guard"
  fi

  if [ -n "$SOURCE_BRAND_PATTERN" ] && grep -R -nE "$SOURCE_BRAND_PATTERN" "$kit"/tokens.css "$kit"/components.html "$kit"/template.html "$kit"/prompt.md >/tmp/zhimeng-style-capture-brand-leak.txt 2>/dev/null; then
    fail "$kit_name leaks source brand outside DESIGN.md"
    cat /tmp/zhimeng-style-capture-brand-leak.txt
  elif [ -z "$SOURCE_BRAND_PATTERN" ]; then
    pass "$kit_name executable asset brand check skipped; set SOURCE_BRAND_PATTERN to enforce source-brand leakage"
  else
    pass "$kit_name has no source brand in executable assets/prompts"
  fi
done

if [ "$STATUS" -eq 0 ]; then
  printf 'PASS zhimeng-style-capture validation\n'
else
  printf 'FAIL zhimeng-style-capture validation\n'
fi

exit "$STATUS"
