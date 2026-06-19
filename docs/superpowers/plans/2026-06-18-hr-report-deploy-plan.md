# HR Report GitHub Pages 部署实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 复用现有 2023 年报数据, 通过 `build_report.py` 生成单文件交互式 HTML, 部署到公开 GitHub Pages 仓库 `somAzzz/tcfd-report`, 拿到 `https://somAzzz.github.io/tcfd-report/` 线上 URL。

**Architecture:** 端到端执行链: 本地 JSONL → 既有 visualization 包生成 HTML → 一次性 README 修复 (sed) → gh CLI 建仓+推送+启用 Pages → curl 验证。 不修改 visualization 包任何源代码。

**Tech Stack:** Python ≥ 3.12 (uv), Plotly 5+ (base64 inline), Jinja2, matplotlib, NetworkX, gh CLI ≥ 2.0, Git over SSH。

**Worktree:** 本任务为纯部署操作 (无源代码修改), 不创建独立 worktree, 在 main 分支直接执行。 唯一可能的本地修改是更新 README.md 中的部署 URL 章节, 这属于 main 分支允许的文档更新。

**Spec reference:** `doc/superpowers/specs/2026-06-18-hr-report-deploy-design.md` (commit `5440ed5`)

---

## File Structure

| 路径 | 性质 | 责任 |
|---|---|---|
| `scripts/build_report.py` | 已存在, 只读 | orchestrator (调 5 个 visualization 模块 + check_leakage) |
| `scripts/check_leakage.py` | 已存在, 只读 | 隐私泄漏校验 (公司名 + 危险模式) |
| `src/tcfd_extractor/visualization/*.py` | 已存在, 只读 | 8 个模块 (anonymize / data_loader / chart_builders / static_charts / module_graph / html_assembler / template / translations) |
| `output/evaluate_cooccurrence/2023/results.jsonl` | 已存在, 只读 | 2023 单年聚合数据, 报告输入 |
| `output/report/index.html` | 本次新增 (gitignored) | 单文件交互式报告, 含 3 个 Plotly + 1 个 matplotlib + 1 个 SVG |
| `output/report/README.md` | 本次新增 (gitignored) | build_report.py 生成的 README, 需 sed 修复 |
| `output/report/.nojekyll` | 本次新增 (gitignored) | 禁用 GitHub Pages Jekyll 处理 |
| `somAzzz/tcfd-report` | 外部 (GitHub 公开仓) | 部署目标, 推送后由 gh CLI 创建 |

**无新增源代码文件**。 整个流程是"运行既有脚本 + shell 修复 + gh CLI 部署"。

---

## Chunk 1: Pre-flight 环境校验

**Files:** 无 (纯只读检查)

### Task 1.1: 校验 gh CLI 认证与协议

- [ ] **Step 1: 验证 gh 已安装并登录**

Run: `gh --version && gh auth status 2>&1`
Expected:
- `gh version 2.x.x` (任意 2.x 即可)
- `Logged in to github.com account somAzzz (keyring)`
- `Active account: true`
- `Git operations protocol: ssh`
- Token scopes 含 `repo` 和 `admin:repo`

- [ ] **Step 2: 若未登录或协议不是 SSH, 中止并提示**

(只在 Step 1 输出不符合预期时执行)
```bash
gh auth login --git-protocol ssh --scopes "repo,admin:repo,workflow,read:org"
```

### Task 1.2: 校验 SSH key 在 GitHub 已注册

- [ ] **Step 1: 测试 SSH 认证**

Run: `ssh -T git@github.com 2>&1 | head -3`
Expected: `Hi somAzzz! You've successfully authenticated, but GitHub does not provide shell access.`

- [ ] **Step 2: 若认证失败, 添加公钥**

(只在 Step 1 失败时执行)
```bash
# 检查是否有现有 key
ls -la ~/.ssh/id_*.pub
# 若无, 生成 (跳过已有)
ssh-keygen -t ed25519 -C "$(git config user.email)"
# 添加到 GitHub
gh ssh-key add ~/.ssh/id_ed25519.pub --title "$(hostname)-$(date +%Y%m%d)"
# 重试
ssh -T git@github.com
```

