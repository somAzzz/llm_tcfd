# HR 报告部署到 GitHub Pages — 设计文档

**日期**: 2026-06-18
**作者**: 头脑风暴会话
**状态**: 待 spec 审阅

## 1. 背景与目标

项目已经在 `src/tcfd_extractor/visualization/` 下实现了完整的 HR 演示报告流水线 (8 个 visualization 模块), 配合 `scripts/` 下的 `build_report.py` (orchestrator) 和 `check_leakage.py` (内嵌隐私检查) 共同组成可执行流水线。 该能力已在 `feat/hr-visualization` 分支完成, 合并 commit 为 `340f750`。 报告本身尚未生成, 也没有上线地址。

**目标**: 端到端运行现有 `build_report.py`, 将生成的 `index.html` 部署到 GitHub Pages 公开仓库, 拿到可分享的 URL。

**非目标** (避免范围蔓延):
- 不修改 visualization 包的任何源码 (现状已通过 30+ 单元测试)
- 不切换数据源, 不用本地 Qwen 模型重跑流水线
- 不调整报告主题、布局、配色
- 不引入 GitHub Actions / CI (Pages 直接从 main 分支静态托管)

## 2. 数据源

- **使用**: `output/evaluate_cooccurrence/2023/results.jsonl` (已经存在, 25 年历史数据中只取 2023 单年)
- **不用**: Qwen 重新抽取, 不重跑 cooccurrence 流水线
- **原因**: 2023 年数据已经覆盖 HR 报告所需的全部 5 个 section (donut / trend / bar / refactor / module graph)

## 3. 执行链

```
output/evaluate_cooccurrence/2023/results.jsonl
  └─→ python scripts/build_report.py --output output/report/
        ├─→ tcfd_extractor.visualization.data_loader        (读 JSONL + 聚合)
        ├─→ tcfd_extractor.visualization.chart_builders     (3 个 Plotly 图, base64 inline)
        ├─→ tcfd_extractor.visualization.static_charts      (matplotlib 柱图 + 模块依赖 SVG)
        ├─→ tcfd_extractor.visualization.html_assembler     (组装 HTML)
        └─→ scripts/check_leakage.py                        (内嵌校验, 失败 exit 1)
              ↓ exit 0
       output/report/{index.html, README.md, .nojekyll}
              ↓
       # Post-build fixup: build_report.py 写出的 README.md
       # 硬编码了 https://<username>.github.io/tcfd-hr-report/,
       # 需要在推送前 sed 替换为 tcfd-report
       sed -i 's|tcfd-hr-report|tcfd-report|g; s|<username>|somAzzz|g' \
           output/report/README.md
              ↓
       # 先在 output/report/ 中 git init + 首次提交
       # (因为 --source 要求源是 git 仓库)
       git -C /home/bo/projects/python/frequency_analyzer/output/report init
       git -C .../output/report add -A
       git -C .../output/report commit -m "init: HR report artifacts"
              ↓
       gh repo create tcfd-report --public \
         --source /home/bo/projects/python/frequency_analyzer/output/report \
         --push
              ↓
       # gh repo edit 不支持 --enable-pages, 改用 gh api 调 REST
       gh api -X POST repos/somAzzz/tcfd-report/pages \
         -f 'source[branch]=main' -f 'source[path]=/'
              ↓
       https://somAzzz.github.io/tcfd-report/
```

## 4. 关键决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 仓库名 | `tcfd-report` (替代 `tcfd-hr-report`) | 用户指定 |
| 仓库可见性 | `public` | GitHub Pages 公开托管免费层要求 |
| 推入方式 | `gh repo create --source --push` | gh CLI 一行完成 "建仓 + 推送", 避免手动 git init |
| Pages 来源 | branch=`main`, folder=`/(root)` | 与 `build_report.py` 生成的 `.nojekyll` 一致, 跳过 Jekyll 处理 |
| 仓库宿主 | `somAzzz` | 当前 `gh auth status` 已确认登录 |
| 推送协议 | SSH | gh CLI 当前配置为 SSH, 推 `somAzzz/tcfd-report` 时直接走 `git@github.com` |

## 5. 错误处理

| 失败点 | 检测方式 | 处理 |
|---|---|---|
| `build_report.py` 退出码 ≠ 0 | `$?` 检查 | 中止流程, 不推送; 输出泄漏检查报告让用户先修 |
| `gh repo create` 失败 (同名仓库已存在) | gh CLI stderr | 1) 先 `gh api repos/somAzzz/tcfd-report/contents/` 列出已有内容; 2) 若为空或仅有无关文件, 确认 `gh repo delete somAzzz/tcfd-report` 后重建; 3) 若非空且不属于本任务, 改用新名字 (如 `tcfd-report-v2`) |
| `gh api -X POST repos/.../pages` 失败 (Pages 启用) | gh CLI stderr / API 响应 body | 给出 GitHub Settings → Pages 的手动启用链接, 不阻塞主流程 |
| Push 时 SSH 认证失败 (协议为 SSH) | gh CLI stderr / git stderr | 提示运行 `ssh -T git@github.com` 验证 key 注册; 必要时 `gh ssh-key add ~/.ssh/id_ed25519.pub` 添加公钥 |
| 部署后 URL 404 / 5xx | `curl -I https://somAzzz.github.io/tcfd-report/` | 等待 60-120s 后重试; 首次部署证书签发可能需 5-10 分钟, 最多重试 3 次 |

## 6. 验证

每一步都有显式校验点, 失败立即停:

| 步骤 | 验证 |
|---|---|
| 1. 跑 `build_report.py` | 退出码 = 0 (内置 `check_leakage.py` 已通过); `index.html` 存在 |
| 2. Post-build README 替换 | `grep "tcfd-report" output/report/README.md` 命中; `grep "tcfd-hr-report" output/report/README.md` 零命中 |
| 3. 仓库创建 | `gh repo view somAzzz/tcfd-report` 可见 |
| 4. 推送完成 | `gh api repos/somAzzz/tcfd-report/contents/index.html` 返回 200 |
| 5. Pages 启用 | `gh api repos/somAzzz/tcfd-report/pages` 返回 `html_url` 字段 (非 `url`) |
| 6. 站点可达 | `curl -I https://somAzzz.github.io/tcfd-report/` 返回 200 |

## 7. 影响范围

**只新增/修改**:

- 新增: `output/report/{index.html, README.md, .nojekyll}` (本地产物, 不入库)
- 新增: GitHub 公开仓库 `somAzzz/tcfd-report` (公网产物, 公开数据)
- 不动: 主仓任何源代码
- 不动: `output/evaluate_cooccurrence/` 下任何 JSONL (只读)

## 8. 已知遗留问题 (后续任务, 不阻塞本次部署)

- `2026-06-18-hr-visualization-design.md` (29KB, 旧的 HR 可视化设计) 中仍推荐 `tcfd-hr-report` 仓库名, 需在后续会话更新以与本次决策一致
- `scripts/build_report.py` 写出的 README 模板硬编码 `tcfd-hr-report`, 本次用 sed 临时修复; 长期方案是把 repo 名作为 CLI 参数传入

## 9. 后续 (后续会话, 不在本设计范围)

- 接入 GH Actions 实现 "push to main → 自动 build + 自动 deploy Pages"
- 集成本地 Qwen 模型生成 AI 摘要段落, 嵌入 HR 报告
- 多语言切换 (i18n 切换中/英报告)
- 域名自定义 (`tcfd-report.example.com`)
