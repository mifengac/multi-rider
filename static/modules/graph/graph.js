(function () {
  let chart = null;
  let currentDepth = 1;
  let graphData = { nodes: [], edges: [] };

  function initChart() {
    chart = echarts.init(document.getElementById('graphCanvas'));
    chart.on('click', function (params) {
      if (params.dataType === 'node') {
        showNodeDetail(params.data);
      }
    });
    chart.on('dblclick', function (params) {
      if (params.dataType === 'node' && params.data.properties && params.data.properties.zjhm) {
        loadGraph(params.data.properties.zjhm);
      }
    });
    window.addEventListener('resize', () => chart && chart.resize());
  }

  function renderGraph(data) {
    graphData = data;
    document.getElementById('placeholder').style.display = 'none';

    const categories = [
      { name: '人员', itemStyle: { color: '#3b82f6' } },
      { name: '案件', itemStyle: { color: '#7c3aed' } },
      { name: '学校', itemStyle: { color: '#f59e0b' } },
      { name: '监护人', itemStyle: { color: '#10b981' } }
    ];
    const categoryMap = { person: 0, case: 1, school: 2, guardian: 3 };

    const nodes = data.nodes.map(n => ({
      id: n.id,
      name: n.label,
      symbolSize: (n.style && n.style.size) || 30,
      category: categoryMap[n.type] || 0,
      itemStyle: { color: (n.style && n.style.fill) || '#3b82f6' },
      properties: n.properties || {},
      nodeType: n.type
    }));

    const edges = data.edges.map(e => ({
      source: e.source,
      target: e.target,
      label: { show: true, formatter: e.label || '', fontSize: 10, color: '#94a3b8' },
      lineStyle: {
        color: (e.style && e.style.stroke) || '#475569',
        width: (e.style && e.style.lineWidth) || 1.5,
        curveness: 0.1
      }
    }));

    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: function (params) {
          if (params.dataType === 'node') {
            const p = params.data.properties || {};
            let tip = `<b>${params.data.name}</b><br/>类型: ${params.data.nodeType || ''}`;
            if (p.zjhm) tip += `<br/>证件号: ${p.zjhm}`;
            if (p.risk_score != null) tip += `<br/>风险分: ${p.risk_score}`;
            if (p.ajbh) tip += `<br/>案件编号: ${p.ajbh}`;
            return tip;
          }
          return params.data.label ? params.data.label.formatter : '';
        }
      },
      legend: { show: false },
      animationDuration: 800,
      animationEasingUpdate: 'quinticInOut',
      series: [{
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: edges,
        categories: categories,
        roam: true,
        draggable: true,
        force: {
          repulsion: 300,
          edgeLength: [80, 200],
          gravity: 0.1
        },
        label: {
          show: true,
          position: 'bottom',
          fontSize: 11,
          color: '#e2e8f0'
        },
        edgeLabel: {
          fontSize: 9
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 }
        }
      }]
    }, true);
  }

  async function loadGraph(zjhm) {
    try {
      const res = await fetch(`/api/graph/person/${encodeURIComponent(zjhm)}?depth=${currentDepth}`);
      if (!res.ok) {
        alert('未找到该人员的关系数据');
        return;
      }
      const data = await res.json();
      if (!data.nodes || !data.nodes.length) {
        alert('未找到该人员的关系数据');
        return;
      }
      renderGraph(data);
    } catch (e) {
      alert('加载失败: ' + e.message);
    }
  }

  async function handleSearch(event) {
    event.preventDefault();
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) return false;

    if (/^\d{15,18}[xX]?$/.test(keyword)) {
      loadGraph(keyword);
      return false;
    }

    try {
      const res = await fetch(`/api/graph/search?keyword=${encodeURIComponent(keyword)}`);
      const data = await res.json();
      const results = data.results || [];
      if (!results.length) {
        alert('未找到相关结果');
        return false;
      }
      if (results.length === 1 && results[0].type === 'person') {
        loadGraph(results[0].id);
      } else {
        showSearchResults(results);
      }
    } catch (e) {
      alert('搜索失败: ' + e.message);
    }
    return false;
  }

  function showSearchResults(results) {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebarContent');
    sidebar.classList.remove('sidebar-hidden');

    content.innerHTML = `
      <div class="text-xs text-slate-400 mb-3">找到 ${results.length} 条结果</div>
      ${results.map(r => `
        <div class="py-2 border-b border-slate-700 cursor-pointer hover:bg-slate-700/50 px-2 rounded"
             onclick="window._graphSelectResult('${r.id}', '${r.type}')">
          <div class="text-sm text-slate-200">${r.label || r.id}</div>
          <div class="text-xs text-slate-500">${r.type === 'person' ? '人员' : '案件'} · ${r.id}</div>
        </div>
      `).join('')}
    `;
  }

  window._graphSelectResult = function (id, type) {
    if (type === 'person') {
      loadGraph(id);
    }
  };

  function showNodeDetail(nodeData) {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebarContent');
    sidebar.classList.remove('sidebar-hidden');

    const p = nodeData.properties || {};
    const typeLabels = { person: '人员', case: '案件', school: '学校', guardian: '监护人' };

    let html = `<div class="text-xs text-slate-400 mb-1">${typeLabels[nodeData.nodeType] || ''}</div>`;
    html += `<div class="text-lg font-bold text-white mb-3">${nodeData.name}</div>`;

    if (nodeData.nodeType === 'person') {
      html += `<div class="space-y-2 text-sm">`;
      if (p.zjhm) html += `<div><span class="text-slate-400">证件号:</span> <span class="text-slate-200">${p.zjhm}</span></div>`;
      if (p.risk_score != null) html += `<div><span class="text-slate-400">风险评分:</span> <span class="text-slate-200">${p.risk_score}</span></div>`;
      if (p.risk_level) html += `<div><span class="text-slate-400">风险等级:</span> <span class="text-slate-200">${riskLabel(p.risk_level)}</span></div>`;
      html += `</div>`;
      html += `<div class="mt-4 flex gap-2">`;
      html += `<a href="/profile/${p.zjhm}" class="text-xs bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">查看画像</a>`;
      html += `<button onclick="window._graphExpandNode('${p.zjhm}')" class="text-xs bg-slate-600 text-white px-3 py-1.5 rounded hover:bg-slate-500">展开关系</button>`;
      html += `</div>`;
    } else if (nodeData.nodeType === 'case') {
      html += `<div class="space-y-2 text-sm">`;
      if (p.ajbh) html += `<div><span class="text-slate-400">案件编号:</span> <span class="text-slate-200">${p.ajbh}</span></div>`;
      if (p.ajmc) html += `<div><span class="text-slate-400">案件名称:</span> <span class="text-slate-200">${p.ajmc}</span></div>`;
      if (p.ay) html += `<div><span class="text-slate-400">案由:</span> <span class="text-slate-200">${p.ay}</span></div>`;
      if (p.fasj) html += `<div><span class="text-slate-400">发案时间:</span> <span class="text-slate-200">${p.fasj}</span></div>`;
      html += `</div>`;
    } else if (nodeData.nodeType === 'guardian') {
      html += `<div class="space-y-2 text-sm">`;
      if (p.xm) html += `<div><span class="text-slate-400">姓名:</span> <span class="text-slate-200">${p.xm}</span></div>`;
      if (p.lxdh) html += `<div><span class="text-slate-400">联系电话:</span> <span class="text-slate-200">${p.lxdh}</span></div>`;
      html += `</div>`;
    } else if (nodeData.nodeType === 'school') {
      html += `<div class="text-sm"><span class="text-slate-400">学校名称:</span> <span class="text-slate-200">${p.name || ''}</span></div>`;
    }

    content.innerHTML = html;
  }

  window._graphExpandNode = function (zjhm) {
    loadGraph(zjhm);
  };

  function closeSidebar() {
    document.getElementById('sidebar').classList.add('sidebar-hidden');
  }

  function setDepth(d) {
    currentDepth = d;
    document.querySelectorAll('.control-btn').forEach(btn => {
      if (btn.textContent.includes(d + '层')) {
        btn.classList.add('active');
      } else if (btn.textContent.match(/\d层/)) {
        btn.classList.remove('active');
      }
    });
    const input = document.getElementById('searchInput');
    if (input.value.trim()) {
      handleSearch(new Event('submit'));
    }
  }

  function riskLabel(level) {
    const map = { extreme: '极高风险', high: '高风险', medium: '中风险', low: '低风险', normal: '正常' };
    return map[level] || level || '';
  }

  // Expose globals for inline handlers
  window.handleSearch = handleSearch;
  window.setDepth = setDepth;
  window.closeSidebar = closeSidebar;

  // Init
  initChart();

  // Auto-load if zjhm is in URL
  const params = new URLSearchParams(window.location.search);
  const zjhm = params.get('zjhm');
  if (zjhm) {
    document.getElementById('searchInput').value = zjhm;
    loadGraph(zjhm);
  }
})();
