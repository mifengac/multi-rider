# Codex UI Implementation Prompt

## Goal

Rewrite the UI for 4 modules (Dashboard, Profile, Graph, AI Analyst) using the design reference in `docs/claude_design/`. The design is a static SPA prototype with demo data. Your job is to translate it into real Flask Jinja2 templates + vanilla JS that call the existing backend APIs.

**IMPORTANT RULES:**
- Do NOT use any CDN links. All assets are local (offline intranet deployment).
- Do NOT use any icon font (Material Symbols, Font Awesome, etc.). Use inline SVG icons only (see `docs/claude_design/js/icons.js`).
- Do NOT use React, Vue, or any frontend framework. Vanilla JS only.
- Do NOT modify any Python backend files (`routes.py`, services, etc.). Only touch templates, static JS, and static CSS.
- Do NOT touch the main app shell (`templates/index.html`) or any detection/training/face/dispatch modules.
- Use system fonts only: `"PingFang SC","Microsoft YaHei","Hiragino Sans GB",system-ui,sans-serif`.
- ECharts is already available at `static/vendor/echarts.min.js`.
- Tailwind CSS is available at `static/dist/tailwind.css` but the new design primarily uses custom CSS. You may include both.

---

## Architecture Decision: Shared Base Template (NOT SPA)

The design prototype is an SPA with a PageManager. **Do NOT implement it as an SPA.** Instead:

1. Create a **shared base template** `templates/base_sentinel.html` with the common header/nav shell.
2. Each module template **extends** this base template with `{% extends "base_sentinel.html" %}`.
3. Navigation between pages uses **regular `<a href>` links** (`/dashboard`, `/profile/<zjhm>`, `/graph`, `/ai-analyst`).
4. The base template accepts a block variable to highlight the active nav tab.

This approach is simpler, more maintainable, and compatible with the existing Flask routing.

---

## File Map — What to Create/Modify

### New Files to Create

| File | Purpose |
|------|---------|
| `templates/base_sentinel.html` | Shared base template with header, nav, clock |
| `static/shared/css/sentinel.css` | Full design system CSS (from `docs/claude_design/css/styles.css`) |
| `static/shared/js/sentinel-icons.js` | Inline SVG icon library (from `docs/claude_design/js/icons.js`) |
| `static/shared/js/sentinel-utils.js` | Shared utilities: risk badges, ECharts config, formatters, markdown renderer (from `docs/claude_design/js/utils.js`) |

### Files to Rewrite (replace entire content)

| File | Purpose |
|------|---------|
| `templates/modules/dashboard/dashboard.html` | Dashboard page (extends base_sentinel) |
| `templates/modules/profile/profile.html` | Profile page (extends base_sentinel) |
| `templates/modules/graph/graph.html` | Graph page (extends base_sentinel) |
| `templates/modules/ai_analyst/analyst.html` | AI Analyst page (extends base_sentinel) |
| `static/modules/dashboard/dashboard.js` | Dashboard JS with real API calls |
| `static/modules/profile/profile.js` | Profile JS with real API calls |
| `static/modules/graph/graph.js` | Graph JS with real API calls |
| `static/modules/ai_analyst/analyst.js` | AI Analyst JS with real API calls |

---

## Part 1: Shared Base Template