### Task 1.3: 校验输入数据存在

- [ ] **Step 1: 验证 2023 JSONL 存在且非空**

Run: `ls -la output/evaluate_cooccurrence/2023/results.jsonl && wc -l output/evaluate_cooccurrence/2023/results.jsonl`
Expected:
- 文件存在, 大小 > 1KB
- 行数 > 100 (2023 年应有 100+ 家公司记录)

- [ ] **Step 2: 验证 summary.md 存在**

Run: `test -f output/evaluate_cooccurrence/2023/summary.md && echo "summary.md OK"`
Expected: `summary.md OK`

### Task 1.4: 校验当前工作树状态

- [ ] **Step 1: 检查 git 状态**

Run: `git status --short && git log -1 --oneline`
Expected:
- 仅 `.gitignore` 修改可接受 (本会话先前未提交)
- 其它任何未提交改动 → 先 `git stash` 或 `git commit`
- HEAD 应该是 `5440ed5` (spec commit) 之后, 或 spec commit 本身

- [ ] **Step 2: 确认在 main 分支 (硬约束)**

Run:
```bash
git branch --show-current | grep -q '^main$' || { echo "ABORT: not on main branch"; exit 1; }
```
Expected: 无输出 (静默通过); 失败则中止整个计划

- [ ] **Step 3: 提交 (若有) .gitignore 修改**

(只在 Step 1 显示 `.gitignore` 修改时执行)
```bash
git diff .gitignore | head -30   # 查看改动是否合理
git add .gitignore
git commit -m "chore: .gitignore 增量更新"
```

### Task 1.5: 校验 visualization 包可导入

- [ ] **Step 1: 触发模块导入**

Run: `PYTHONPATH=src uv run python -c "from tcfd_extractor.visualization.html_assembler import assemble_html; from tcfd_extractor.visualization.data_loader import load_year; print('imports OK')"`
Expected: `imports OK`

- [ ] **Step 2: 若导入失败, 检查 venv**

```bash
uv sync --dev
```

### Task 1.6: Chunk 1 提交 (如有变更)

- [ ] **Step 1: 提交 pre-flight 期间任何产生的变更**

(若整个 Chunk 1 无任何修改, 跳过此步)
```bash
git status --short   # 确认无残留
# 若有, 按常规提交
```

---

## Chunk 2: 运行 build_report.py 生成报告

**Files:** `output/report/index.html`, `output/report/README.md`, `output/report/.nojekyll` (新增, gitignored)

### Task 2.1: 跑构建脚本

- [ ] **Step 1: 执行 build_report.py**

Run: `uv run python scripts/build_report.py --output output/report/ 2>&1 | tee /tmp/build_report.log`
Expected 关键输出行:
- `Building refactor bar chart...`
- `Building module graph SVG (via AST discovery)...`
- `Assembling HTML...`
- `Wrote output/report/index.html (XXX,XXX chars)`
- `Wrote output/report/README.md`
- `Wrote output/report/.nojekyll`
- `Running leakage check...`
- `✅ Build complete. Report at: output/report/index.html`
- 退出码 = 0

- [ ] **Step 2: 检查退出码**

Run: `echo "exit: $?"`
Expected: `exit: 0`

### Task 2.2: 若 build_report.py 失败 (泄漏检查未过)

(只在 Task 2.1 Step 2 不为 0 时执行)

- [ ] **Step 1: 查看完整日志**

Run: `cat /tmp/build_report.log | tail -50`
查找包含 `LEAK` 或具体公司名的行

- [ ] **Step 2: 决定修复方向**

- 若泄漏来自 `output/evaluate_cooccurrence/2023/results.jsonl` 中残留公司名: 修 `src/tcfd_extractor/visualization/anonymize.py` (不在本计划范围, 转交)
- 若泄漏来自 `check_leakage.py` 误报 (如 Plotly/matplotlib 脚本片段): 修 `scripts/check_leakage.py` (不在本计划范围, 转交)

**中止本计划, 等待修复后重跑 Task 2.1。**

### Task 2.3: 验证产物文件

