(function () {
  let chart = null;
  let currentDepth = 1;
  let graphData = { nodes: [], edges: [] };
  let currentRoot = null;
  let searchResults = [];

  const typeLabels = {
    person: '人员',
    case: '案件',
    school: '学校',
    guardian: '监护人',
    location: '地点',
    organization: '机构'
  };

  function initChart() {
    chart = echarts.init(document.getElementById('graphCanvas'));
    chart.on('click', function (params) {
      if (params.dataType === 'node') {
        showNodeDetail(params.data);
      }
    });
    chart.on('dblclick', function (params) {
      if (params.dataType !== 'node' || !params.data.properties) return;
      if (params.data.properties.zjhm) {
        loadGraph(params.data.properties.zjhm);
      } else if (params.data.nodeType === 'case' && params.data.properties.ajbh) {
        loadCaseGraph(params.data.properties.ajbh);
      }
    });
    window.addEventListener('resize', () => chart && chart.resize());
    document.addEventListener('fullscreenchange', updateFullscreenButton);
  }

  function renderGraph(data) {
    graphData = data;
    document.getElementById('placeholder').style.display = 'none';

    const categories = [
      { name: '人员', itemStyle: { color: '#3b82f6' } },
      { name: '案件', itemStyle: { color: '#7c3aed' } },
      { name: '学校', itemStyle: { color: '#f59e0b' } },
      { name: '监护人', itemStyle: { color: '#10b981' } },
      { name: '地点', itemStyle: { color: '#14b8a6' } },
      { name: '机构', itemStyle: { color: '#a855f7' } }
    ];
    const categoryMap = { person: 0, case: 1, school: 2, guardian: 3, location: 4, organization: 5 };

    const nodes = (data.nodes || []).map(n => ({
      id: n.id,
      name: n.label,
      symbolSize: (n.style && n.style.size) || 30,
      category: Object.prototype.hasOwnProperty.call(categoryMap, n.type) ? categoryMap[n.type] : 0,
      itemStyle: { color: (n.style && n.style.fill) || '#3b82f6' },
      properties: n.properties || {},
      nodeType: n.type
    }));

    const edges = (data.edges || []).map(e => ({
      source: e.source,
      target: e.target,
      edgeType: e.type,
      properties: e.properties || {},
      label: { show: true, formatter: e.label || '', fontSize: 10, color: '#94a3b8' },
      lineStyle: {
        color: (e.style && e.style.stroke) || '#475569',
        width: (e.style && e.style.lineWidth) || 1.5,
        curveness: 0.1,
        type: (e.style && e.style.lineDash) ? 'dashed' : 'solid'
      }
    }));

    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: function (params) {
          if (params.dataType === 'node') {
            const p = params.data.properties || {};
            let tip = `<b>${escapeHtml(params.data.name)}</b><br/>类型: ${typeLabels[params.data.nodeType] || params.data.nodeType || ''}`;
            if (p.zjhm) tip += `<br/>证件号: ${escapeHtml(p.zjhm)}`;
            if (p.risk_score != null) tip += `<br/>风险分: ${p.risk_score}`;
            if (p.ajbh) tip += `<br/>案件编号: ${escapeHtml(p.ajbh)}`;
            if (p.name) tip += `<br/>名称: ${escapeHtml(p.name)}`;
            return tip;
          }
          return params.data.edgeType || '';
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

  function getSelectedRelations() {
    const select = document.getElementById('relationFilter');
    if (!select) return '';
    const values = Array.from(select.selectedOptions).map(option => option.value);
    return values.length ? values.join(',') : 'none';
  }

  function getTimeRange() {
    const select = document.getElementById('timeRange');
    return select ? select.value : '';
  }

  async function loadGraph(zjhm) {
    showLoading('加载关系图谱...');
    try {
      currentRoot = { type: 'person', id: zjhm };
      const params = new URLSearchParams();
      params.set('depth', currentDepth);
      params.set('relations', getSelectedRelations());
      const timeRange = getTimeRange();
      if (timeRange) params.set('time_range', timeRange);
      const res = await fetch(`/api/graph/person/${encodeURIComponent(zjhm)}?${params.toString()}`);
      if (!res.ok) {
        showError('未找到该人员的关系数据');
        return;
      }
      const data = await res.json();
      if (!data.nodes || !data.nodes.length) {
        showError('未找到该人员的关系数据');
        return;
      }
      renderGraph(data);
    } catch (e) {
      showError('加载数据失败，请稍后重试');
    } finally {
      hideLoading();
    }
  }

  async function loadCaseGraph(ajbh) {
    showLoading('加载案件图谱...');
    try {
      currentRoot = { type: 'case', id: ajbh };
      const res = await fetch(`/api/graph/case/${encodeURIComponent(ajbh)}?depth=${currentDepth}`);
      if (!res.ok) {
        showError('未找到该案件的关系数据');
        return;
      }
      const data = await res.json();
      if (!data.nodes || !data.nodes.length) {
        showError('未找到该案件的关系数据');
        return;
      }
      renderGraph(data);
    } catch (e) {
      showError('加载数据失败，请稍后重试');
    } finally {
      hideLoading();
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

    showLoading('搜索中...');
    try {
      const res = await fetch(`/api/graph/search?keyword=${encodeURIComponent(keyword)}`);
      const data = await res.json();
      const results = data.results || [];
      if (!results.length) {
        showError('未找到相关结果');
        return false;
      }
      if (results.length === 1 && results[0].type === 'person') {
        await loadGraph(results[0].id);
      } else if (results.length === 1 && results[0].type === 'case') {
        await loadCaseGraph(results[0].id);
      } else {
        showSearchResults(results);
      }
    } catch (e) {
      showError('搜索失败: ' + e.message);
    } finally {
      hideLoading();
    }
    return false;
  }

  function showSearchResults(results) {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebarContent');
    sidebar.classList.remove('sidebar-hidden');
    searchResults = results;

    content.innerHTML = `
      <div class="text-xs text-slate-400 mb-3">找到 ${results.length} 条结果</div>
      ${results.map((r, index) => `
        <div class="py-2 border-b border-slate-700 cursor-pointer hover:bg-slate-700/50 px-2 rounded"
             onclick="window._graphSelectResult(${index})">
          <div class="text-sm text-slate-200">${escapeHtml(r.label || r.id)}</div>
          <div class="text-xs text-slate-500">${typeLabels[r.type] || r.type || ''} · ${escapeHtml(r.id)}</div>
        </div>
      `).join('')}
    `;
  }

  window._graphSelectResult = function (index) {
    const result = searchResults[index];
    if (!result) return;
    if (result.type === 'person') {
      loadGraph(result.id);
    } else if (result.type === 'case') {
      loadCaseGraph(result.id);
    } else if (result.type === 'location') {
      showLocationResult(result);
    }
  };

  function showLocationResult(result) {
    currentRoot = null;
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebarContent');
    sidebar.classList.remove('sidebar-hidden');
    content.innerHTML = `
      <div class="text-xs text-slate-400 mb-1">地点</div>
      <div class="text-lg font-bold text-white mb-3">${escapeHtml(result.label || result.id)}</div>
      <div class="text-sm text-slate-400">该节点仅用于定位展示，请选择人员或案件加载关系图。</div>
    `;
  }

  function showNodeDetail(nodeData) {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebarContent');
    sidebar.classList.remove('sidebar-hidden');

    const p = nodeData.properties || {};

    let html = `<div class="text-xs text-slate-400 mb-1">${typeLabels[nodeData.nodeType] || ''}</div>`;
    html += `<div class="text-lg font-bold text-white mb-3">${escapeHtml(nodeData.name || '')}</div>`;

    if (nodeData.nodeType === 'person') {
      html += `<div class="space-y-2 text-sm">`;
      if (p.zjhm) html += `<div><span class="text-slate-400">证件号:</span> <span class="text-slate-200">${escapeHtml(p.zjhm)}</span></div>`;
      if (p.risk_score != null) html += `<div><span class="text-slate-400">风险评分:</span> <span class="text-slate-200">${p.risk_score}</span></div>`;
      if (p.risk_level) html += `<div><span class="text-slate-400">风险等级:</span> <span class="text-slate-200">${riskLabel(p.risk_level)}</span></div>`;
      html += `</div>`;
      html += `<div class="mt-4 flex gap-2">`;
      html += `<a href="/profile/${encodeURIComponent(p.zjhm || '')}" class="text-xs bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">查看画像</a>`;
      html += `<button data-action="expand" data-node-id="${escapeAttr(nodeData.id)}" data-node-type="${escapeAttr(nodeData.nodeType)}" class="text-xs bg-slate-600 text-white px-3 py-1.5 rounded hover:bg-slate-500">展开关系</button>`;
      html += `</div>`;
    } else if (nodeData.nodeType === 'case') {
      html += `<div class="space-y-2 text-sm">`;
      if (p.ajbh) html += `<div><span class="text-slate-400">案件编号:</span> <span class="text-slate-200">${escapeHtml(p.ajbh)}</span></div>`;
      if (p.ajmc) html += `<div><span class="text-slate-400">案件名称:</span> <span class="text-slate-200">${escapeHtml(p.ajmc)}</span></div>`;
      if (p.ay) html += `<div><span class="text-slate-400">案由:</span> <span class="text-slate-200">${escapeHtml(p.ay)}</span></div>`;
      if (p.fasj) html += `<div><span class="text-slate-400">发案时间:</span> <span class="text-slate-200">${escapeHtml(p.fasj)}</span></div>`;
      html += `</div>`;
    } else if (nodeData.nodeType === 'guardian') {
      html += `<div class="space-y-2 text-sm">`;
      if (p.xm) html += `<div><span class="text-slate-400">姓名:</span> <span class="text-slate-200">${escapeHtml(p.xm)}</span></div>`;
      if (p.lxdh) html += `<div><span class="text-slate-400">联系电话:</span> <span class="text-slate-200">${escapeHtml(p.lxdh)}</span></div>`;
      html += `</div>`;
    } else {
      html += `<div class="space-y-2 text-sm">`;
      Object.keys(p).slice(0, 8).forEach(key => {
        if (p[key] !== null && p[key] !== undefined) {
          html += `<div><span class="text-slate-400">${escapeHtml(key)}:</span> <span class="text-slate-200">${escapeHtml(String(p[key]))}</span></div>`;
        }
      });
      html += `</div>`;
    }

    content.innerHTML = html;
    const expandButton = content.querySelector('[data-action="expand"]');
    if (expandButton) {
      expandButton.addEventListener('click', () => {
        window._graphExpandNode(expandButton.dataset.nodeId, expandButton.dataset.nodeType);
      });
    }
  }

  window._graphExpandNode = async function (nodeId, nodeType) {
    if (!nodeId || !nodeType) return;
    showLoading('展开关系...');
    try {
      const res = await fetch('/api/graph/expand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, node_type: nodeType, direction: 'both' })
      });
      if (!res.ok) {
        showError('展开关系失败');
        return;
      }
      mergeGraph(await res.json());
    } catch (e) {
      showError('展开关系失败: ' + e.message);
    } finally {
      hideLoading();
    }
  };

  function mergeGraph(increment) {
    const nodeMap = new Map((graphData.nodes || []).map(node => [node.id, node]));
    const edgeMap = new Map((graphData.edges || []).map(edge => [`${edge.source}|${edge.target}|${edge.type || ''}`, edge]));
    (increment.nodes || []).forEach(node => nodeMap.set(node.id, node));
    (increment.edges || []).forEach(edge => edgeMap.set(`${edge.source}|${edge.target}|${edge.type || ''}`, edge));
    renderGraph({ nodes: Array.from(nodeMap.values()), edges: Array.from(edgeMap.values()) });
  }

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
    reloadCurrentGraph();
  }

  function reloadCurrentGraph() {
    if (currentRoot && currentRoot.type === 'person') {
      loadGraph(currentRoot.id);
    } else if (currentRoot && currentRoot.type === 'case') {
      loadCaseGraph(currentRoot.id);
    }
  }

  async function toggleFullscreen() {
    const target = document.getElementById('graphCanvas');
    if (!target) return;
    try {
      if (!document.fullscreenElement) {
        if (target.requestFullscreen) {
          await target.requestFullscreen();
        }
      } else if (document.exitFullscreen) {
        await document.exitFullscreen();
      }
    } catch (e) {
      showError('全屏切换失败: ' + e.message);
    } finally {
      updateFullscreenButton();
      setTimeout(() => chart && chart.resize(), 80);
    }
  }

  function updateFullscreenButton() {
    const btn = document.getElementById('fullscreenBtn');
    if (btn) {
      btn.textContent = document.fullscreenElement ? '退出全屏' : '全屏';
    }
    setTimeout(() => chart && chart.resize(), 80);
  }

  function riskLabel(level) {
    const map = { extreme: '极高风险', high: '高风险', medium: '中风险', low: '低风险', normal: '正常' };
    return map[level] || level || '';
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, '&#96;');
  }

  window.handleSearch = handleSearch;
  window.setDepth = setDepth;
  window.toggleFullscreen = toggleFullscreen;
  window.reloadCurrentGraph = reloadCurrentGraph;
  window.closeSidebar = closeSidebar;
  window.loadCaseGraph = loadCaseGraph;

  initChart();

  const params = new URLSearchParams(window.location.search);
  const zjhm = params.get('zjhm');
  if (zjhm) {
    document.getElementById('searchInput').value = zjhm;
    loadGraph(zjhm);
  }
})();
