// ============================================================
// graph.js - 关系图谱 Graph
// ============================================================

var GraphPage = (function() {
  var charts = [];
  var graphChart = null;
  var drawerOpen = false;

  // ---- 演示数据 ----
  var NODES = [
    { id: 'p1', name: '张某辉', type: 'person', risk: 'high', score: 78 },
    { id: 'p2', name: '李某阳', type: 'person', risk: 'high', score: 65 },
    { id: 'p3', name: '王某飞', type: 'person', risk: 'medium', score: 45 },
    { id: 'p4', name: '赵某杰', type: 'highrisk', risk: 'extreme', score: 92 },
    { id: 'p5', name: '陈某龙', type: 'person', risk: 'high', score: 70 },
    { id: 'p6', name: '刘某伟', type: 'person', risk: 'medium', score: 40 },
    { id: 'p7', name: '周某浩', type: 'person', risk: 'low', score: 28 },
    { id: 'g1', name: '张某国', type: 'guardian', relation: '父亲', phone: '138****5672' },
    { id: 'g2', name: '李某华', type: 'guardian', relation: '母亲', phone: '139****8901' },
    { id: 's1', name: '西安市第XX中学', type: 'school' },
    { id: 's2', name: '西安市第YY中学', type: 'school' },
    { id: 'c1', name: '新城区系列盗窃案', type: 'case', time: '2026-03-15', reason: '盗窃' },
    { id: 'c2', name: '碑林区电动车盗窃案', type: 'case', time: '2025-11-22', reason: '盗窃' },
    { id: 'c3', name: '雁塔区商场扒窃案', type: 'case', time: '2025-08-07', reason: '盗窃' },
    { id: 'c4', name: '未央区敲诈勒索案', type: 'case', time: '2025-04-12', reason: '敲诈勒索' },
  ];

  var LINKS = [
    { source: 'p1', target: 'c1', label: '涉嫌', type: 'suspect' },
    { source: 'p1', target: 'c2', label: '涉嫌', type: 'suspect' },
    { source: 'p1', target: 'c3', label: '涉嫌', type: 'suspect' },
    { source: 'p1', target: 'c4', label: '涉嫌', type: 'suspect' },
    { source: 'p2', target: 'c1', label: '共犯', type: 'accomplice' },
    { source: 'p2', target: 'c2', label: '共犯', type: 'accomplice' },
    { source: 'p4', target: 'c1', label: '共犯', type: 'accomplice' },
    { source: 'p4', target: 'c4', label: '涉嫌', type: 'suspect' },
    { source: 'p3', target: 'c3', label: '涉嫌', type: 'suspect' },
    { source: 'p5', target: 'c4', label: '涉嫌', type: 'suspect' },
    { source: 'p6', target: 'c2', label: '涉嫌', type: 'suspect' },
    { source: 'p1', target: 'p2', label: '共犯', type: 'accomplice' },
    { source: 'p1', target: 'p4', label: '共犯', type: 'accomplice' },
    { source: 'p1', target: 'g1', label: '监护', type: 'guardian' },
    { source: 'p2', target: 'g2', label: '监护', type: 'guardian' },
    { source: 'p1', target: 's1', label: '就读', type: 'school' },
    { source: 'p2', target: 's1', label: '就读', type: 'school' },
    { source: 'p3', target: 's2', label: '就读', type: 'school' },
    { source: 'p7', target: 's2', label: '就读', type: 'school' },
    { source: 'p5', target: 's1', label: '就读', type: 'school' },
  ];

  var NODE_TYPE_MAP = {
    person:   { color: '#38bdf8', symbol: 'circle', size: 36, label: '人员' },
    highrisk: { color: '#ef4444', symbol: 'circle', size: 44, label: '高风险人员' },
    case:     { color: '#a855f7', symbol: 'roundRect', size: 32, label: '案件' },
    school:   { color: '#f59e0b', symbol: 'triangle', size: 32, label: '学校' },
    guardian: { color: '#10b981', symbol: 'diamond', size: 30, label: '监护人' },
  };

  // ---- 渲染 ----
  function render(container) {
    container.innerHTML =
      '<div class="graph-layout">' +
        // 主画布区
        '<div class="graph-main">' +
          // 搜索栏
          '<div class="graph-toolbar">' +
            '<div class="graph-search-wrap">' +
              icon('search', 18, 'graph-search-icon') +
              '<input class="graph-search-input" id="graph-search" placeholder="输入姓名 / 身份证号 / 案件编号…" />' +
              '<button class="btn-primary graph-search-btn" id="graph-search-btn">' + icon('search', 16) + ' 搜索</button>' +
            '</div>' +
            '<div class="graph-depth-toggle">' +
              '<button class="depth-btn active" data-depth="1">1层</button>' +
              '<button class="depth-btn" data-depth="2">2层</button>' +
            '</div>' +
          '</div>' +
          // 图表容器
          '<div id="graph-canvas" class="graph-canvas"></div>' +
          // 空状态
          '<div id="graph-empty" class="graph-empty">' +
            '<div class="graph-empty-icon">' + icon('network', 64) + '</div>' +
            '<div class="graph-empty-title">搜索姓名或身份证号，展开关系图谱</div>' +
            '<div class="graph-empty-sub">支持按人员、案件、学校等维度探索关联关系</div>' +
          '</div>' +
          // 图例
          '<div class="graph-legend" id="graph-legend" style="display:none">' +
            Object.keys(NODE_TYPE_MAP).map(function(k) {
              var t = NODE_TYPE_MAP[k];
              return '<span class="legend-item"><span class="legend-dot" style="background:' + t.color + '"></span>' + t.label + '</span>';
            }).join('') +
          '</div>' +
        '</div>' +
        // 右侧详情抽屉
        '<div class="graph-drawer" id="graph-drawer">' +
          '<div class="drawer-header">' +
            '<span class="drawer-title">节点详情</span>' +
            '<button class="drawer-close" id="drawer-close">' + icon('x', 18) + '</button>' +
          '</div>' +
          '<div class="drawer-body" id="drawer-body"></div>' +
        '</div>' +
      '</div>';
  }

  function buildGraphOption() {
    var eNodes = NODES.map(function(n) {
      var t = NODE_TYPE_MAP[n.type] || NODE_TYPE_MAP.person;
      var isHighRisk = n.type === 'highrisk';
      return {
        id: n.id, name: n.name, symbolSize: t.size, symbol: t.symbol,
        category: n.type,
        itemStyle: {
          color: t.color, borderColor: t.color, borderWidth: 2,
          shadowColor: t.color + '60', shadowBlur: isHighRisk ? 20 : 10,
        },
        label: { show: true, color: '#e6edf7', fontSize: 11, position: 'bottom', distance: 5 },
        emphasis: {
          itemStyle: { shadowBlur: 25, shadowColor: t.color + '80', borderWidth: 3 },
          label: { fontSize: 13, fontWeight: 'bold' },
        },
        // Store original data for drawer
        _data: n,
      };
    });

    var eLinks = LINKS.map(function(l) {
      var isAccomplice = l.type === 'accomplice';
      return {
        source: l.id || l.source, target: l.target,
        label: { show: true, formatter: l.label, color: '#5b6b80', fontSize: 9, distance: 5 },
        lineStyle: {
          color: isAccomplice ? 'rgba(239,68,68,0.6)' : 'rgba(56,189,248,0.25)',
          width: isAccomplice ? 2.5 : 1.2,
          curveness: 0.1,
        },
        emphasis: {
          lineStyle: { color: isAccomplice ? '#ef4444' : '#38bdf8', width: isAccomplice ? 3 : 2 },
        },
        _data: l,
      };
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        show: false,
      },
      animationDuration: 800,
      animationEasingUpdate: 'quinticInOut',
      series: [{
        type: 'graph', layout: 'force', roam: true, draggable: true,
        data: eNodes, links: eLinks,
        force: {
          repulsion: 320, edgeLength: [80, 180], gravity: 0.08, layoutAnimation: true,
        },
        emphasis: { focus: 'adjacency', blurScope: 'global' },
        scaleLimit: { min: 0.4, max: 3 },
        lineStyle: { opacity: 1 },
      }],
    };
  }

  function showDrawer(nodeData) {
    var drawer = document.getElementById('graph-drawer');
    var body = document.getElementById('drawer-body');
    var n = nodeData;
    var html = '';

    if (n.type === 'person' || n.type === 'highrisk') {
      html = '<div class="drawer-section">' +
        '<div class="drawer-person-name">' + n.name + ' ' + riskBadge(n.risk) + '</div>' +
        '<div class="drawer-info-row"><span class="info-label">风险评分</span><span class="glow-number" style="color:' + RISK_CONFIG[n.risk].color + '">' + n.score + '</span></div>' +
        '<div class="drawer-info-row"><span class="info-label">证件号</span><span>610102****</span></div>' +
        '<div class="drawer-actions">' +
          '<button class="btn-primary btn-sm" onclick="PageManager.switchTo(\'profile\')">' + icon('eye',14) + ' 查看画像</button>' +
          '<button class="btn-outline btn-sm" onclick="void(0)">' + icon('network',14) + ' 展开关系</button>' +
        '</div>' +
      '</div>';
    } else if (n.type === 'case') {
      html = '<div class="drawer-section">' +
        '<div class="drawer-case-name">' + icon('folder',18) + ' ' + n.name + '</div>' +
        '<div class="drawer-info-row"><span class="info-label">案由</span><span>' + (n.reason||'--') + '</span></div>' +
        '<div class="drawer-info-row"><span class="info-label">发案时间</span><span>' + (n.time||'--') + '</span></div>' +
      '</div>';
    } else if (n.type === 'guardian') {
      html = '<div class="drawer-section">' +
        '<div class="drawer-person-name">' + icon('users',18) + ' ' + n.name + '</div>' +
        '<div class="drawer-info-row"><span class="info-label">关系</span><span>' + (n.relation||'--') + '</span></div>' +
        '<div class="drawer-info-row"><span class="info-label">联系电话</span><span>' + (n.phone||'--') + '</span></div>' +
      '</div>';
    } else if (n.type === 'school') {
      html = '<div class="drawer-section">' +
        '<div class="drawer-case-name">' + icon('building',18) + ' ' + n.name + '</div>' +
      '</div>';
    }

    body.innerHTML = html;
    drawer.classList.add('open');
    drawerOpen = true;
  }

  function hideDrawer() {
    document.getElementById('graph-drawer').classList.remove('open');
    drawerOpen = false;
  }

  function showGraph() {
    document.getElementById('graph-empty').style.display = 'none';
    document.getElementById('graph-legend').style.display = 'flex';
    var canvas = document.getElementById('graph-canvas');
    canvas.style.display = 'block';

    if (!graphChart || graphChart.isDisposed()) {
      graphChart = echarts.init(canvas);
      charts.push(graphChart);
    }
    graphChart.setOption(buildGraphOption(), true);
    graphChart.resize();

    // 点击节点 → 打开抽屉
    graphChart.off('click');
    graphChart.on('click', function(params) {
      if (params.dataType === 'node' && params.data._data) {
        showDrawer(params.data._data);
      }
    });
  }

  // ---- 初始化 ----
  function init() {
    // 搜索
    var searchBtn = document.getElementById('graph-search-btn');
    var searchInput = document.getElementById('graph-search');

    function doSearch() {
      var val = searchInput.value.trim();
      if (val) {
        showGraph();
      }
    }

    if (searchBtn) searchBtn.addEventListener('click', doSearch);
    if (searchInput) searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') doSearch();
    });

    // 深度切换
    delegate(document.querySelector('.graph-depth-toggle'), '.depth-btn', 'click', function(e, btn) {
      document.querySelectorAll('.depth-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      if (graphChart && !graphChart.isDisposed()) showGraph();
    });

    // 关闭抽屉
    var closeBtn = document.getElementById('drawer-close');
    if (closeBtn) closeBtn.addEventListener('click', hideDrawer);

    // Resize
    var resizeHandler = debounce(function() {
      if (graphChart && !graphChart.isDisposed()) graphChart.resize();
    }, 200);
    window.addEventListener('resize', resizeHandler);
  }

  function destroy() {
    charts.forEach(function(c) { if (!c.isDisposed()) c.dispose(); });
    charts = [];
    graphChart = null;
    drawerOpen = false;
  }

  return { render: render, init: init, destroy: destroy };
})();

PageManager.register('graph', GraphPage);