- [ ] **Step 1: 三个文件都存在**

Run: `ls -la output/report/`
Expected:
- `index.html` (大小通常 2-10 MB, 含 inline chart)
- `README.md` (约 1-2 KB)
- `.nojekyll` (空文件)

- [ ] **Step 2: index.html 头部和尾部 sanity check**

Run: `head -c 200 output/report/index.html && echo "" && tail -c 200 output/report/index.html`
Expected:
- 头部含 `<!DOCTYPE html>` 或 `<html`
- 尾部含 `</html>`

- [ ] **Step 3: index.html 大小 sanity floor**

Run: `wc -c output/report/index.html`
Expected: > 1,000,000 (含 3 个 Plotly + 1 个 SVG + 1 个 matplotlib, 合理最小 1MB; 若 < 500KB 视为内容缺失, 中止调查)

- [ ] **Step 4: 验证关键 chart inline 数据存在**

Run: `grep -c "Plotly.newPlot\|<svg\|data:image/png;base64" output/report/index.html`
Expected: 至少 3 (3 个 Plotly + 1 个 SVG + 1 个 matplotlib base64)

- [ ] **Step 5: 提交 (若有意) 文档类变更**

本步骤不产生 git 提交 — output/ 在 .gitignore 中, 不入版本库。

---

## Chunk 3: Post-build README 修复

**Files:** `output/report/README.md` (修改, gitignored)

**原因:** `scripts/build_report.py` 写出的 README 模板硬编码 `https://<username>.github.io/tcfd-hr-report/` 和仓库名 `tcfd-hr-report`, 与本计划目标 `tcfd-report` 不一致, 必须在推送前修复。

### Task 3.1: 执行 sed 替换

- [ ] **Step 1: 修复前先看现状**

Run: `grep -n "tcfd-hr-report\|<username>\|tcfd-report\|somAzzz" output/report/README.md`
Expected: README 中出现 `tcfd-hr-report` (硬编码) 和 `<username>` (占位符)

- [ ] **Step 2: 执行 sed**

Run:
```bash
sed -i.bak \
  -e 's|tcfd-hr-report|tcfd-report|g' \
  -e 's|<username>|somAzzz|g' \
  output/report/README.md
```

> **平台注意**: 以上是 GNU sed 语法 (Linux 适用)。 若在 macOS 上执行, 需改为 `sed -i '' -e '...' ...` (BSD sed 要求 `''` 占位)。 本计划目标环境是 Linux, 保持 GNU 语法。

- [ ] **Step 3: 验证替换成功**

Run:
```bash
echo "--- 替换后应命中 tcfd-report: ---"
grep -c "tcfd-report" output/report/README.md
echo "--- 替换后应零命中 tcfd-hr-report: ---"
grep -c "tcfd-hr-report" output/report/README.md && echo "FAIL: 还有 tcfd-hr-report 残留" || echo "OK"
echo "--- 替换后应零命中 <username>: ---"
grep -c "<username>" output/report/README.md && echo "FAIL: 还有 <username> 残留" || echo "OK"
echo "--- 应命中 somAzzz: ---"
grep -c "somAzzz" output/report/README.md
```

Expected:
- `tcfd-report` 命中 ≥ 1
- `tcfd-hr-report` 零命中 (grep -c 返回 0 且无 FAIL)
- `<username>` 零命中
- `somAzzz` 命中 ≥ 1

- [ ] **Step 4: 删除备份**

Run: `rm output/report/README.md.bak`

- [ ] **Step 5: 显示最终 README**

Run: `cat output/report/README.md`
确认 URL 是 `https://somAzzz.github.io/tcfd-report/`, 仓库名是 `tcfd-report`

---

## Chunk 4: Pre-push 二次验证

**Files:** 无 (只读检查)

### Task 4.1: 独立跑 check_leakage.py

- [ ] **Step 1: 二次验证泄漏检查**

Run: `uv run python scripts/check_leakage.py output/report/index.html 2>&1`
Expected:
- 退出码 = 0
- 输出恰好是: `✅ Leakage check passed for output/report/index.html`
- (若输出 "LEAK" 字样或公司名, 中止调查)