### `templates/base_sentinel.html`

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1920">
  <title>{% block title %}未成年人侵财智能管控中枢{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='dist/tailwind.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='shared/css/sentinel.css') }}">
  <script src="{{ url_for('static', filename='vendor/echarts.min.js') }}"></script>
  <script src="{{ url_for('static', filename='shared/js/sentinel-icons.js') }}"></script>
  <script src="{{ url_for('static', filename='shared/js/sentinel-utils.js') }}"></script>
  {% block head %}{% endblock %}
</head>
<body>
  <div class="app-shell">
    <header class="app-header">
      <div class="header-left">
        <div class="header-logo" id="header-logo"></div>
        <span class="header-title">未成年人侵财智能管控中枢</span>
        <div class="header-divider"></div>
        <span class="header-subtitle">{% block subtitle %}{% endblock %}</span>
      </div>

      <nav class="header-nav">
        <a href="/dashboard" class="nav-tab {% if active_page == 'dashboard' %}active{% endif %}">
          <span class="nav-icon" data-icon="grid"></span>
          态势总览
        </a>
        <a href="/profile/lookup" class="nav-tab {% if active_page == 'profile' %}active{% endif %}">
          <span class="nav-icon" data-icon="user"></span>
          个人画像
        </a>
        <a href="/graph" class="nav-tab {% if active_page == 'graph' %}active{% endif %}">
          <span class="nav-icon" data-icon="network"></span>
          关系图谱
        </a>
        <a href="/ai-analyst" class="nav-tab {% if active_page == 'analyst' %}active{% endif %}">
          <span class="nav-icon" data-icon="sparkles"></span>
          AI 研判
        </a>
        <a href="/" class="nav-tab">
          <span class="nav-icon" data-icon="home"></span>
          工作台
        </a>
      </nav>

      <div class="header-right">
        <span class="header-clock" id="header-clock">00:00:00</span>
        <span class="status-dot" title="系统在线"></span>
      </div>
    </header>

    <div class="page-wrap">
      <div class="page-container">
        {% block content %}{% endblock %}
      </div>
    </div>
  </div>

  <script>
    // Inject nav icons
    document.querySelectorAll('.nav-icon').forEach(function(el) {
      el.innerHTML = icon(el.dataset.icon, 18);
    });
    // Inject logo
    document.getElementById('header-logo').innerHTML = logoSVG(32);
    // Start clock
    startClock(document.getElementById('header-clock'));
  </script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

**Profile lookup note:** The profile page requires a `zjhm` parameter. The nav link should go to a search/lookup page, or you can make `profile/lookup` redirect. For now, the Profile nav link should point to `/profile/lookup`. Add this page route:

Create a simple lookup page at `/profile/lookup` that shows a search input. When the user enters a zjhm and submits, redirect to `/profile/<zjhm>`. OR, you can simply have the Profile nav link NOT exist and instead use a search approach from the Graph page. **The simplest approach**: keep the nav link as `/graph` (since graph has search), and set the Profile page to have no dedicated nav tab (it's always accessed via search from Graph or Dashboard). Update the nav accordingly.

**Actually, the best approach**: Use a "个人画像" nav tab that opens a small search modal (similar to how the graph search works). When the user inputs a zjhm, navigate to `/profile/<zjhm>`. This can be done in JS:

```javascript
// In base template script
document.querySelector('[data-page="profile"]').addEventListener('click', function(e) {
  e.preventDefault();
  var zjhm = prompt('请输入证件号码:');
  if (zjhm && zjhm.trim()) window.location.href = '/profile/' + zjhm.trim();
});
```

Actually, DON'T use browser `prompt()`. Instead: when the user clicks "个人画像" nav tab, navigate to `/graph` and focus the search input. Or better: just leave the nav link as-is and handle the zjhm input within each page's search functionality. The Profile page is always reached from Graph node clicks, Dashboard alert clicks, or AI Analyst links.

**DECISION: Remove the Profile nav link from the top nav. Profile is accessed through:**
1. Clicking a person in the Graph page
2. Clicking an alert in the Dashboard
3. Clicking links in the AI Analyst

---

## Part 2: CSS Design System

### `static/shared/css/sentinel.css`

Copy the full CSS from `docs/claude_design/css/styles.css` with these modifications:

1. Remove the `.page-container.hidden` and multi-page visibility rules (not needed since we use separate pages).
2. Change the `#page-dashboard.page-container:not(.hidden)` grid rule to apply to `.page-container` only on the dashboard page. Use a `.page-dashboard` class instead.
3. Keep everything else as-is — all the design tokens, component styles, dashboard layout, profile layout, graph layout, AI analyst layout.

---

## Part 3: Shared JS Utilities

### `static/shared/js/sentinel-icons.js`

Copy directly from `docs/claude_design/js/icons.js`. No changes needed.

### `static/shared/js/sentinel-utils.js`

Copy from `docs/claude_design/js/utils.js` with these modifications:

1. **Remove the `PageManager` object entirely.** We use server-side routing instead.
2. **Remove `startClock`** — wait, keep it. The base template needs it.
3. **Add a `fetchJSON` helper:**

```javascript
function fetchJSON(url) {
  return fetch(url).then(function(res) {
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  });
}
```

4. **Add an `escapeHtml` function** (from the AI analyst code):

```javascript
function escapeHtml(text) {
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
```

---

## Part 4: Dashboard Implementation

### Template: `templates/modules/dashboard/dashboard.html`

```html
{% extends "base_sentinel.html" %}
{% block title %}态势总览 - 未成年人侵财智能管控中枢{% endblock %}
{% block subtitle %}态势总览{% endblock %}

{% block content %}
<!-- Copy the exact HTML structure from DashboardPage.render() in docs/claude_design/js/dashboard.js -->
<!-- But remove hardcoded demo data from HTML. The JS will populate everything. -->
<!-- Keep skeleton/loading states for charts -->

<div class="dash-kpi-row" id="kpiRow">
  <!-- 4 KPI cards — rendered by JS after API returns -->
</div>

<div class="dash-charts-row">
  <div class="card dash-trend-card">
    <div class="card-head">
      <span class="section-title"><span class="section-icon" data-icon="activity"></span> 月度趋势</span>
      <div class="trend-tabs">
        <button class="trend-tab active" data-series="cases">案件</button>
        <button class="trend-tab" data-series="persons">人员</button>
        <button class="trend-tab" data-series="score">评分</button>
      </div>
    </div>
    <div id="chart-trend" class="chart-box"></div>
  </div>
  <div class="card dash-pie-card">
    <div class="card-head"><span class="section-title"><span class="section-icon" data-icon="target"></span> 风险等级分布</span></div>
    <div id="chart-risk" class="chart-box"></div>
  </div>
  <div class="card dash-pie-card">
    <div class="card-head"><span class="section-title"><span class="section-icon" data-icon="folder"></span> 案件类型分布</span></div>
    <div id="chart-crime" class="chart-box"></div>
  </div>
</div>

<div class="dash-bottom-row">
  <div class="card dash-rank-card">
    <div class="card-head"><span class="section-title"><span class="section-icon" data-icon="barChart"></span> 辖区排名</span></div>
    <div id="chart-district" class="chart-box"></div>
  </div>
  <div class="card dash-age-card">
    <div class="card-head"><span class="section-title"><span class="section-icon" data-icon="users"></span> 年龄分布</span></div>
    <div id="chart-age" class="chart-box"></div>
  </div>
  <div class="card dash-alert-card">
    <div class="card-head">
      <span class="section-title"><span class="section-icon" data-icon="bell"></span> 实时预警流</span>
      <span class="pulse-dot"></span>
    </div>
    <div class="alert-list" id="alert-list"></div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='modules/dashboard/dashboard.js') }}"></script>
{% endblock %}
```

### JS: `static/modules/dashboard/dashboard.js`

The design prototype has demo data in `DashboardPage`. Replace ALL demo data with real API calls.

**API Endpoints to call:**

| Data | API Call | Response Shape |
|------|----------|----------------|
| KPI cards | `GET /api/dashboard/summary` | `{total_persons, high_risk_count, month_cases, avg_score}` |
| Trend chart | `GET /api/dashboard/trend?months=12&metric=cases` | `{points: [{month, count}]}` |
| Risk distribution | `GET /api/dashboard/distribution?dim=risk_level` | `{items: [{label, value}]}` where label is "extreme","high","medium","low","normal" |
| Case type distribution | `GET /api/dashboard/distribution?dim=case_type` | `{items: [{label, value}]}` |
| Area ranking | `GET /api/dashboard/ranking?metric=risk_count` | `{items: [{label, value}]}` |
| Age distribution | `GET /api/dashboard/distribution?dim=age` | `{items: [{label, value}]}` |
| Alerts | `GET /api/dashboard/alerts?limit=20` | `{items: [{id, name, risk_level, message, time, zjhm}]}` |

**KPI Card Rendering:**

```javascript
(function() {
  var API = '/api/dashboard';
  var charts = [];

  // --- KPI ---
  function loadKPI() {
    fetchJSON(API + '/summary').then(function(d) {
      var KPI = [
        { title: '管控总人数', value: d.total_persons || 0, color: '#38bdf8', iconName: 'users', trend: null, suffix: '人' },
        { title: '高风险人数', value: d.high_risk_count || 0, color: '#f97316', iconName: 'alertTriangle', trend: null, suffix: '人' },
        { title: '本月新增案件', value: d.month_cases || 0, color: '#ef4444', iconName: 'folder', trend: null, suffix: '起' },
        { title: '平均风险评分', value: d.avg_score || 0, color: '#eab308', iconName: 'target', trend: null, suffix: '分', isFloat: true },
      ];
      var html = '';
      KPI.forEach(function(k, i) {
        html += '<div class="kpi-card" style="--kpi-color:' + k.color + '">' +
          '<div class="kpi-header">' +
            '<span class="kpi-icon" style="color:' + k.color + '">' + icon(k.iconName, 20) + '</span>' +
            '<span class="kpi-title">' + k.title + '</span>' +
          '</div>' +
          '<div class="kpi-body">' +
            '<span class="kpi-value glow-number" data-target="' + k.value + '" style="color:' + k.color + '">0</span>' +
            '<span class="kpi-suffix">' + k.suffix + '</span>' +
          '</div>' +
          '<div class="kpi-footer">' +
            '<span class="kpi-trend" style="color:var(--text-muted)">累计数据</span>' +
          '</div>' +
        '</div>';
      });
      document.getElementById('kpiRow').innerHTML = html;
      // Animate numbers
      document.querySelectorAll('.kpi-value').forEach(function(el) {
        animateNumber(el, parseFloat(el.dataset.target), 1200);
      });
    });
  }

  // ... similar pattern for each chart section
})();
```

**Trend Chart with Tab Switching:**

```javascript
function loadTrendChart() {
  var trendChart = echarts.init(document.getElementById('chart-trend'));
  charts.push(trendChart);
  var currentSeries = 'cases';

  function updateTrend(metric) {
    fetchJSON(API + '/trend?months=12&metric=' + metric).then(function(d) {
      var points = d.points || [];
      var base = echartBaseOption();
      var axDef = echartAxisDefaults();
      trendChart.setOption({
        backgroundColor: 'transparent',
        tooltip: Object.assign({}, base.tooltip, { trigger: 'axis' }),
        grid: { left: 40, right: 16, top: 20, bottom: 28 },
        xAxis: Object.assign({ type: 'category', data: points.map(function(p){return p.month;}), boundaryGap: false }, axDef),
        yAxis: Object.assign({ type: 'value' }, axDef),
        series: [{
          type: 'line', data: points.map(function(p){return p.count;}), smooth: true,
          symbol: 'circle', symbolSize: 6,
          lineStyle: { color: '#38bdf8', width: 2.5, shadowColor: 'rgba(56,189,248,0.4)', shadowBlur: 8 },
          itemStyle: { color: '#38bdf8', borderColor: '#0f1729', borderWidth: 2 },
          areaStyle: { color: cyanAreaGradient(0.2) },
        }],
      }, true);
    });
  }
  updateTrend('cases');

  // Tab switching
  delegate(document.querySelector('.trend-tabs'), '.trend-tab', 'click', function(e, tab) {
    document.querySelectorAll('.trend-tab').forEach(function(t) { t.classList.remove('active'); });
    tab.classList.add('active');
    updateTrend(tab.dataset.series);
  });
}
```

**Risk Distribution Chart:**

```javascript
function loadRiskChart() {
  fetchJSON(API + '/distribution?dim=risk_level').then(function(d) {
    var chart = echarts.init(document.getElementById('chart-risk'));
    charts.push(chart);
    var colorMap = { extreme: '#ef4444', high: '#f97316', medium: '#eab308', low: '#3b82f6', normal: '#22c55e' };
    var labelMap = { extreme: '极高', high: '高', medium: '中', low: '低', normal: '正常' };
    var data = (d.items || []).map(function(i) {
      return { name: labelMap[i.label] || i.label, value: i.value, itemStyle: { color: colorMap[i.label] || '#6b7280' } };
    });
    var total = data.reduce(function(s, d) { return s + d.value; }, 0);
    // Use the exact same ECharts option from docs/claude_design/js/dashboard.js riskChart section
    // but with real data instead of RISK_DIST
    chart.setOption(/* ... same option structure as design prototype ... */);
  });
}
```

**Alert List:**

```javascript
function loadAlerts() {
  fetchJSON(API + '/alerts?limit=20').then(function(d) {
    var list = document.getElementById('alert-list');
    var items = d.items || [];
    if (items.length === 0) {
      list.innerHTML = emptyState('bell', '暂无预警', '系统运行正常');
      return;
    }
    var html = '';
    items.forEach(function(a) {
      var risk = a.risk_level || 'normal';
      html += '<div class="alert-item fade-in" style="' + riskBar(risk) + '">' +
        '<div class="alert-item-top">' +
          '<span class="alert-name">' + escapeHtml(a.name || '--') + '</span>' +
          '<span class="alert-time">' + escapeHtml(a.time || '') + '</span>' +
          riskBadge(risk) +
        '</div>' +
        '<div class="alert-msg">' + escapeHtml(a.message || '') + '</div>' +
        (a.zjhm ? '<a class="alert-link" href="/profile/' + a.zjhm + '">查看详情 ' + icon('chevronRight', 14) + '</a>' : '') +
      '</div>';
    });
    list.innerHTML = html;
  });
}
```

**IMPORTANT:** Follow the exact same ECharts option structure, colors, gradients, and styling from the design prototype. The design code in `docs/claude_design/js/dashboard.js` is the visual source of truth. Just replace demo arrays with API data.

**Init pattern:**

```javascript
// Call all loaders
loadKPI();
loadTrendChart();
loadRiskChart();
loadCrimeChart();
loadRankingChart();
loadAgeChart();
loadAlerts();

// Inject section icons
document.querySelectorAll('.section-icon').forEach(function(el) {
  el.outerHTML = icon(el.dataset.icon, 16);
});

// Resize handler
var resizeHandler = debounce(function() {
  charts.forEach(function(c) { if (!c.isDisposed()) c.resize(); });
}, 200);
window.addEventListener('resize', resizeHandler);

// Auto-refresh alerts every 30s
setInterval(loadAlerts, 30000);
```

---

## Part 5: Profile Implementation

### Template: `templates/modules/profile/profile.html`

The template receives `{{ zjhm }}` from the Flask page route. It extends `base_sentinel.html`.

```html
{% extends "base_sentinel.html" %}
{% block title %}个人画像 - {{ zjhm }}{% endblock %}
{% block subtitle %}个人画像{% endblock %}

{% block content %}
<div id="profileLoading">
  <!-- skeleton loading state -->
</div>
<div id="profileContent" style="display:none">
  <!-- Profile header card + body will be rendered by JS -->
</div>
<div id="profileError" style="display:none">
  <!-- error state -->
</div>
{% endblock %}

{% block scripts %}
<script>var ZJHM = "{{ zjhm }}";</script>
<script src="{{ url_for('static', filename='modules/profile/profile.js') }}"></script>
{% endblock %}
```

### JS: `static/modules/profile/profile.js`

**API Call:** `GET /api/profile/<zjhm>` returns:

```json
{
  "basic": {
    "xm": "张某辉",
    "xb": "男",
    "age": 16,
    "zjhm": "610102200812****",
    "hjdz": "陕西省西安市新城区"
  },
  "score": {
    "total_score": 78,
    "risk_level": "high",
    "dimensions": {
      "case": {"score": 24, "max": 30, "detail": {...}},
      "behavior": {"score": 18, "max": 25, "detail": {...}},
      "family": {"score": 16, "max": 20, "detail": {...}},
      "education": {"score": 12, "max": 15, "detail": {...}},
      "social": {"score": 8, "max": 10, "detail": {...}}
    }
  },
  "cases": [
    {"ajbh": "...", "ay": "盗窃", "ajmc": "新城区系列盗窃案", "fasj": "2026-03-15", "unit": "新城分局刑侦大队"}
  ],
  "co_suspects": [
    {"zjhm": "...", "xm": "李某阳", "shared_cases": 5}
  ],
  "family": {
    "guardian_name": "张某国",
    "guardian_relation": "父亲",
    "guardian_phone": "138****5672",
    "family_situation": "...",
    "difficulty_type": "...",
    "child_type": "..."
  },
  "education": {
    "status": "辍学",
    "school": "...",
    "detail": "..."
  },
  "trajectory": {
    "recent": [...],
    "hotspots": [{"place": "...", "count": 23}],
    "time_pattern": [1,0,2,1,...],  // 24 hours array
    "last_seen": {"time": "...", "place": "..."}
  },
  "suggestions": ["建议1", "建议2", ...]
}
```

**Note:** The actual response shape may differ slightly from the above. The JS should handle missing/null fields gracefully. Check the actual API response by reading `modules/profile/services/profile_assembler.py` if needed.

**Rendering approach:** Follow the exact same HTML structure from `ProfilePage.render()` in `docs/claude_design/js/profile.js`, but replace hardcoded demo data with API response fields.

```javascript
(function() {
  fetchJSON('/api/profile/' + ZJHM).then(function(data) {
    if (!data || !data.basic) {
      showError('未找到该人员信息');
      return;
    }
    renderProfile(data);
  }).catch(function(err) {
    showError('加载失败: ' + err.message);
  });

  function renderProfile(data) {
    document.getElementById('profileLoading').style.display = 'none';
    var content = document.getElementById('profileContent');
    content.style.display = 'block';

    var p = data.basic;
    var score = data.score || {};
    var riskLevel = score.risk_level || 'normal';
    var totalScore = score.total_score || 0;
    var dims = score.dimensions || {};

    // Build the profile HTML following the design prototype structure
    content.innerHTML = /* ... same structure as ProfilePage.render() but with real data ... */;

    // Initialize charts (hours chart, etc.)
    initProfileCharts(data);

    // Animate risk progress bar
    setTimeout(function() {
      document.querySelectorAll('.risk-progress-bar').forEach(function(bar) {
        bar.style.width = bar.dataset.targetWidth;
      });
    }, 100);
  }
})();
```

**Inter-page links:**
- "展开关系图谱" button → `window.location.href = '/graph?zjhm=' + ZJHM`
- Co-suspect name click → `window.location.href = '/profile/' + coSuspectZjhm`

---

## Part 6: Graph Implementation

### Template: `templates/modules/graph/graph.html`

```html
{% extends "base_sentinel.html" %}
{% block title %}关系图谱 - 未成年人侵财智能管控中枢{% endblock %}
{% block subtitle %}关系图谱{% endblock %}

{% block content %}
<!-- Copy the exact HTML from GraphPage.render() in docs/claude_design/js/graph.js -->
<div class="graph-layout">
  <div class="graph-main">
    <div class="graph-toolbar">
      <div class="graph-search-wrap">
        <span class="graph-search-icon" data-icon="search"></span>
        <input class="graph-search-input" id="graph-search" placeholder="输入姓名 / 身份证号 / 案件编号..." />
        <button class="btn-primary graph-search-btn" id="graph-search-btn"><span data-icon="search"></span> 搜索</button>
      </div>
      <div class="graph-depth-toggle">
        <button class="depth-btn active" data-depth="1">1层</button>
        <button class="depth-btn" data-depth="2">2层</button>
      </div>
    </div>
    <div id="graph-canvas" class="graph-canvas"></div>
    <div id="graph-empty" class="graph-empty">
      <div class="graph-empty-icon"><!-- network icon 64px --></div>
      <div class="graph-empty-title">搜索姓名或身份证号，展开关系图谱</div>
      <div class="graph-empty-sub">支持按人员、案件、学校等维度探索关联关系</div>
    </div>
    <div class="graph-legend" id="graph-legend" style="display:none">
      <!-- legend items -->
    </div>
  </div>
  <div class="graph-drawer" id="graph-drawer">
    <div class="drawer-header">
      <span class="drawer-title">节点详情</span>
      <button class="drawer-close" id="drawer-close"><!-- x icon --></button>
    </div>
    <div class="drawer-body" id="drawer-body"></div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='modules/graph/graph.js') }}"></script>
<script>
  // If URL has ?zjhm= parameter, auto-search on load
  (function() {
    var params = new URLSearchParams(window.location.search);
    var zjhm = params.get('zjhm');
    if (zjhm) {
      document.getElementById('graph-search').value = zjhm;
      if (typeof doGraphSearch === 'function') doGraphSearch(zjhm);
    }
  })();
</script>
{% endblock %}
```

### JS: `static/modules/graph/graph.js`

**API Endpoints:**

| Action | API Call | Response |
|--------|----------|----------|
| Search nodes | `GET /api/graph/search?keyword=xxx` | `{results: [{zjhm, xm, type}]}` |
| Build graph | `GET /api/graph/person/<zjhm>?depth=1` | `{nodes: [{id, name, type, ...}], links: [{source, target, label, ...}]}` |
| Shortest path | `GET /api/graph/paths?from=x&to=y` | `{found, path, hops}` |

**Search Flow:**
1. User types keyword → click search (or Enter)
2. Call `GET /api/graph/search?keyword=xxx`
3. If exactly 1 result → directly build graph for that person
4. If multiple results → show a dropdown/list to pick
5. Call `GET /api/graph/person/<zjhm>?depth=<depth>` to get graph data

**Graph Rendering:**
The `build_person_graph()` API returns nodes and links in a format close to what ECharts needs. Map API response to ECharts graph option using the same visual style from `docs/claude_design/js/graph.js`:

```javascript
function buildGraphOption(apiData) {
  var NODE_TYPE_MAP = {
    person:   { color: '#38bdf8', symbol: 'circle', size: 36 },
    highrisk: { color: '#ef4444', symbol: 'circle', size: 44 },
    case:     { color: '#a855f7', symbol: 'roundRect', size: 32 },
    school:   { color: '#f59e0b', symbol: 'triangle', size: 32 },
    guardian: { color: '#10b981', symbol: 'diamond', size: 30 },
  };

  var eNodes = (apiData.nodes || []).map(function(n) {
    var t = NODE_TYPE_MAP[n.type] || NODE_TYPE_MAP.person;
    return {
      id: n.id, name: n.name || n.xm || n.id,
      symbolSize: t.size, symbol: t.symbol,
      itemStyle: { color: t.color, borderColor: t.color, borderWidth: 2, shadowColor: t.color + '60', shadowBlur: 10 },
      label: { show: true, color: '#e6edf7', fontSize: 11, position: 'bottom', distance: 5 },
      _data: n,  // store original for drawer
    };
  });

  var eLinks = (apiData.links || []).map(function(l) {
    var isAccomplice = l.type === 'accomplice' || l.label === '共犯';
    return {
      source: l.source, target: l.target,
      label: { show: true, formatter: l.label || '', color: '#5b6b80', fontSize: 9 },
      lineStyle: {
        color: isAccomplice ? 'rgba(239,68,68,0.6)' : 'rgba(56,189,248,0.25)',
        width: isAccomplice ? 2.5 : 1.2,
        curveness: 0.1,
      },
    };
  });

  return {
    backgroundColor: 'transparent',
    animationDuration: 800,
    series: [{
      type: 'graph', layout: 'force', roam: true, draggable: true,
      data: eNodes, links: eLinks,
      force: { repulsion: 320, edgeLength: [80, 180], gravity: 0.08 },
      emphasis: { focus: 'adjacency', blurScope: 'global' },
      scaleLimit: { min: 0.4, max: 3 },
    }],
  };
}
```

**Node Click → Drawer:**
When user clicks a node, show the side drawer with node details. If the node is a person, show a "查看画像" button that links to `/profile/<zjhm>`.

---

## Part 7: AI Analyst Implementation

### Template: `templates/modules/ai_analyst/analyst.html`

Extends `base_sentinel.html`. Copy the layout from `AIAnalystPage.render()` in `docs/claude_design/js/ai-analyst.js`.

### JS: `static/modules/ai_analyst/analyst.js`

This is the most complex module because it uses Server-Sent Events (SSE) for streaming.

**API Endpoints:**

| Action | API Call | Payload | Response |
|--------|----------|---------|----------|
| Chat | `POST /api/ai/chat` | `{message, history, mode: "general"\|"rag"}` | SSE stream |
| Person analysis | `POST /api/ai/analyze/person` | `{zjhm}` | SSE stream |
| Serial analysis | `POST /api/ai/analyze/serial` | `{months: 6}` | SSE stream |

**SSE Stream Format:**
```
data: {"content": "partial text chunk"}
data: {"content": "more text"}
data: {"meta": {"case_count": 287, "pair_count": 2}}  // serial analysis only
data: {"error": "error message"}                        // on error
data: [DONE]                                            // end of stream
```

**Real Streaming Implementation (replace simulated typing from design prototype):**

```javascript
function sendToAPI(url, body, onMeta) {
  isGenerating = true;
  updateSendBtn();

  // Add thinking indicator
  showThinking();

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(function(response) {
    removeThinking();
    var reader = response.body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';
    var fullContent = '';

    // Add empty AI message placeholder
    messages.push({ role: 'ai', content: '' });
    var idx = messages.length - 1;

    function read() {
      reader.read().then(function(result) {
        if (result.done) {
          isGenerating = false;
          updateSendBtn();
          return;
        }
        buffer += decoder.decode(result.value, { stream: true });
        var lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line in buffer

        lines.forEach(function(line) {
          if (!line.startsWith('data: ')) return;
          var payload = line.substring(6).trim();
          if (payload === '[DONE]') {
            isGenerating = false;
            updateSendBtn();
            return;
          }
          try {
            var data = JSON.parse(payload);
            if (data.content) {
              fullContent += data.content;
              messages[idx].content = fullContent;
              renderMessages();
            }
            if (data.meta && onMeta) {
              onMeta(data.meta);
            }
            if (data.error) {
              fullContent += '\n\n**错误:** ' + data.error;
              messages[idx].content = fullContent;
              renderMessages();
            }
          } catch(e) { /* ignore parse errors */ }
        });
        read(); // continue reading
      });
    }
    read();
  }).catch(function(err) {
    removeThinking();
    addMessage('ai', '网络请求失败: ' + err.message);
    isGenerating = false;
    updateSendBtn();
  });
}
```

**Chat message sending:**

```javascript
function sendMessage() {
  var text = inputBox.value.trim();
  if (!text || isGenerating) return;
  inputBox.value = '';
  inputBox.style.height = 'auto';

  addMessage('user', text);
  chatHistory.push({ role: 'user', content: text });

  sendToAPI('/api/ai/chat', {
    message: text,
    history: chatHistory,
    mode: ragMode ? 'rag' : 'general',
  });
}
```

**Person analysis:**

```javascript
function startPersonAnalysis() {
  // Show modal (same as design prototype)
  document.getElementById('modal-person').style.display = 'flex';
}

function submitPersonAnalysis(zjhm) {
  document.getElementById('modal-person').style.display = 'none';
  addMessage('user', '请对证件号 ' + zjhm + ' 进行人员研判分析');
  sendToAPI('/api/ai/analyze/person', { zjhm: zjhm });
}
```

**Serial analysis:**

```javascript
function startSerialAnalysis() {
  addMessage('user', '请进行串并案分析，发现近期侵财系列案线索');
  sendToAPI('/api/ai/analyze/serial', { months: 6 }, function(meta) {
    if (meta) {
      var metaText = '已检索 ' + (meta.case_count || 0) + ' 起案件';
      if (meta.pair_count) metaText += '，发现 ' + meta.pair_count + ' 组相似对';
      if (meta.used_embedding === false) metaText += '（纯AI分析模式）';
      addMessage('meta', metaText);
    }
  });
}
```

---

## Part 8: CSS Adjustments

After copying `docs/claude_design/css/styles.css` to `static/shared/css/sentinel.css`, make these changes:

1. The dashboard page needs `display: grid` on its `.page-container`. Since we use separate pages, add a CSS class:

```css
/* Dashboard grid layout */
.page-dashboard {
  display: grid;
  grid-template-rows: auto 1fr 1fr;
  gap: 0;
  overflow: hidden;
}
```

Then in `dashboard.html`, add class to the page-container block or wrap content in a `<div class="page-dashboard">`.

2. The profile and graph pages need full-height layouts. Add:

```css
/* Graph full-height */
.page-graph { height: 100%; }
.page-graph .graph-layout { height: 100%; }

/* AI Analyst full-height */
.page-analyst { height: 100%; }
.page-analyst .ai-layout { height: 100%; }
```

3. Ensure the `.page-container` has `height: 100%` and proper overflow for each page type.

---

## Part 9: Edge Cases and Error Handling

1. **Empty API responses:** Always show the `emptyState()` helper from `sentinel-utils.js` when data arrays are empty.
2. **API errors:** Show `errorState()` in the relevant card/section. Don't crash the whole page.
3. **Null fields:** Many API fields may be null. Always use `|| ''` or `|| '--'` fallbacks.
4. **Graph search no results:** Show a message "未找到相关人员或案件" in the graph area.
5. **Profile not found:** Show error state with "未找到该人员信息" and a link back to the graph search.
6. **AI service unavailable:** The SSE stream may return `{error: "..."}`. Display it in the chat as an error message.
7. **Long loading times:** Show skeleton screens (use the `skeleton()` helper) while waiting for API responses.

---

## Part 10: Visual Reference

The visual source of truth is in `docs/claude_design/`. Open `docs/claude_design/index.html` in a browser to see the exact visual result. Your implementation must match this visual output pixel-for-pixel (within reasonable tolerance for dynamic data differences).

Key visual details to preserve:
- **Background:** `#0a0e1a` with subtle dot grid pattern
- **Top gradient line:** 1px cyan→blue gradient at top of viewport
- **Cards:** `#0f1729` background with `rgba(56,189,248,0.14)` borders
- **Glow effects:** cyan box-shadow on hover, text-shadow on numbers
- **Charts:** transparent background, dark axis lines, cyan gradients
- **Typography:** monospace numbers, uppercase section titles with left border accent
- **Timeline:** left-border with dot indicators
- **Scrollbars:** thin (6px) with subtle thumb color

---

## Summary Checklist

- [ ] `templates/base_sentinel.html` — shared nav shell
- [ ] `static/shared/css/sentinel.css` — full design system
- [ ] `static/shared/js/sentinel-icons.js` — SVG icons
- [ ] `static/shared/js/sentinel-utils.js` — shared utilities (no PageManager)
- [ ] `templates/modules/dashboard/dashboard.html` — extends base, uses real APIs
- [ ] `static/modules/dashboard/dashboard.js` — fetches from `/api/dashboard/*`
- [ ] `templates/modules/profile/profile.html` — extends base, receives `{{ zjhm }}`
- [ ] `static/modules/profile/profile.js` — fetches from `/api/profile/<zjhm>`
- [ ] `templates/modules/graph/graph.html` — extends base, search + ECharts graph
- [ ] `static/modules/graph/graph.js` — fetches from `/api/graph/*`
- [ ] `templates/modules/ai_analyst/analyst.html` — extends base, chat UI
- [ ] `static/modules/ai_analyst/analyst.js` — SSE streaming from `/api/ai/*`
- [ ] All charts use dark theme config from `echartBaseOption()` and `echartAxisDefaults()`
- [ ] No CDN links, no icon fonts, no framework dependencies
- [ ] All navigation uses `<a href>` links (not SPA routing)
- [ ] Error states and empty states handled gracefully
