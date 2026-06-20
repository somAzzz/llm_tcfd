"""Jinja2 HTML template for the public portfolio report."""
from __future__ import annotations

from jinja2 import Template

HTML_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Climate Risk Intelligence — A-share Disclosure Analysis</title>
  <link rel="icon" href="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%231f77b4'/><text x='16' y='22' font-size='18' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'>T</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
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
      --bg: #111416;
      --fg: #f2efe8;
      --card-bg: #171b1d;
      --card-border: #323a3b;
      --muted: #a6aaa4;
      --accent: #36d6b5;
      --accent-2: #7fb7ff;
      --accent-3: #e7b75f;
      --accent-fg: #07100f;
      --header-bg: #101315;
      --kpi-number-color: #36d6b5;
      --aside-bg: #171b1d;
      --aside-border: #323a3b;
      --code-bg: #0b0e10;
      --paper: #efe7d7;
      --paper-ink: #16191b;
      --rule: rgba(242, 239, 232, 0.18);
      --chart-frame: rgba(54, 214, 181, 0.1);
    }
    :root[data-theme="light"] {
      --bg: #f5f1e7;
      --fg: #151817;
      --card-bg: #fffaf0;
      --card-border: #d7cdbd;
      --muted: #5f675f;
      --accent: #087f6e;
      --accent-2: #245ea8;
      --accent-3: #9a6417;
      --accent-fg: #ffffff;
      --header-bg: #ede5d6;
      --kpi-number-color: #087f6e;
      --aside-bg: #fffaf0;
      --aside-border: #d7cdbd;
      --code-bg: #ebe2d2;
      --paper: #201f1a;
      --paper-ink: #fffaf0;
      --rule: rgba(21, 24, 23, 0.18);
      --chart-frame: rgba(8, 127, 110, 0.1);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; overflow-x: hidden; }
    body {
      font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--fg);
      margin: 0;
      padding: 0;
      line-height: 1.55;
      overflow-x: hidden;
    }
    body, section, .kpi-card, header, .hr-side-panel, .callout, .evidence-tape {
      transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
    }
    a { color: inherit; }
    .container { max-width: 1180px; margin: 0 auto; padding: 1.25rem 1.25rem 2.5rem; }
    header {
      background: var(--header-bg);
      color: var(--fg);
      padding: 4.5rem 1.5rem 1.25rem;
      text-align: left;
      position: relative;
      border-bottom: 1px solid var(--card-border);
      overflow: hidden;
    }
    header::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(90deg, rgba(54, 214, 181, 0.12) 1px, transparent 1px),
        linear-gradient(0deg, rgba(127, 183, 255, 0.08) 1px, transparent 1px);
      background-size: 74px 74px;
      mask-image: linear-gradient(90deg, transparent, #000 18%, #000 82%, transparent);
      opacity: 0.55;
      pointer-events: none;
    }
    .hero-inner {
      max-width: 1180px;
      margin: 0 auto;
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 2.25rem;
      align-items: end;
      min-width: 0;
    }
    .hero-kicker {
      color: var(--accent);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0;
      text-transform: uppercase;
      margin: 0 0 1rem;
    }
    header h1 {
      margin: 0 0 1rem 0;
      font-family: 'Fraunces', Georgia, serif;
      font-size: clamp(2.55rem, 6vw, 5.95rem);
      line-height: 0.9;
      font-weight: 700;
      max-width: 920px;
      letter-spacing: 0;
      overflow-wrap: anywhere;
    }
    header .subtitle {
      color: var(--muted);
      font-size: 1.06rem;
      max-width: 760px;
      margin: 0;
    }
    .hero-finding {
      margin-top: 1.35rem;
      padding: 1rem 1.1rem;
      border-left: 4px solid var(--accent);
      background: var(--chart-frame);
      border-radius: 8px;
      max-width: 860px;
      color: var(--fg);
    }
    .hero-proof {
      border: 1px solid var(--card-border);
      background: rgba(255, 255, 255, 0.025);
      border-radius: 8px;
      padding: 1rem;
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
      min-width: 0;
    }
    .proof-label {
      margin: 0 0 0.75rem;
      color: var(--accent-3);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      text-transform: uppercase;
    }
    .evidence-tape {
      display: grid;
      gap: 0.65rem;
    }
    .tape-row {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 0.75rem;
      align-items: center;
      padding: 0.72rem 0.8rem;
      background: var(--paper);
      color: var(--paper-ink);
      border-radius: 4px;
      transform: rotate(var(--tilt, -0.5deg));
    }
    .tape-row:nth-child(2) { --tilt: 0.7deg; }
    .tape-row:nth-child(3) { --tilt: -0.3deg; }
    .tape-rank, .tape-count {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .tape-pair {
      min-width: 0;
      font-weight: 700;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }
    .tape-translation {
      display: block;
      font-weight: 500;
      opacity: 0.72;
      font-size: 0.82rem;
      margin-top: 0.18rem;
    }
    .hr-theme-toggle {
      position: absolute;
      top: 1rem;
      right: 1rem;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--fg);
      width: 2.4rem;
      height: 2.4rem;
      border-radius: 999px;
      cursor: pointer;
      font-size: 1rem;
      z-index: 2;
    }
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin: 1.4rem 0 1rem;
    }
    .kpi-card {
      background: transparent;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      text-align: left;
    }
    .kpi-card .number {
      font-family: 'JetBrains Mono', monospace;
      font-size: clamp(1.35rem, 2.3vw, 2rem);
      font-weight: 700;
      color: var(--kpi-number-color);
      margin: 0;
      line-height: 1;
    }
    .kpi-card .label {
      font-size: 0.78rem;
      color: var(--muted);
      margin: 0.55rem 0 0;
      text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
    }
    .insight-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin: 0 0 1.5rem;
    }
    .insight-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.1rem;
    }
    .insight-card .label {
      color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      margin: 0 0 0.45rem;
    }
    .insight-card .value {
      color: var(--accent);
      font-family: 'Fraunces', Georgia, serif;
      font-size: 1.55rem;
      font-weight: 700;
      margin: 0 0 0.55rem;
    }
    .insight-card .detail {
      color: var(--fg);
      font-size: 0.92rem;
      margin: 0;
    }
    .evidence-list {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 0.75rem;
      margin: 1rem 0 1.25rem;
    }
    .evidence-item {
      border: 1px solid var(--card-border);
      background: rgba(255, 255, 255, 0.02);
      border-radius: 6px;
      padding: 0.85rem;
      min-height: 108px;
    }
    .evidence-item .rank {
      color: var(--muted);
      font-size: 0.75rem;
      margin-bottom: 0.35rem;
    }
    .evidence-item .pair {
      font-weight: 700;
      color: var(--fg);
      line-height: 1.35;
    }
    .evidence-item .translated {
      color: var(--muted);
      font-size: 0.78rem;
      margin-top: 0.3rem;
    }
    .evidence-item .count {
      color: var(--accent);
      font-weight: 700;
      margin-top: 0.45rem;
      font-size: 0.9rem;
    }
    section {
      background: transparent;
      border-top: 1px solid var(--rule);
      padding: 2.25rem 0;
      margin: 0;
    }
    section h2 {
      margin: 0 0 1rem 0;
      font-family: 'Fraunces', Georgia, serif;
      font-size: clamp(1.8rem, 3.5vw, 3.2rem);
      line-height: 0.98;
      color: var(--fg);
      font-weight: 700;
    }
    section h3 {
      font-family: 'Fraunces', Georgia, serif;
      font-size: 1.55rem;
      color: var(--fg);
    }
    .section-head {
      display: grid;
      grid-template-columns: minmax(220px, 0.75fr) minmax(0, 1fr);
      gap: 2rem;
      align-items: start;
      margin-bottom: 1.35rem;
    }
    .section-tag {
      margin: 0 0 0.75rem;
      color: var(--accent-3);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .lede {
      color: var(--muted);
      font-size: 1.05rem;
      margin: 0;
    }
    .chart-frame {
      border: 1px solid var(--card-border);
      border-radius: 8px;
      background: var(--card-bg);
      padding: 0.75rem;
      min-width: 0;
      overflow: hidden;
    }
    .callout {
      background: var(--code-bg);
      border-left: 4px solid var(--accent);
      padding: 1rem 1.25rem;
      margin: 1.5rem 0;
      border-radius: 4px;
    }
    .flow-copy {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-top: 1rem;
    }
    .pipeline-board {
      border: 1px solid var(--card-border);
      border-radius: 8px;
      background:
        linear-gradient(90deg, rgba(54, 214, 181, 0.14), transparent 34%),
        var(--card-bg);
      padding: 1rem;
      overflow: hidden;
    }
    .pipeline-track {
      display: grid;
      grid-template-columns: repeat(6, minmax(130px, 1fr));
      gap: 0.65rem;
      align-items: stretch;
    }
    .pipeline-stage {
      position: relative;
      min-height: 150px;
      border: 1px solid var(--rule);
      border-radius: 8px;
      padding: 0.95rem;
      background: rgba(255, 255, 255, 0.025);
    }
    .pipeline-stage::after {
      content: "";
      position: absolute;
      right: -0.68rem;
      top: 50%;
      width: 0.7rem;
      height: 1px;
      background: var(--accent);
      opacity: 0.75;
    }
    .pipeline-stage:last-child::after { display: none; }
    .pipeline-step {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.7rem;
      height: 1.7rem;
      border-radius: 999px;
      background: var(--accent);
      color: var(--accent-fg);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      font-weight: 700;
      margin-bottom: 0.8rem;
    }
    .pipeline-stage h3 {
      margin: 0 0 0.45rem;
      font-family: 'IBM Plex Sans', sans-serif;
      font-size: 1rem;
      color: var(--fg);
    }
    .pipeline-stage p {
      margin: 0;
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.45;
    }
    .method-note {
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.02);
    }
    .method-note h3 {
      margin: 0 0 0.5rem;
      font-size: 1.1rem;
      color: var(--accent);
      font-family: 'IBM Plex Sans', sans-serif;
    }
    .method-note p { margin: 0; color: var(--muted); }
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
      .insight-grid { grid-template-columns: 1fr; }
      .evidence-list { grid-template-columns: 1fr; }
      header h1 { font-size: 2rem; }
    }
    @media (min-width: 701px) and (max-width: 1000px) {
      .insight-grid { grid-template-columns: 1fr; }
      .evidence-list { grid-template-columns: repeat(2, 1fr); }
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
      border-left: 3px solid var(--accent);
      border-radius: 4px;
      padding: 0.85rem 1rem;
    }
    .spec-card h3 {
      margin: 0 0 0.4rem 0;
      font-size: 1.05rem;
      color: var(--accent);
    }
    .spec-card p {
      margin: 0;
      font-size: 0.9rem;
      line-height: 1.5;
      color: var(--muted);
    }
    .hr-side-panel { max-width: 100vw; }
    .hr-side-panel button:focus-visible, .hr-theme-toggle:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 3px;
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
      }
    }
    @media (max-width: 900px) {
      .engineering-layout-grid { grid-template-columns: 1fr; }
      .hero-inner { grid-template-columns: 1fr; }
      .section-head { grid-template-columns: 1fr; gap: 0.75rem; }
      .flow-copy { grid-template-columns: 1fr; }
      .pipeline-track {
        grid-template-columns: 1fr;
      }
      .pipeline-stage::after {
        right: auto;
        left: 1.8rem;
        top: auto;
        bottom: -0.68rem;
        width: 1px;
        height: 0.7rem;
      }
      header { padding-top: 4rem; }
    }
    @media (max-width: 520px) {
      .container { padding-inline: 0.9rem; }
      .kpi-row { grid-template-columns: 1fr; }
      header h1 { font-size: 2.45rem; }
      .tape-row { grid-template-columns: 1fr; gap: 0.28rem; }
      aside.hr-side-panel { width: 100vw !important; }
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
    <div class="hero-inner">
      <div>
        <p class="hero-kicker">Portfolio case file / NLP / Climate finance / Local LLM</p>
        <h1>Climate risk signals hidden in 10,814 annual reports</h1>
        <p class="subtitle">
          A reproducible NLP pipeline that turns Chinese A-share annual reports into
          evidence-backed TCFD disclosure intelligence across policy, market, and
          technology dimensions.
        </p>
        <div class="hero-finding">
          Finding: climate disclosure accelerates sharply after 2020. Policy and
          compliance language remains the dominant signal, while transition technology
          terms become increasingly visible in recent filings.
        </div>
      </div>
      <div class="hero-proof" aria-label="Top evidence highlights">
        <p class="proof-label">Evidence extracted from annual-report language</p>
        <div class="evidence-tape">
          {% for item in top_pairs[:3] %}
          <div class="tape-row">
            <span class="tape-rank">#{{ loop.index }}</span>
            <span class="tape-pair">
              {{ item.pair }}
              <span class="tape-translation">{{ item.translated }}</span>
            </span>
            <span class="tape-count">{{ item.count }}</span>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>
  </header>

  <div class="container">
    <div class="kpi-row">
      <div class="kpi-card">
        <p class="number">{{ report_stats.get("companies", "0") }}</p>
        <p class="label">Companies Analyzed</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ report_stats.get("records", "0") }}</p>
        <p class="label">LLM Evaluations</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ report_stats.get("disclosures", "0") }}</p>
        <p class="label">TCFD Disclosures</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ report_stats.get("test_count", "0") }} tests passing</p>
        <p class="label">Engineering Quality</p>
      </div>
    </div>

    <section>
      <div class="section-head">
        <div>
          <p class="section-tag">01 / Result</p>
          <h2>From filings to climate-risk evidence</h2>
        </div>
        <p class="lede">
          The project turns annual-report text into a structured map of climate-risk
          language. It combines local LLM extraction, co-occurrence analysis, TCFD
          relevance evaluation, semantic clustering, and a public-safe interactive report.
        </p>
      </div>
      <div class="insight-grid">
        {% for insight in insights %}
        <article class="insight-card">
          <p class="label">{{ insight.label }}</p>
          <p class="value">{{ insight.value }}</p>
          <p class="detail">{{ insight.detail }}</p>
        </article>
        {% endfor %}
      </div>
      <p class="lede">
        The sunburst below shows the vocabulary hierarchy: TCFD dimension →
        semantic cluster → individual keyword. It is a compact view of the
        topic space discovered by the pipeline.
      </p>
      <div class="chart-frame">
        <div id="echarts-sunburst" class="echarts-chart" style="width:100%; height:520px;"></div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <p class="section-tag">02 / System</p>
          <h2>A pipeline built for noisy disclosure text</h2>
        </div>
        <p class="lede">
          Raw annual-report text moves through sampling, chunking, local LLM keyword
          extraction, co-occurrence analysis, TCFD scoring, and topic clustering.
          The public report is the final artifact, not a hand-made dashboard.
        </p>
      </div>
      <div class="pipeline-board" aria-label="NLP pipeline stages">
        <div class="pipeline-track">
          <article class="pipeline-stage">
            <span class="pipeline-step">01</span>
            <h3>Sample reports</h3>
            <p>Load annual-report files and keep year-level provenance.</p>
          </article>
          <article class="pipeline-stage">
            <span class="pipeline-step">02</span>
            <h3>Split text</h3>
            <p>Convert long filings into bounded analysis chunks.</p>
          </article>
          <article class="pipeline-stage">
            <span class="pipeline-step">03</span>
            <h3>Extract terms</h3>
            <p>Use a local LLM to identify climate-related terms.</p>
          </article>
          <article class="pipeline-stage">
            <span class="pipeline-step">04</span>
            <h3>Build pairs</h3>
            <p>Count co-occurring terms that describe the same disclosure signal.</p>
          </article>
          <article class="pipeline-stage">
            <span class="pipeline-step">05</span>
            <h3>Score TCFD fit</h3>
            <p>Route evidence into policy, market, and technology dimensions.</p>
          </article>
          <article class="pipeline-stage">
            <span class="pipeline-step">06</span>
            <h3>Cluster topics</h3>
            <p>Aggregate similar language into readable chart structures.</p>
          </article>
        </div>
      </div>
      <div class="flow-copy">
        <article class="method-note">
          <h3>Reusable pattern</h3>
          <p>Multi-dimensional routing, structured LLM outputs, concurrent batch processing,
             retry handling, and downstream analytics can transfer to other document-heavy domains.</p>
        </article>
        <article class="method-note">
          <h3>Public-safe output</h3>
          <p>Company names are anonymized, chart data is embedded into a single HTML file,
             and a leakage scanner runs before publication.</p>
        </article>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <p class="section-tag">03 / Findings</p>
          <h2>The signal is temporal, then linguistic</h2>
        </div>
        <p class="lede">
          The strongest story is time: climate-related disclosures were sparse in
          the early 2000s and surged in the 2020s. The streamgraph lets you compare
          how policy, market, and technology language evolved.
        </p>
      </div>
      <div class="chart-frame">
        <div id="echarts-streamgraph" class="echarts-chart" style="width:100%; height:520px;"></div>
      </div>

      <h3 style="margin-top: 2rem;">Recent language graph</h3>
      <p class="lede">
        The most frequent co-occurrences reveal the vocabulary behind the trend:
        compliance pressure, energy reduction, and transition technology dominate
        the recent disclosure graph.
      </p>
      <div class="evidence-list">
        {% for item in top_pairs %}
        <article class="evidence-item">
          <div class="rank">#{{ loop.index }}</div>
          <div class="pair">{{ item.pair }}</div>
          <div class="translated">{{ item.translated }}</div>
          <div class="count">{{ item.count }} mentions</div>
        </article>
        {% endfor %}
      </div>
      <p>Drag nodes, hover for counts, and click a node to inspect source context samples.</p>
      <div class="chart-frame">
        <div id="echarts-network" class="echarts-chart" style="width:100%; height:600px;"></div>
      </div>

      <h3 style="margin-top: 2rem;">Pipeline refinement</h3>
      <p>{{ report_stats.get("companies", "0") }} reports → chunks → disclosures → dimensions. Click a link to view source contexts.</p>
      <div class="chart-frame">
        <div id="echarts-sankey" class="echarts-chart" style="width:100%; height:480px;"></div>
      </div>
    </section>

    <section class="engineering-excellence">
      <div class="section-head">
        <div>
          <p class="section-tag">04 / Engineering</p>
          <h2>Turning stochastic LLM output into a repeatable artifact</h2>
        </div>
        <p class="lede">The project is designed as an engineering system, not a one-off notebook.</p>
      </div>

      <div class="engineering-layout-grid">
        <div class="chart-frame">
          <div id="echarts-pipeline-health-dashboard"
               class="echarts-chart"
               style="width:100%; height:380px;"></div>
        </div>

        <div class="engineering-specs">
          <div class="spec-card">
            <h3>Structured validation</h3>
            <p>A local 35B model can return malformed JSON or partial schema
               matches. The evaluator wraps every response in Pydantic validation,
               explicit parse exceptions, raw-response logging, and retry-aware
               batch execution.</p>
          </div>
          <div class="spec-card">
            <h3>Streaming and concurrency</h3>
            <p>Large JSONL outputs are loaded and aggregated with streaming
               readers. Concurrent evaluation is handled with
               <code>ThreadPoolExecutor</code>, bounded workers, and resumable
               per-year output files.</p>
          </div>
          <div class="spec-card">
            <h3>Publication checks</h3>
            <p>The current suite has <strong>{{ report_stats.get("test_count", "0") }} automated tests</strong>.
               The public report is rebuilt from source data and checked with a
               leakage scanner before publication.</p>
          </div>
        </div>
      </div>

      <div x-show="$store.pipelineUi.showDeepDive" x-transition.opacity.duration.300ms
           style="margin-top: 1rem;">
        <h3 style="margin-top: 1rem; color: var(--accent);">
          Module dependency graph
        </h3>
        <p>Hover a module to highlight its import dependencies.</p>
        <div class="chart-frame">
          <div id="echarts-module-graph" class="echarts-chart"
               style="width:100%; height:480px;"></div>
        </div>
      </div>
    </section>

    <footer>
      <p>Built {{ build_date }} · Source available on request · All data anonymized</p>
    </footer>
  </div>

  <!-- Side panel: backdrop + aside -->
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

  <script>
    window.__hrCharts = {};
    window.__hrOpts = {
      sunburst:    {{ sunburst_json|safe }},
      streamgraph: {{ streamgraph_json|safe }},
      network:     {{ network_json|safe }},
      sankey:      {{ sankey_json|safe }},
      moduleGraph: {{ module_graph_json|safe }},
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
          const source = params.data.source;
          const target = params.data.target;
          const edgeKey = `${source}->${target}`;
          const contexts = _contextsFor(edgeKey, 'sankey');
          window.Alpine.store('hrApp').openPanel({
            type: 'link',
            title: `${window.__hrTranslate(source)} → ${window.__hrTranslate(target)}`,
            contexts: contexts,
          });
        }
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
      buildChart('echarts-module-graph',         window.__hrOpts.moduleGraph);
      buildChart('echarts-pipeline-health-dashboard', window.__hrOpts.pipelineHealthDashboard);
      bindPipelineHealthClickHandler();
    }

    function bindPipelineHealthClickHandler() {
      const el = document.getElementById('echarts-pipeline-health-dashboard');
      if (!el || !window.__hrCharts['echarts-pipeline-health-dashboard']) return;
      const chart = window.__hrCharts['echarts-pipeline-health-dashboard'];
      chart.off('click');
      chart.on('click', function () { window.__hrToggleDeepDive(); });
    }

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