### Task 4.2: 列出推送内容

- [ ] **Step 1: 确认推什么**

Run: `ls -la output/report/ && du -sh output/report/`
Expected:
- 3 个文件 (index.html, README.md, .nojekyll)
- 总大小 < 20 MB (Pages 单仓 1 GB 限额足够)

- [ ] **Step 2: 排除 macOS 垃圾文件**

Run: `find output/report/ -name ".DS_Store" -delete`
(若有, 删除; 实际 Linux 仓库一般没有)

### Task 4.3: 抓取 index.html 的关键元数据

- [ ] **Step 1: 检查页面 title 和 section 标题**

Run: `grep -oE "<title>[^<]+</title>" output/report/index.html | head -3`
Expected: 含 "TCFD" 或 "Demo" 关键词

- [ ] **Step 2: 统计 5 个 section 的图表**

Run: `grep -c "id=\"section-" output/report/index.html`
Expected: ≥ 4 (donut / pipeline / trend+bar / refactor) + 1 details (tech deep dive)

---

## Chunk 5: 创建 GitHub 公开仓库并推送

**Files:** 外部 `somAzzz/tcfd-report` (公网产物, 不在本仓)

### Task 5.1: 检查仓库名是否已存在

- [ ] **Step 1: API 检查**

Run: `gh api repos/somAzzz/tcfd-report 2>&1 | head -20`
Expected:
- 成功: 仓库已存在 (状态 200), 列出 README 等
- 失败: 仓库不存在 (状态 404) — 这是预期情况, 进入 Task 5.2

### Task 5.2: 仓库已存在时 (Task 5.1 Step 1 状态 200)

(只在 Task 5.1 Step 1 显示仓库已存在时执行)

- [ ] **Step 1: 列出已有内容**

Run: `gh api repos/somAzzz/tcfd-report/contents/ | jq -r '.[].name'`
Expected: 列出 index.html, README.md, .nojekyll 等

- [ ] **Step 2: 决定处理方式**

- 若是上次本计划部署残留: 删除后重建
  ```bash
  gh repo delete somAzzz/tcfd-report --yes
  ```
- 若是非本计划的他人仓库: 中止, 改用 `tcfd-report-v2` 名称 (需回退到 Task 5.1 Step 1 重新检查 `tcfd-report-v2`)

### Task 5.3: 创建仓库并推送 (干净状态)

**重要前置**: `output/report/` 不是 git 仓库, `gh repo create --source` 要求源是 git 仓库, 因此必须先 `git init` 并做首次提交。 全部使用绝对路径避免 cwd 漂移。

- [ ] **Step 1: 在 output/report/ 中初始化 git 仓库并首次提交**

Run:
```bash
cd /home/bo/projects/python/frequency_analyzer
set -e  # 任一命令失败立即停
git init output/report
git -C output/report add -A
git -C output/report -c user.email="noreply@github.com" -c user.name="somAzzz" commit -m "init: HR report artifacts (index.html, README.md, .nojekyll)"
```

Expected:
- `Initialized empty Git repository in /home/bo/projects/python/frequency_analyzer/output/report/.git/`
- `1 file changed, ...` (或 3 files)
- 退出码 = 0

- [ ] **Step 2: 创建 + 推送仓库 (使用绝对路径)**

Run:
```bash
cd /home/bo/projects/python/frequency_analyzer
gh repo create tcfd-report --public \
  --description "TCFD Project Demo — interactive single-file HTML report" \
  --source /home/bo/projects/python/frequency_analyzer/output/report \
  --push
```

Expected 关键输出:
- `✓ Created repository somAzzz/tcfd-report on GitHub`
- `✓ Pushed commits to https://github.com/somAzzz/tcfd-report.git`

- [ ] **Step 3: 验证仓库可见**

Run: `gh repo view somAzzz/tcfd-report --json name,visibility,url --jq '"name=" + .name, "visibility=" + .visibility, "url=" + .url'`
Expected:
- `name=tcfd-report`
- `visibility=PUBLIC`
- `url=https://github.com/somAzzz/tcfd-report`

- [ ] **Step 4: 验证 index.html 已推送**

