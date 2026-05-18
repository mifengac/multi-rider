// ============================================================
// dashboard.js - 态势总览 Dashboard
// ============================================================

var DashboardPage = (function() {
  var charts = [];
  var intervals = [];

  // ---- 演示数据 ----
  var KPI = [
    { title: '管控总人数', value: 2847, color: '#38bdf8', icon: 'users', trend: null, suffix: '人' },
    { title: '高风险人数', value: 186, color: '#f97316', icon: 'alertTriangle', trend: 12.3, suffix: '人' },
    { title: '本月新增案件', value: 43, color: '#ef4444', icon: 'folder', trend: -8.5, suffix: '起' },
    { title: '平均风险评分', value: 42.6, color: '#eab308', icon: 'target', trend: 3.1, suffix: '分', isFloat: true },
  ];

  var MONTHS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  var TREND_CASES   = [38,42,35,48,52,45,41,39,47,51,43,40];
  var TREND_PERSONS  = [210,225,198,240,255,230,218,205,235,248,220,212];
  var TREND_SCORES   = [39,41,38,43,45,42,40,39,44,46,42,41];

  var RISK_DIST = [
    { value: 42,  name: '极高', itemStyle: { color: '#ef4444' } },
    { value: 144, name: '高',   itemStyle: { color: '#f97316' } },
    { value: 387, name: '中',   itemStyle: { color: '#eab308' } },
    { value: 891, name: '低',   itemStyle: { color: '#3b82f6' } },
    { value: 1383,name: '正常', itemStyle: { color: '#22c55e' } },
  ];

  var CRIME_DIST = [
    { value: 456, name: '盗窃', itemStyle: { color: '#38bdf8' } },
    { value: 87,  name: '抢劫', itemStyle: { color: '#ef4444' } },
    { value: 63,  name: '抢夺', itemStyle: { color: '#f97316' } },
    { value: 234, name: '诈骗', itemStyle: { color: '#a855f7' } },
    { value: 45,  name: '敲诈勒索', itemStyle: { color: '#eab308' } },
  ];

  var DISTRICTS = [
    { name: '新城区分局', value: 42 }, { name: '碑林区分局', value: 38 },
    { name: '雁塔区分局', value: 35 }, { name: '未央区分局', value: 31 },
    { name: '莲湖区分局', value: 28 }, { name: '灞桥区分局', value: 24 },
    { name: '长安区分局', value: 21 }, { name: '临潼区分局', value: 17 },
  ];

  var AGE_DIST = [
    { name: '14岁以下', value: 312, itemStyle: { color: '#38bdf8' } },
    { name: '14-16岁',  value: 1245, itemStyle: { color: '#3b82f6' } },
    { name: '16-18岁',  value: 1290, itemStyle: { color: '#a855f7' } },
  ];

  var ALERT_NAMES = ['张某辉','李某阳','王某飞','赵某杰','陈某龙','刘某伟','周某浩','吴某明','郑某强','孙某磊'];
  var ALERT_TYPES = ['extreme','high','high','medium','extreme','high','medium','low','high','extreme'];
  var ALERT_MSGS  = [
    '夜间多次出现在商业区，行为异常，风险上升',
    '与已知团伙成员频繁接触，存在共犯风险',
    '近一周内涉嫌2起盗窃案件，需重点关注',
    '辍学状态持续3个月，家庭监管缺失',
    '凌晨在ATM取款点徘徊，行为高度可疑',
    '旅馆入住频率异常，与多名未成年人同住',
    '多次在学校周边出现，涉嫌敲诈勒索在校学生',
    '风险评分近期上升12分，需跟进评估',
    '与涉案人员存在3次以上共同轨迹重合',
    '新发盗窃案件关联嫌疑人，建议立即管控',
  ];

  function generateAlerts() {
    var now = new Date();
    var html = '';
    for (var i = 0; i < ALERT_NAMES.length; i++) {
      var t = new Date(now - (i * 180 + Math.random() * 120) * 1000);
      var timeStr = String(t.getHours()).padStart(2,'0') + ':' + String(t.getMinutes()).padStart(2,'0') + ':' + String(t.getSeconds()).padStart(2,'0');
      var risk = ALERT_TYPES[i];
      var rc = RISK_CONFIG[risk];
      html += '<div class="alert-item fade-in" style="' + riskBar(risk) + '">' +
        '<div class="alert-item-top">' +
          '<span class="alert-name">' + ALERT_NAMES[i] + '</span>' +
          '<span class="alert-time">' + timeStr + '</span>' +
          riskBadge(risk) +
        '</div>' +
        '<div class="alert-msg">' + ALERT_MSGS[i] + '</div>' +
        '<a class="alert-link" href="javascript:void(0)" onclick="PageManager.switchTo(\'profile\')">' +
          '查看详情 ' + icon('chevronRight', 14) +
        '</a>' +
      '</div>';
    }
    return html;
  }

  // ---- 渲染 ----
  function render(container) {
    // KPI Cards
    var kpiHtml = '';
    KPI.forEach(function(k, i) {
      kpiHtml += '<div class="kpi-card" style="--kpi-color:' + k.color + '">' +
        '<div class="kpi-header">' +
          '<span class="kpi-icon" style="color:' + k.color + '">' + icon(k.icon, 20) + '</span>' +
          '<span class="kpi-title">' + k.title + '</span>' +
        '</div>' +
        '<div class="kpi-body">' +
          '<span class="kpi-value glow-number" data-target="' + k.value + '" data-float="' + (k.isFloat||false) + '" style="color:' + k.color + '">0</span>' +
          '<span class="kpi-suffix">' + k.suffix + '</span>' +
        '</div>' +
        '<div class="kpi-footer">' +
          (k.trend !== null ? '<span class="kpi-trend">同比 ' + trendArrow(k.trend) + '</span>' : '<span class="kpi-trend" style="color:var(--text-muted)">累计数据</span>') +
          '<div class="kpi-spark" id="spark-' + i + '"></div>' +
        '</div>' +
      '</div>';
    });

    container.innerHTML =
      // Row 1: KPI
      '<div class="dash-kpi-row">' + kpiHtml + '</div>' +

      // Row 2: Charts
      '<div class="dash-charts-row">' +
        '<div class="card dash-trend-card">' +
          '<div class="card-head">' +
            '<span class="section-title">' + icon('activity', 16) + ' 月度趋势</span>' +
            '<div class="trend-tabs">' +
              '<button class="trend-tab active" data-series="cases">案件</button>' +
              '<button class="trend-tab" data-series="persons">人员</button>' +
              '<button class="trend-tab" data-series="scores">评分</button>' +
            '</div>' +
          '</div>' +
          '<div id="chart-trend" class="chart-box"></div>' +
        '</div>' +
        '<div class="card dash-pie-card">' +
          '<div class="card-head"><span class="section-title">' + icon('target', 16) + ' 风险等级分布</span></div>' +
          '<div id="chart-risk" class="chart-box"></div>' +
        '</div>' +
        '<div class="card dash-pie-card">' +
          '<div class="card-head"><span class="section-title">' + icon('folder', 16) + ' 案件类型分布</span></div>' +
          '<div id="chart-crime" class="chart-box"></div>' +
        '</div>' +
      '</div>' +

      // Row 3: Bottom
      '<div class="dash-bottom-row">' +
        '<div class="card dash-rank-card">' +
          '<div class="card-head"><span class="section-title">' + icon('barChart', 16) + ' 辖区排名（高风险人数）</span></div>' +
          '<div id="chart-district" class="chart-box"></div>' +
        '</div>' +
        '<div class="card dash-age-card">' +
          '<div class="card-head"><span class="section-title">' + icon('users', 16) + ' 年龄分布</span></div>' +
          '<div id="chart-age" class="chart-box"></div>' +
        '</div>' +
        '<div class="card dash-alert-card">' +
          '<div class="card-head">' +
            '<span class="section-title">' + icon('bell', 16) + ' 实时预警流</span>' +
            '<span class="pulse-dot"></span>' +
          '</div>' +
          '<div class="alert-list" id="alert-list">' + generateAlerts() + '</div>' +
        '</div>' +
      '</div>';
  }

  // ---- 图表初始化 ----
  function init() {
    // 延迟一帧确保布局完成后再初始化图表
    requestAnimationFrame(function() { requestAnimationFrame(function() { initCharts(); }); });
  }

  function initCharts() {
    // 数字滚动
    document.querySelectorAll('.kpi-value').forEach(function(el) {
      var target = parseFloat(el.dataset.target);
      var isFloat = el.dataset.float === 'true';
      animateNumber(el, target, 1200);
    });

    // 趋势图
    var trendChart = echarts.init(document.getElementById('chart-trend'));
    charts.push(trendChart);

    var trendData = { cases: TREND_CASES, persons: TREND_PERSONS, scores: TREND_SCORES };
    var currentSeries = 'cases';

    function updateTrend(series) {
      var base = echartBaseOption();
      var axDef = echartAxisDefaults();
      trendChart.setOption({
        backgroundColor: 'transparent',
        tooltip: Object.assign({}, base.tooltip, { trigger: 'axis' }),
        grid: { left: 40, right: 16, top: 20, bottom: 28 },
        xAxis: Object.assign({ type: 'category', data: MONTHS, boundaryGap: false }, axDef),
        yAxis: Object.assign({ type: 'value' }, axDef),
        series: [{
          type: 'line', data: trendData[series], smooth: true,
          symbol: 'circle', symbolSize: 6,
          lineStyle: { color: '#38bdf8', width: 2.5, shadowColor: 'rgba(56,189,248,0.4)', shadowBlur: 8 },
          itemStyle: { color: '#38bdf8', borderColor: '#0f1729', borderWidth: 2 },
          areaStyle: { color: cyanAreaGradient(0.2) },
          animationDuration: 800, animationEasing: 'cubicOut',
        }],
      }, true);
    }
    updateTrend('cases');

    delegate(document.querySelector('.trend-tabs'), '.trend-tab', 'click', function(e, tab) {
      document.querySelectorAll('.trend-tab').forEach(function(t) { t.classList.remove('active'); });
      tab.classList.add('active');
      currentSeries = tab.dataset.series;
      updateTrend(currentSeries);
    });

    // 风险分布环形图
    var riskChart = echarts.init(document.getElementById('chart-risk'));
    charts.push(riskChart);
    var total = RISK_DIST.reduce(function(s, d) { return s + d.value; }, 0);
    riskChart.setOption(Object.assign({}, echartBaseOption(), {
      tooltip: Object.assign({}, echartBaseOption().tooltip, { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' }),
      series: [{
        type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'],
        data: RISK_DIST, label: { show: true, color: '#94a3b8', fontSize: 11, formatter: '{b}\n{d}%' },
        labelLine: { lineStyle: { color: 'rgba(148,163,184,0.3)' } },
        emphasis: { scaleSize: 6 },
        animationDuration: 800,
      }],
      graphic: [{
        type: 'group', left: 'center', top: '50%',
        children: [
          { type: 'text', style: { text: formatNum(total), fill: '#e6edf7', fontSize: 22, fontWeight: 'bold', fontFamily: 'ui-monospace,"SF Mono",Consolas,monospace', textAlign: 'center', textVerticalAlign: 'bottom' }, left: 'center', top: -8 },
          { type: 'text', style: { text: '总人数', fill: '#5b6b80', fontSize: 11, textAlign: 'center', textVerticalAlign: 'top' }, left: 'center', top: 8 },
        ],
      }],
    }));

    // 案件类型环形图
    var crimeChart = echarts.init(document.getElementById('chart-crime'));
    charts.push(crimeChart);
    var crimeTotal = CRIME_DIST.reduce(function(s, d) { return s + d.value; }, 0);
    crimeChart.setOption(Object.assign({}, echartBaseOption(), {
      tooltip: Object.assign({}, echartBaseOption().tooltip, { trigger: 'item', formatter: '{b}: {c}起 ({d}%)' }),
      series: [{
        type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'],
        data: CRIME_DIST, label: { show: true, color: '#94a3b8', fontSize: 11, formatter: '{b}\n{d}%' },
        labelLine: { lineStyle: { color: 'rgba(148,163,184,0.3)' } },
        emphasis: { scaleSize: 6 },
        animationDuration: 800,
      }],
      graphic: [{
        type: 'group', left: 'center', top: '50%',
        children: [
          { type: 'text', style: { text: formatNum(crimeTotal), fill: '#e6edf7', fontSize: 22, fontWeight: 'bold', fontFamily: 'ui-monospace,"SF Mono",Consolas,monospace', textAlign: 'center', textVerticalAlign: 'bottom' }, left: 'center', top: -8 },
          { type: 'text', style: { text: '总案件', fill: '#5b6b80', fontSize: 11, textAlign: 'center', textVerticalAlign: 'top' }, left: 'center', top: 8 },
        ],
      }],
    }));

    // 辖区排名横向柱状图
    var distChart = echarts.init(document.getElementById('chart-district'));
    charts.push(distChart);
    var dNames = DISTRICTS.map(function(d) { return d.name; }).reverse();
    var dValues = DISTRICTS.map(function(d) { return d.value; }).reverse();
    distChart.setOption(Object.assign({}, echartBaseOption(), {
      grid: { left: 100, right: 24, top: 8, bottom: 8 },
      xAxis: Object.assign({ type: 'value', show: false }, echartAxisDefaults()),
      yAxis: Object.assign({ type: 'category', data: dNames, inverse: false }, echartAxisDefaults(), { axisLine: { show: false } }),
      series: [{
        type: 'bar', data: dValues,
        barWidth: 14, itemStyle: { color: cyanBarGradient(), borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11 },
        animationDuration: 800,
      }],
    }));

    // 年龄分布环形图
    var ageChart = echarts.init(document.getElementById('chart-age'));
    charts.push(ageChart);
    var ageTotal = AGE_DIST.reduce(function(s, d) { return s + d.value; }, 0);
    ageChart.setOption(Object.assign({}, echartBaseOption(), {
      tooltip: Object.assign({}, echartBaseOption().tooltip, { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' }),
      series: [{
        type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'],
        data: AGE_DIST, label: { show: true, color: '#94a3b8', fontSize: 11, formatter: '{b}\n{d}%' },
        labelLine: { lineStyle: { color: 'rgba(148,163,184,0.3)' } },
        emphasis: { scaleSize: 6 },
        animationDuration: 800,
      }],
      graphic: [{
        type: 'group', left: 'center', top: '50%',
        children: [
          { type: 'text', style: { text: formatNum(ageTotal), fill: '#e6edf7', fontSize: 22, fontWeight: 'bold', fontFamily: 'ui-monospace,"SF Mono",Consolas,monospace', textAlign: 'center', textVerticalAlign: 'bottom' }, left: 'center', top: -8 },
          { type: 'text', style: { text: '总人数', fill: '#5b6b80', fontSize: 11, textAlign: 'center', textVerticalAlign: 'top' }, left: 'center', top: 8 },
        ],
      }],
    }));

    // Sparklines (mini 迷你折线)
    for (var i = 0; i < 4; i++) {
      var sparkEl = document.getElementById('spark-' + i);
      if (!sparkEl) continue;
      var sparkChart = echarts.init(sparkEl);
      charts.push(sparkChart);
      var sparkData = [4,6,5,7,8,6,7,5,8,9,7,8].map(function(v) { return v + Math.floor(Math.random()*3); });
      sparkChart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 0, right: 0, top: 2, bottom: 2 },
        xAxis: { type: 'category', show: false, data: sparkData },
        yAxis: { type: 'value', show: false },
        series: [{ type: 'line', data: sparkData, smooth: true, symbol: 'none',
          lineStyle: { color: KPI[i].color, width: 1.5, opacity: 0.6 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[
            { offset: 0, color: KPI[i].color.replace(')', ',0.15)').replace('rgb','rgba') },
            { offset: 1, color: 'transparent' },
          ])},
        }],
      });
    }

    // 预警自动刷新
    intervals.push(setInterval(function() {
      var list = document.getElementById('alert-list');
      if (list) list.innerHTML = generateAlerts();
    }, 30000));

    // 首次 resize 确保尺寸正确
    setTimeout(function() {
      charts.forEach(function(c) { if (!c.isDisposed()) c.resize(); });
    }, 100);

    // 图表 resize
    var resizeHandler = debounce(function() {
      charts.forEach(function(c) { if (!c.isDisposed()) c.resize(); });
    }, 200);
    window.addEventListener('resize', resizeHandler);
    intervals.push({ clear: function() { window.removeEventListener('resize', resizeHandler); } });
  }

  function destroy() {
    charts.forEach(function(c) { if (!c.isDisposed()) c.dispose(); });
    charts = [];
    intervals.forEach(function(i) { if (typeof i === 'number') clearInterval(i); else if (i && i.clear) i.clear(); });
    intervals = [];
  }

  return { render: render, init: init, destroy: destroy };
})();

PageManager.register('dashboard', DashboardPage);
