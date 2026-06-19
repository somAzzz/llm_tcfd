"""Jinja2 HTML template for the HR report (Stage 2: dark + Inter + Alpine)."""
from __future__ import annotations

from jinja2 import Template

HTML_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TCFD Project Demo — Climate Disclosure Analysis</title>
  <link rel="icon" href="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%231f77b4'/><text x='16' y='22' font-size='18' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'>T</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
    // Stage 2: 翻译 map + context 索引 (由 html_assembler.py 渲染)
    window.__hrTranslateMap = {{ translate_map_json|safe }};
    window.__hrContextIndex = {{ context_index_json|safe }};
    window.__hrTranslate = function(kw) {
      if (!kw) return '';
      const map = window.__hrTranslateMap || {};
      if (map[kw]) return map[kw];
      if (/^[\x00-\x7F]+$/.test(kw)) return kw;
      const stripped = kw.replace(/[^\w\s]+/g, '').trim();
      if (!stripped) return kw;
      return '[[ZH: ' + stripped + ']]';
    };
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
  <style>
    :root[data-theme="dark"] {
      --bg: #0f1419;
      --fg: #e6e6e6;
      --card-bg: #1a1f24;
      --card-border: #2a2f34;
      --muted: #8b95a1;
      --accent: #58a6ff;
      --accent-fg: #ffffff;
      --header-bg: linear-gradient(135deg, #1f3a5f 0%, #1a4d2e 100%);
      --kpi-number-color: #58a6ff;
      --aside-bg: #1a1f24;
      --aside-border: #2a2f34;
      --code-bg: #0d1117;
    }
    :root[data-theme="light"] {
      --bg: #fafafa;
      --fg: #222;
      --card-bg: #ffffff;
      --card-border: #e0e0e0;
      --muted: #666;
      --accent: #1f77b4;
      --accent-fg: #ffffff;
      --header-bg: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%);
      --kpi-number-color: #1f77b4;
      --aside-bg: #ffffff;
      --aside-border: #e0e0e0;
      --code-bg: #f5f5f5;
    }
    * { box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--fg);
      margin: 0;
      padding: 0;
      line-height: 1.5;
    }
    body, section, .kpi-card, header, .hr-side-panel, .callout {
      transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
    header {
      background: var(--header-bg);
      color: white;
      padding: 2rem 1.5rem;
      text-align: center;
      position: relative;
    }
    header h1 { margin: 0 0 0.5rem 0; font-size: 1.8rem; font-weight: 700; }
    header .subtitle { opacity: 0.9; font-size: 1.05rem; }
    .hr-theme-toggle {
      position: absolute;
      top: 1rem;
      right: 1rem;
      background: rgba(255,255,255,0.15);
      border: 1px solid rgba(255,255,255,0.3);
      color: white;
      padding: 0.4rem 0.7rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
    }
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin: 2rem 0;
    }
    .kpi-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.25rem;
      text-align: center;
    }
    .kpi-card .number {
      font-size: 2.25rem;
      font-weight: 700;
      color: var(--kpi-number-color);
      margin: 0;
      font-family: 'Inter', sans-serif;
    }
    .kpi-card .label {
      font-size: 0.85rem;
      color: var(--muted);
      margin-top: 0.5rem;
    }
    section {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.5rem;
      margin: 1.5rem 0;
    }
    section h2 {
      margin: 0 0 1rem 0;
      font-size: 1.4rem;
      color: var(--accent);
      font-weight: 600;
    }
    .callout {
      background: var(--code-bg);
      border-left: 4px solid var(--accent);
      padding: 1rem 1.25rem;
      margin: 1.5rem 0;
      border-radius: 4px;
    }
    .callout h3 {
      margin: 0 0 0.5rem 0;
      color: var(--accent);
      font-size: 1.1rem;
    }
    details.tech-deep-dive {
      margin: 1.5rem 0;
    }
    details.tech-deep-dive summary {
      cursor: pointer;
      padding: 0.75rem 1rem;
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      border-radius: 4px;
      font-weight: 500;
    }
    details.tech-deep-dive[open] summary { border-radius: 4px 4px 0 0; }
    details.tech-deep-dive > div {
      border: 1px solid var(--card-border);
      border-top: none;
      padding: 1rem;
      border-radius: 0 0 4px 4px;
    }
    footer {
      text-align: center;
      padding: 2rem 1rem;
      color: var(--muted);
      font-size: 0.85rem;
    }
    @media (max-width: 700px) {
      .kpi-row { grid-template-columns: repeat(2, 1fr); }
    }
    /* Side panel slide transitions (Alpine x-transition) */
    .hr-slide-in {
      animation: hr-slide-from-right 0.25s ease-out;
    }
    .hr-slide-out {
      animation: hr-slide-to-right 0.25s ease-in;
    }
    @keyframes hr-slide-from-right {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
    @keyframes hr-slide-to-right {
      from { transform: translateX(0); }
      to { transform: translateX(100%); }
    }
    .engineering-layout-grid {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 1.5rem;
      align-items: start;
      margin-top: 1rem;
    }
    .engineering-specs {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .spec-card {
      background: rgba(255, 255, 255, 0.02);
      border-left: 3px solid var(--accent, #56d364);
      border-radius: 4px;
      padding: 0.85rem 1rem;
    }
    .spec-card h3 {
      margin: 0 0 0.4rem 0;
      font-size: 1.05rem;
      color: var(--accent, #56d364);
    }
    .spec-card p {
      margin: 0;
      font-size: 0.9rem;
      line-height: 1.5;
      color: var(--text-muted, #8b949e);
    }
    @media (max-width: 900px) {
      .engineering-layout-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body x-data x-init="
  document.documentElement.dataset.theme = localStorage.getItem('hr-theme') || 'dark';
  Alpine.store('hrApp', {
    theme: localStorage.getItem('hr-theme') || 'dark',
    panel: null,
    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('hr-theme', this.theme);
      document.documentElement.dataset.theme = this.theme;
      if (typeof rebuildAllCharts === 'function') rebuildAllCharts();
    },
    openPanel(data) { this.panel = data; },
    closePanel() { this.panel = null; },
  });
  Alpine.store('pipelineUi', { showDeepDive: false });
">
  <button @click="$store.hrApp.toggleTheme()"
          class="hr-theme-toggle"
          :aria-label="`Switch to ${$store.hrApp.theme === 'dark' ? 'light' : 'dark'} mode`">
    <span x-show="$store.hrApp.theme === 'dark'">☀️</span>
    <span x-show="$store.hrApp.theme === 'light'">🌙</span>
  </button>

  <header>
    <h1>TCFD Project Demo</h1>
    <p class="subtitle">A production NLP system for climate-related financial disclosure analysis</p>
  </header>

  <div class="container">
    <div class="kpi-row">
      <div class="kpi-card">
        <p class="number">10,814</p>
        <p class="label">Companies Analyzed</p>
      </div>
      <div class="kpi-card">
        <p class="number">52,000+</p>
        <p class="label">TCFD Disclosures Detected</p>
      </div>
      <div class="kpi-card">
        <p class="number">2000–2024</p>
        <p class="label">Years Covered</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ refactor_stats.get("test_after", 0) }} tests passing</p>
        <p class="label">Engineering Quality</p>
      </div>
    </div>

    <section>
      <h2>1. What is this project about?</h2>
      <p>
        This system reads <strong>annual reports from A-share listed companies</strong> and
        identifies <strong>TCFD (climate-related financial disclosure)</strong> content
        across three dimensions: <em>Policy</em>, <em>Market</em>, <em>Technology</em>.
      </p>
      <p>Three-dimensional clustering hierarchy (Sunburst) — click a node to drill down to keywords.</p>
      <div id="echarts-sunburst" class="echarts-chart" style="width:100%; height:520px;"></div>
    </section>

    <section>
      <h2>2. What we built</h2>
      <p>
        An end-to-end <strong>NLP pipeline</strong> that takes raw annual-report text
        through sampling, chunking, LLM-based keyword extraction, co-occurrence analysis,
        TCFD evaluation, and clustering.
      </p>
      <div class="mermaid">
flowchart LR
    A[1. Sample Reports] --> B[2. Split into Chunks]
    B --> C[3. Extract Keywords with LLM]
    C --> D[4. Find Co-occurring Pairs]
    D --> E[5. Score on Policy/Market/Technology]
    E --> F[6. Cluster Similar Topics]
      </div>
      <div class="callout">
        <h3>Beyond TCFD: Reusable Architecture</h3>
        <p>
          The patterns demonstrated here — multi-dimensional routing, structured LLM outputs,
          concurrent batch processing with retry — are domain-agnostic. The same architecture
          applies to:
        </p>
        <ul>
          <li><strong>Multilingual content classification</strong> at scale</li>
          <li><strong>Concurrent pipeline</strong> of LLM evaluations with rate limiting</li>
          <li><strong>Structured outputs from open-source models</strong> for downstream analytics</li>
        </ul>
        <p><em>Same engineering. New domain.</em></p>
      </div>
    </section>

    <section>
      <h2>3. What we discovered</h2>
      <p>
        Below: 25 years (2000-2024) of three-dimensional disclosure evolution (Streamgraph) —
        drag the bottom slider to zoom into a time range.
      </p>
      <div id="echarts-streamgraph" class="echarts-chart" style="width:100%; height:520px;"></div>

      <h3 style="margin-top: 2rem;">Keyword Co-occurrence Network (Recent 3 Years)</h3>
      <p>Draggable nodes, hover to see co-occurrence count, click a node to view original context.</p>
      <div id="echarts-network" class="echarts-chart" style="width:100%; height:600px;"></div>

      <h3 style="margin-top: 2rem;">NLP Pipeline Data Refinement (Sankey)</h3>
      <p>10,814 reports → chunking → disclosure → by dimension. Click a link to view context.</p>
      <div id="echarts-sankey" class="echarts-chart" style="width:100%; height:480px;"></div>
    </section>

    <section class="engineering-excellence">
      <h2>4. Robust AI Pipeline Engineering</h2>
      <p class="subtitle">How we transformed a volatile LLM script into a
         fault-tolerant, industry-grade text processing mill.</p>

      <div class="engineering-layout-grid">
        <div id="echarts-pipeline-health-dashboard"
             class="echarts-chart"
             style="width:100%; height:380px; cursor: pointer;"
             @click="window.__hrToggleDeepDive && window.__hrToggleDeepDive()"></div>

        <div class="engineering-specs">
          <div class="spec-card">
            <h3>&#x1F6E1;&#xFE0F; Stochastic-to-Deterministic Defense</h3>
            <p>Deploying a local 35B model presents non-deterministic JSON
               deformations. We implemented a Pydantic-driven validation
               guardrail featuring a strict exception hierarchy
               (<code>LLMResponseParseError</code>) and automatic
               token-rate-limiting. Raw responses are safely isolated and logged
               without halting the entire multi-year batch run.</p>
          </div>
          <div class="spec-card">
            <h3>&#x26A1;&#xFE0F; Memory-Safe Streaming &amp; Concurrency</h3>
            <p>Processing 10,814 files sequentially triggers tight coupling and
               out-of-memory stalls. The refactored pipeline decouples
               orchestration into 8 single-responsibility submodules, shifting
               to a generator-based stream architecture. Controlled by a
               <code>ThreadPoolExecutor</code> semaphore, the pipeline achieved
               zero-leak concurrency across 25 years of financial reports.</p>
          </div>
          <div class="spec-card">
            <h3>&#x1F52C; Comprehensive Observability</h3>
            <p>To eliminate regressions caused by LLM prompt tuning, we expanded
               the test suite from 16 baseline specs to
               <strong>329+ automated tests</strong>. New evaluation submodules
               maintain a 95%&ndash;100% coverage rate, wrapping the entire AI
               infrastructure in a transparent, highly verifiable test harness.</p>
          </div>
        </div>
      </div>

      <div x-show="$store.pipelineUi.showDeepDive" x-transition.opacity.duration.300ms
           style="margin-top: 1rem;">
        <h3 style="margin-top: 1rem; color: var(--accent);">
          &#x1F9E9; Module Dependency Graph (click any bar to collapse)
        </h3>
        <p>Hover a module to highlight its import dependencies.</p>
        <div id="echarts-module-graph" class="echarts-chart"
             style="width:100%; height:480px;"></div>
      </div>
    </section>

    <footer>
      <p>Built {{ build_date }} · Source available on request · All data anonymized</p>
    </footer>
  </div>

  <!-- Side panel: backdrop + aside (Alpine 侧栏) -->
  <div x-show="$store.hrApp.panel"
       x-transition.opacity.duration.200ms
       @click="$store.hrApp.closePanel()"
       class="hr-side-panel-backdrop"
       style="position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 999;"></div>

  <aside x-show="$store.hrApp.panel"
         x-transition:enter="hr-slide-in"
         x-transition:leave="hr-slide-out"
         @keydown.escape.window="$store.hrApp.closePanel()"
         class="hr-side-panel"
         style="position: fixed; right: 0; top: 0; width: 420px; height: 100vh;
                background: var(--aside-bg); border-left: 1px solid var(--aside-border);
                box-shadow: -4px 0 12px rgba(0,0,0,0.3); z-index: 1000;
                transform: translateX(100%); transition: transform 0.25s ease;
                overflow-y: auto; padding: 1.5rem;">
    <header style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;
                   padding-bottom: 0.75rem; border-bottom: 1px solid var(--card-border);">
      <h3 x-text="$store.hrApp.panel ? $store.hrApp.panel.title : ''"
          style="margin: 0; flex: 1; font-size: 1.15rem; color: var(--fg);"></h3>
      <span class="dim-badge"
            x-show="$store.hrApp.panel && $store.hrApp.panel.dimension"
            x-text="$store.hrApp.panel ? $store.hrApp.panel.dimension : ''"
            style="background: var(--accent); color: var(--accent-fg); padding: 0.2rem 0.6rem;
                   border-radius: 4px; font-size: 0.8rem;"></span>
      <button @click="$store.hrApp.closePanel()"
              style="background: none; border: none; color: var(--muted); cursor: pointer;
                     font-size: 1.25rem; padding: 0.25rem 0.5rem;">✕</button>
    </header>
    <div class="hr-side-panel__body">
      <template x-if="$store.hrApp.panel && $store.hrApp.panel.contexts.length === 0">
        <p style="color: var(--muted); font-style: italic;">No context samples available for this item.</p>
      </template>
      <template x-for="ctx in $store.hrApp.panel ? $store.hrApp.panel.contexts : []" :key="ctx.id">
        <article class="context-card" style="background: var(--card-bg);
                                              border: 1px solid var(--card-border);
                                              border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
          <p class="context-zh" x-text="ctx.original"
             style="color: var(--fg); margin: 0 0 0.5rem 0; font-size: 0.95rem;"></p>
          <p class="context-en" x-text="ctx.translated"
             style="color: var(--muted); margin: 0 0 0.75rem 0; font-size: 0.9rem; font-style: italic;"></p>
          <footer style="display: flex; justify-content: space-between;
                         color: var(--muted); font-size: 0.8rem;">
            <span x-text="ctx.source"></span>
            <span x-text="ctx.year"></span>
          </footer>
        </article>
      </template>
    </div>
  </aside>

  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });

    // Stage 2: ECharts 4 图表统一管理 (dispose + reinit 主题切换)
    window.__hrCharts = {};
    window.__hrOpts = {
      sunburst:    {{ sunburst_json|safe }},
      streamgraph: {{ streamgraph_json|safe }},
      network:     {{ network_json|safe }},
      sankey:      {{ sankey_json|safe }},
      pipelineHealthDashboard: {{ pipeline_health_dashboard_json|safe }},
    };

    function applyTheme(opt, theme) {
      const isDark = theme === 'dark';
      const fg = isDark ? '#e6e6e6' : '#222';
      const muted = isDark ? '#8b95a1' : '#666';
      opt = JSON.parse(JSON.stringify(opt));
      opt.textStyle = Object.assign({}, opt.textStyle, { color: fg });
      if (opt.title) opt.title.textStyle = Object.assign({}, opt.title.textStyle, { color: fg });
      ['xAxis', 'yAxis'].forEach(k => {
        if (opt[k]) {
          opt[k] = Object.assign({}, opt[k], {
            axisLine: { lineStyle: { color: muted } },
            axisLabel: { color: muted },
            splitLine: { lineStyle: { color: muted, opacity: 0.2 } },
          });
        }
      });
      if (opt.legend) opt.legend.textStyle = Object.assign({}, opt.legend.textStyle, { color: fg });
      return opt;
    }

    function bindClickHandlers(chart, chartId) {
      const _contextsFor = function(key, source) {
        const idx = (window.__hrContextIndex && window.__hrContextIndex[source]) || {};
        return (idx[key] || []).slice(0, 3);
      };
      chart.on('click', function(params) {
        if (chartId === 'echarts-network' && params.dataType === 'node') {
          const kw = params.data.name;
          const contexts = _contextsFor(kw, 'keywords');
          window.Alpine.store('hrApp').openPanel({
            type: 'node',
            title: window.__hrTranslate(kw),
            dimension: window.__hrTranslate(params.data.category || ''),
            contexts: contexts,
          });
        } else if (chartId === 'echarts-sankey' && params.dataType === 'edge') {
          // Stage 3.2 修复: 节点名是 clean English ("Reports 2023" 等),
          // 不再用 stage{N}_ prefix (旧 prefix 触发了 formatter → ECharts 把
          // JS 源码当 template 渲染)。所以这里也不再需要 stripPrefix。
          const source = params.data.source;
          const target = params.data.target;
          // 关键: 与 build_context_index 保持一致 — 排序后的 a->b 字符串
          const pair = [source, target].sort();
          const edgeKey = `${pair[0]}->${pair[1]}`;
          const contexts = _contextsFor(edgeKey, 'sankey');
          window.Alpine.store('hrApp').openPanel({
            type: 'link',
            title: `${window.__hrTranslate(source)} → ${window.__hrTranslate(target)}`,
            contexts: contexts,
          });
        }
        // 其它点击 (axisLabel / legend / 空白) → 不响应, panel 保持
      });
    }

    function buildChart(chartId, opt) {
      const el = document.getElementById(chartId);
      if (!el) return;
      if (window.__hrCharts[chartId]) {
        window.__hrCharts[chartId].dispose();
      }
      opt = applyTheme(opt, document.documentElement.dataset.theme);
      const chart = echarts.init(el);
      chart.setOption(opt);
      window.__hrCharts[chartId] = chart;
      bindClickHandlers(chart, chartId);
      return chart;
    }

    function rebuildAllCharts() {
      buildChart('echarts-sunburst',             window.__hrOpts.sunburst);
      buildChart('echarts-streamgraph',          window.__hrOpts.streamgraph);
      buildChart('echarts-network',              window.__hrOpts.network);
      buildChart('echarts-sankey',               window.__hrOpts.sankey);
      buildChart('echarts-pipeline-health-dashboard', window.__hrOpts.pipelineHealthDashboard);
      bindPipelineHealthClickHandler();
    }

    function bindPipelineHealthClickHandler() {
      const el = document.getElementById('echarts-pipeline-health-dashboard');
      if (!el || !window.__hrCharts['echarts-pipeline-health-dashboard']) return;
      const chart = window.__hrCharts['echarts-pipeline-health-dashboard'];
      chart.on('click', function () { window.__hrToggleDeepDive(); });
    }

    // Toggle the hidden Module Dependency Graph on any bar click.
    window.__hrToggleDeepDive = function () {
      if (!window.Alpine) return;
      const s = Alpine.store('pipelineUi');
      s.showDeepDive = !s.showDeepDive;
      if (s.showDeepDive) {
        Alpine.nextTick(function () {
          const el = document.getElementById('echarts-module-graph');
          if (el && window.echarts) {
            const inst = echarts.getInstanceByDom(el);
            if (inst) inst.resize();   // prevent 0x0 hidden canvas
          }
        });
      }
    };

    document.addEventListener('DOMContentLoaded', function() {
      if (typeof echarts === 'undefined') {
        document.querySelectorAll('.echarts-chart').forEach(el => {
          el.innerHTML = '<div style="background:#f0f0f0;color:#666;text-align:center;line-height:400px;">Load failed</div>';
        });
        return;
      }
      rebuildAllCharts();
    });
  </script>

</body>
</html>
""")