Run: `gh api repos/somAzzz/tcfd-report/contents/index.html --jq '.name + " size=" + (.size|tostring) + " url=" + .html_url'`
Expected: `index.html size=NNNNNNN url=https://github.com/somAzzz/tcfd-report/blob/main/index.html` (size > 500000)

---

## Chunk 6: 启用 GitHub Pages

**Files:** 外部 `somAzzz/tcfd-report` Pages 设置

**重要**: `gh repo edit` **不支持** `--enable-pages` 或 `--pages-source` flags。 GitHub Pages 启用必须通过 REST API (`POST /repos/{owner}/{repo}/pages`)。

### Task 6.1: 启用 Pages (走 REST API)

- [ ] **Step 1: POST 到 Pages API**

Run:
```bash
gh api -X POST repos/somAzzz/tcfd-report/pages \
  -f 'source[branch]=main' \
  -f 'source[path]=/'
```

Expected:
- 退出码 = 0
- API 响应 JSON 含 `html_url` 字段, 值形如 `https://somAzzz.github.io/tcfd-report/`
- 若响应 409 Conflict (Pages 已启用), 视为幂等成功, 继续

- [ ] **Step 2: 验证 Pages 配置 (用 `html_url` 字段名, 不是 `url`)**

Run:
```bash
gh api repos/somAzzz/tcfd-report/pages --jq \
  '"html_url=" + .html_url, "branch=" + .source.branch, "path=" + .source.path, "status=" + (.status // "null")'
```

Expected:
- `html_url=https://somAzzz.github.io/tcfd-report/`
- `branch=main`
- `path=/`
- `status=building` 或 `built` (首次部署可能为 `null`, 不视为失败, Chunk 7 curl 会最终验证)

---

## Chunk 7: 验证线上 URL

**Files:** 无 (网络请求)

### Task 7.1: curl 验证

- [ ] **Step 1: 第一次 curl (可能 404)**

Run: `curl -I -s -o /dev/null -w "%{http_code}\n" https://somAzzz.github.io/tcfd-report/`
Expected (立即): `404` (Pages 首次部署有传播延迟, 这是正常的)

- [ ] **Step 2: 等待 60-120s 后重试**

Run:
```bash
for i in 1 2 3; do
  sleep 60
  code=$(curl -I -s -o /dev/null -w "%{http_code}" https://somAzzz.github.io/tcfd-report/)
  echo "Attempt $i (after $((i*60))s): HTTP $code"
  if [ "$code" = "200" ]; then
    echo "✅ Pages is live"
    break
  fi
done
```

Expected (最终): HTTP `200`

- [ ] **Step 3: 若 3 次重试仍 404, 等待更长**

(GitHub Pages 首次证书签发可能 5-10 分钟)
```bash
for i in 1 2 3 4 5; do
  sleep 90
  code=$(curl -I -s -o /dev/null -w "%{http_code}" https://somAzzz.github.io/tcfd-report/)
  echo "Long-wait attempt $i: HTTP $code"
  if [ "$code" = "200" ]; then
    echo "✅ Pages is live"
    break
  fi
done
```

Expected: 最终返回 200; 若仍 404, 手动访问 https://github.com/somAzzz/tcfd-report/settings/pages 检查

- [ ] **Step 4: 抓取页面 head 验证**

Run: `curl -s https://somAzzz.github.io/tcfd-report/ | head -c 500`
Expected: 含 `<!DOCTYPE html>` 或 `<html` 标签

---

## Chunk 8: 更新项目 README 并最终提交

**Files:** `README.md` 和 `README.en.md` (中英双版)

### Task 8.1: 更新 README 添加部署链接

**插入位置定位**: README.md 中存在 `## 可视化报告` 章节 (line 211, 标题不含 "HR" 前缀, 但 TOC 锚点为 `#hr-可视化报告`)。 英文版对应 `## Visualization Report` 章节。 在线链接应放在该章节标题下方第一段说明之上。

- [ ] **Step 1: 在 README.md 的 `## 可视化报告` 标题下插入链接**

Run: 用 Edit 工具, 在 `## 可视化报告` (line 211) 之后紧跟插入:

