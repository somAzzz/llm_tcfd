"""Jinja2 HTML template for the HR report."""
from __future__ import annotations

from jinja2 import Template

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TCFD Project Demo — Climate Disclosure Analysis</title>
  <style>
    :root {
      --bg: #fafafa;
      --fg: #222;
      --accent: #1f77b4;
      --card-bg: #fff;
      --card-border: #e0e0e0;
      --muted: #666;
    }
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--fg);
      margin: 0;
      padding: 0;
      line-height: 1.5;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
    header {
      background: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%);
      color: white;
      padding: 2rem 1.5rem;
      text-align: center;
    }
    header h1 { margin: 0 0 0.5rem 0; font-size: 1.8rem; }
    header .subtitle { opacity: 0.9; font-size: 1.05rem; }
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
      font-size: 2rem;
      font-weight: 700;
      color: var(--accent);
      margin: 0;
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
    }
    .callout {
      background: #f0f7ff;
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
    .filter-row {
      margin: 1rem 0;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .filter-row label { font-size: 0.9rem; color: var(--muted); }
    .filter-row select {
      padding: 0.4rem 0.6rem;
      font-size: 0.95rem;
      border: 1px solid var(--card-border);
      border-radius: 4px;
      background: white;
    }
    .mermaid { text-align: center; margin: 1rem 0; }
    details.tech-deep-dive {
      margin: 1.5rem 0;
    }
    details.tech-deep-dive summary {
      cursor: pointer;
      padding: 0.75rem 1rem;
      background: #f5f5f5;
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
  </style>
</head>
<body>
  <header>
    <h1>TCFD Project Demo</h1>
    <p class="subtitle">A production NLP system for climate-related financial disclosure analysis</p>
  </header>

  <div class="container">
    <div class="kpi-row">
      <div class="kpi-card">
        <p class="number">{{ kpis.total_companies }}</p>
        <p class="label">Companies Analyzed</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ kpis.tcfd_count }}</p>
        <p class="label">TCFD Disclosures Detected</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ kpis.years_range }}</p>
        <p class="label">Years Covered</p>
      </div>
      <div class="kpi-card">
        <p class="number">{{ kpis.test_summary }}</p>
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
      <p>Below: distribution of detected disclosures by TCFD dimension.</p>
      <div id="donut-chart"></div>
      <script type="application/json" id="donut-data">{{ donut_json }}</script>
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
        Below: yearly trend (filter to inspect specific periods).
      </p>
      <div class="filter-row">
        <label for="year-filter">Year range:</label>
        <select id="year-filter">
          <option value="all" selected>All years</option>
          <option value="2020-2024">2020–2024 (recent)</option>
          <option value="2010-2019">2010–2019 (decade)</option>
          <option value="2000-2009">2000–2009 (earliest)</option>
        </select>
      </div>
      <div id="trend-chart"></div>
      <script type="application/json" id="trend-data">{{ trend_json }}</script>

      <h3 style="margin-top: 2rem;">Top keyword pairs (co-occurrences)</h3>
      <p>Hover any bar for English translation.</p>
      <div id="bar-chart"></div>
      <script type="application/json" id="bar-data">{{ bar_json }}</script>
    </section>

    <section>
      <h2>4. Engineering excellence</h2>
      <p>
        The original 468-line god class has been decomposed into focused modules
        with a significant increase in test coverage.
      </p>
      <div style="text-align: center; margin: 1rem 0;">
        <img src="data:image/png;base64,{{ refactor_b64 }}"
             alt="Refactor before/after chart"
             style="max-width: 100%; height: auto; border: 1px solid var(--card-border); border-radius: 4px;">
      </div>
    </section>

    <details class="tech-deep-dive">
      <summary>🔬 Tech Deep Dive — Module Dependency Graph (click to expand)</summary>
      <div>
        <p>Evaluation modules + shared config + tests. Arrows = import direction.</p>
        {{ module_graph_svg | safe }}
      </div>
    </details>

    <footer>
      <p>Built {{ build_date }} · Source available on request · All data anonymized</p>
    </footer>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });
  </script>

  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>

  <script>
    const donutData = JSON.parse(document.getElementById('donut-data').textContent);
    Plotly.newPlot('donut-chart', donutData.data, donutData.layout, {responsive: true});

    const trendData = JSON.parse(document.getElementById('trend-data').textContent);
    function renderTrend(filter) {
      const xAll = trendData.data[0].x;
      let xRange;
      if (filter === 'all') xRange = [Math.min(...xAll), Math.max(...xAll)];
      else {
        const [lo, hi] = filter.split('-').map(Number);
        xRange = [lo, hi];
      }
      Plotly.newPlot('trend-chart', trendData.data, {
        ...trendData.layout,
        xaxis: { ...trendData.layout.xaxis, range: xRange },
      }, {responsive: true});
    }
    renderTrend('all');
    document.getElementById('year-filter').addEventListener('change', (e) => renderTrend(e.target.value));

    const barData = JSON.parse(document.getElementById('bar-data').textContent);
    Plotly.newPlot('bar-chart', barData.data, barData.layout, {responsive: true});
  </script>
</body>
</html>
""")