```markdown
**🌐 在线演示**: https://somAzzz.github.io/tcfd-report/
```

(空一行后接原 `\`visualization\` 包内置...` 段)

- [ ] **Step 2: 在 README.en.md 的 `## Visualization Report` 标题下插入链接**

Run: 用 Edit 工具, 在 `## Visualization Report` 标题之后紧跟插入:

```markdown
**🌐 Live demo**: https://somAzzz.github.io/tcfd-report/
```

(空一行后接原段落)

### Task 8.2: 提交文档更新

- [ ] **Step 1: git add + commit**

Run:
```bash
git add README.md README.en.md
git diff --cached --stat
git commit -m "docs(README): 添加 tcfd-report 线上演示链接 (https://somAzzz.github.io/tcfd-report/)"
```

Expected:
- diff stat 显示 2 个文件, 仅几行新增
- commit 创建成功

- [ ] **Step 2: 推送到 origin (可选)**

(若用户希望同步到 GitHub 主仓才执行, 否则跳过)
Run: `git push origin main`
Expected: `* [new branch] main -> main` 或 `Everything up-to-date`

---

## Final Verification (整计划完成度检查)

- [ ] **Step 1: 跑全部 verification 命令**

```bash
echo "=== 1. build_report.py 退出码 ==="
test -f output/report/index.html && echo "✅ index.html 存在" || echo "❌ index.html 缺失"

echo "=== 2. Post-build README 修复 ==="
grep -q "tcfd-report" output/report/README.md && echo "✅ tcfd-report 已写入" || echo "❌"
! grep -q "tcfd-hr-report" output/report/README.md && echo "✅ 无 tcfd-hr-report 残留" || echo "❌"

echo "=== 3. 仓库创建 ==="
gh repo view somAzzz/tcfd-report --json visibility -q '.visibility' | grep -q PUBLIC && echo "✅ 仓库 PUBLIC" || echo "❌"

echo "=== 4. 推送完成 ==="
gh api repos/somAzzz/tcfd-report/contents/index.html -q '.name' | grep -q index.html && echo "✅ index.html 已推送" || echo "❌"

echo "=== 5. Pages 启用 ==="
gh api repos/somAzzz/tcfd-report/pages -q '.html_url' | grep -q "tcfd-report" && echo "✅ Pages URL 正确" || echo "❌"

echo "=== 6. 站点可达 ==="
code=$(curl -I -s -o /dev/null -w "%{http_code}" https://somAzzz.github.io/tcfd-report/)
[ "$code" = "200" ] && echo "✅ 线上 200" || echo "⚠️ 线上 $code (可能仍在部署中)"
```

- [ ] **Step 2: 报告最终状态给用户**

将以下信息汇总回复:
- 部署 URL: `https://somAzzz.github.io/tcfd-report/`
- 仓库: `https://github.com/somAzzz/tcfd-report`
- 8 个 Chunk 完成状态
- 任何已知问题 (如 .gitignore 修改, Pages 部署延迟等)
- (后续会话项目见 spec §9, 不在本次范围)

---

## 已知边界 (Out of Plan)

本计划明确**不做**以下事项, 留给后续任务:

1. ❌ 修改 `scripts/build_report.py` (把 repo 名作为 CLI 参数)
2. ❌ 修改 `src/tcfd_extractor/visualization/` 包任何文件
3. ❌ 接入 GH Actions 做自动部署
4. ❌ 用本地 Qwen 模型生成 AI 摘要
5. ❌ 多语言切换 (i18n 切换中/英报告)
6. ❌ 自定义域名

详见 spec §8 已知遗留问题 + §9 后续。

### Spec 修订 (随本次计划一起提交)

由于 v1 spec 错误地推荐了 `gh repo edit --enable-pages` (该 flags 在 gh CLI 中不存在), 已在 spec 修复版 (commit `8c7017` 之后的下一次提交) 中改为 `gh api -X POST .../pages`。 旧 spec `2026-06-18-hr-visualization-design.md` (29KB) 仍推荐 `tcfd-hr-report` 仓库名, 本计划**不**修改, 后续任务处理。
