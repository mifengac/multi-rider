(function () {
  const API = '/api/dashboard';
  let alertsCache = [];
  let alertPollTimer = null;
  let alertEventSource = null;
  const rankingState = {
    level: 'ssfj',
    parentCode: '',
    parentLabel: ''
  };

  function updateClock() {
    const el = document.getElementById('clock');
    if (el) el.textContent = new Date().toLocaleString('zh-CN', { hour12: false });
  }
  setInterval(updateClock, 1000);
  updateClock();

  async function fetchJSON(url) {
    try {
      const res = await fetch(url);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.message || data.error || `HTTP ${res.status}`);
      }
      return data;
    } catch (e) {
      showError('加载数据失败，请稍后重试');
      return {};
    }
  }

  function bindChartResize(chart) {
    if (chart.__resizeBound) {
      requestAnimationFrame(() => chart.resize());
      return;
    }
    const resize = () => chart.resize();
    chart.__resizeBound = true;
    window.addEventListener('resize', resize);
    requestAnimationFrame(resize);
  }

  function updateRankingScope() {
    const scope = document.getElementById('rankingScope');
    const backButton = document.getElementById('rankingBackButton');
    if (scope) {
      scope.textContent = rankingState.level === 'ssfj'
        ? '分局级，点击柱条下钻到派出所'
        : `${rankingState.parentLabel || '当前分局'} · 派出所级`;
    }
    if (backButton) {
      backButton.classList.toggle('hidden', rankingState.level === 'ssfj');
    }
  }

  function initRankingControls() {
    const backButton = document.getElementById('rankingBackButton');
    if (!backButton) return;
    backButton.addEventListener('click', () => {
      if (rankingState.level === 'ssfj') return;
      rankingState.level = 'ssfj';
      rankingState.parentCode = '';
      rankingState.parentLabel = '';
      updateRankingScope();
      loadRankingChart();
    });
    updateRankingScope();
  }

  async function loadSummary() {
    const d = await fetchJSON(`${API}/summary`);
    renderStat('statTotal', (d.total_persons || 0).toLocaleString(), d.total_persons_change_pct);
    renderStat('statHighRisk', (d.high_risk_count || 0).toLocaleString(), d.high_risk_count_change_pct);
    renderStat('statMonthCases', (d.month_cases || 0).toLocaleString(), d.month_cases_change_pct);
    renderStat('statAvgScore', d.avg_score || '--', d.avg_score_change_pct);
  }

  function renderStat(id, value, changePct) {
    const el = document.getElementById(id);
    el.textContent = value;
    const parent = el.parentElement;
    parent.querySelectorAll('.stat-change').forEach(node => node.remove());
    if (changePct === null || changePct === undefined || Number.isNaN(Number(changePct))) return;
    const change = document.createElement('div');
    const direction = Number(changePct) >= 0 ? 'up' : 'down';
    change.className = `stat-change ${direction} mt-2`;
    change.textContent = `${Number(changePct) >= 0 ? '↑' : '↓'} ${Math.abs(Number(changePct)).toFixed(1)}%`;
    parent.appendChild(change);
  }

  async function loadCaseTypeChart() {
    const d = await fetchJSON(`${API}/distribution?dim=case_type`);
    const chart = echarts.init(document.getElementById('chartCaseType'));
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['42%', '78%'],
        center: ['50%', '52%'],
        label: { color: '#94a3b8', fontSize: 12 },
        data: (d.items || []).map(i => ({ name: i.label, value: i.value }))
      }]
    });
    bindChartResize(chart);
  }

  async function loadTrendChart() {
    const d = await fetchJSON(`${API}/trend?months=12&metric=cases`);
    const chart = echarts.init(document.getElementById('chartTrend'));
    const points = d.points || [];
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 46, right: 18, top: 12, bottom: 26 },
      xAxis: { type: 'category', data: points.map(p => p.month), axisLabel: { color: '#94a3b8', fontSize: 11 }, axisLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 11 }, splitLine: { lineStyle: { color: '#334155' } } },
      series: [{ type: 'line', smooth: true, data: points.map(p => p.count), areaStyle: { color: 'rgba(59,130,246,0.15)' }, lineStyle: { color: '#3b82f6' }, itemStyle: { color: '#3b82f6' } }]
    });
    bindChartResize(chart);
  }

  async function loadRiskLevelChart() {
    const d = await fetchJSON(`${API}/distribution?dim=risk_level`);
    const chart = echarts.init(document.getElementById('chartRiskLevel'));
    const colorMap = { extreme: '#dc2626', high: '#ea580c', medium: '#ca8a04', low: '#2563eb', normal: '#16a34a' };
    const labelMap = { extreme: '极高', high: '高', medium: '中', low: '低', normal: '正常' };
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['45%', '80%'],
        center: ['50%', '52%'],
        label: { color: '#94a3b8', fontSize: 12 },
        data: (d.items || []).map(i => ({
          name: labelMap[i.label] || i.label,
          value: i.value,
          itemStyle: { color: colorMap[i.label] || '#6b7280' }
        }))
      }]
    });
    bindChartResize(chart);
  }

  async function loadRankingChart() {
    const params = new URLSearchParams({ metric: 'risk_count', level: rankingState.level });
    if (rankingState.parentCode) params.set('parent_code', rankingState.parentCode);
    const d = await fetchJSON(`${API}/ranking?${params.toString()}`);
    const container = document.getElementById('chartRanking');
    const chart = echarts.getInstanceByDom(container) || echarts.init(container);
    const items = (d.items || []).slice(0, 8).reverse();
    updateRankingScope();
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 80, right: 20, top: 10, bottom: 20 },
      xAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10 }, splitLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'category', data: items.map(i => i.label || ''), axisLabel: { color: '#94a3b8', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      series: [{
        type: 'bar',
        cursor: rankingState.level === 'ssfj' ? 'pointer' : 'default',
        data: items.map(i => ({ value: i.value, item: i })),
        itemStyle: { color: '#3b82f6', borderRadius: [0, 4, 4, 0] }
      }]
    }, true);
    chart.off('click');
    chart.on('click', params => {
      const item = params?.data?.item;
      if (rankingState.level !== 'ssfj' || !item || !item.code) return;
      rankingState.level = 'sspcs';
      rankingState.parentCode = item.code;
      rankingState.parentLabel = item.label || params.name || '';
      updateRankingScope();
      loadRankingChart();
    });
    bindChartResize(chart);
  }

  async function loadAgeChart() {
    const d = await fetchJSON(`${API}/distribution?dim=age`);
    const chart = echarts.init(document.getElementById('chartAge'));
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['30%', '60%'],
        label: { color: '#94a3b8', fontSize: 11 },
        data: (d.items || []).map(i => ({ name: i.label, value: i.value })),
        itemStyle: { color: function (p) { return ['#3b82f6', '#f59e0b', '#ef4444'][p.dataIndex % 3]; } }
      }]
    });
    bindChartResize(chart);
  }

  async function loadHeatmap() {
    const d = await fetchJSON(`${API}/heatmap?days=30`);
    const chart = echarts.init(document.getElementById('chartHeatmap'));
    const points = (d.items || []).map(i => [Number(i.lng), Number(i.lat), Number(i.weight || 0)])
      .filter(i => Number.isFinite(i[0]) && Number.isFinite(i[1]));
    const maxWeight = points.reduce((max, item) => Math.max(max, item[2]), 1);
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: p => `经度: ${p.value[0]}<br/>纬度: ${p.value[1]}<br/>权重: ${p.value[2]}`
      },
      grid: { left: 8, right: 8, top: 15, bottom: 8 },
      visualMap: {
        min: 0,
        max: maxWeight,
        show: false,
        inRange: { color: ['#2563eb', '#22c55e', '#f59e0b', '#ef4444'] }
      },
      xAxis: {
        type: 'value',
        scale: true,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { show: false },
        splitLine: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { show: false },
        splitLine: { show: false }
      },
      series: [{
        type: 'scatter',
        data: points,
        symbolSize: val => Math.max(6, Math.min(28, Math.sqrt(val[2] || 1) * 4)),
        itemStyle: { opacity: 0.85 }
      }]
    });
    bindChartResize(chart);
  }

  async function loadAlerts() {
    const d = await fetchJSON(`${API}/alerts?limit=15`);
    alertsCache = (d.items || []).slice(0, 15);
    renderAlerts(alertsCache);
  }

  function renderAlerts(items) {
    const container = document.getElementById('alertList');
    if (!items.length) {
      container.innerHTML = '<div class="text-slate-500 text-center py-8">暂无预警</div>';
      return;
    }
    const levelColors = { critical: 'bg-red-500', warning: 'bg-orange-500', info: 'bg-blue-500' };
    container.innerHTML = items.map(a => `
      <div class="alert-item flex items-start gap-3">
        <span class="mt-1 w-2 h-2 rounded-full shrink-0 ${levelColors[a.alert_level] || 'bg-slate-500'}"></span>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-200">${a.xm || ''}</span>
            <span class="text-xs text-slate-500">${a.trigger_time ? new Date(a.trigger_time).toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}</span>
          </div>
          <div class="text-xs text-slate-400 truncate">${a.alert_content || a.alert_type || ''}</div>
        </div>
        ${a.zjhm ? `<a href="/profile/${encodeURIComponent(a.zjhm)}" class="text-xs text-blue-400 hover:underline shrink-0">详情</a>` : '<span class="text-xs text-slate-500 shrink-0">详情</span>'}
        <button type="button" data-action="dispatch-alert" data-zjhm="${escapeAttr(a.zjhm || '')}" class="text-xs text-blue-400 hover:underline shrink-0">派发</button>
      </div>
    `).join('');
    container.querySelectorAll('[data-action="dispatch-alert"]').forEach(btn => {
      btn.addEventListener('click', () => dispatchPerson(btn.dataset.zjhm));
    });
  }

  function pushAlert(alert) {
    if (!alert) return;
    const key = alert.id != null ? `id:${alert.id}` : `${alert.alert_type || ''}|${alert.zjhm || ''}|${alert.trigger_time || ''}`;
    const exists = alertsCache.some(item => {
      const itemKey = item.id != null ? `id:${item.id}` : `${item.alert_type || ''}|${item.zjhm || ''}|${item.trigger_time || ''}`;
      return itemKey === key;
    });
    if (exists) return;
    alertsCache.unshift(alert);
    alertsCache = alertsCache.slice(0, 15);
    renderAlerts(alertsCache);
  }

  function startAlertPolling() {
    if (alertPollTimer) return;
    alertPollTimer = setInterval(loadAlerts, 30000);
  }

  function stopAlertPolling() {
    if (!alertPollTimer) return;
    clearInterval(alertPollTimer);
    alertPollTimer = null;
  }

  function initAlertStream() {
    if (!window.EventSource) {
      startAlertPolling();
      return;
    }
    try {
      alertEventSource = new EventSource(`${API}/alerts/stream`);
      stopAlertPolling();
      alertEventSource.onmessage = event => {
        try {
          pushAlert(JSON.parse(event.data));
        } catch {
          startAlertPolling();
        }
      };
      alertEventSource.onerror = () => {
        if (alertEventSource) {
          alertEventSource.close();
          alertEventSource = null;
        }
        startAlertPolling();
      };
    } catch {
      startAlertPolling();
    }
  }

  async function dispatchPerson(zjhm) {
    if (!zjhm) {
      showError('该预警缺少证件号，无法派发');
      return;
    }
    showLoading('正在校验派发对象...');
    try {
      const res = await fetch(`${API}/dispatch/from-person`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zjhm })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showError(data.message || data.error || '派发校验失败');
        return;
      }
      window.location.href = data.redirect || `/dispatch?zjhm=${encodeURIComponent(zjhm)}`;
    } catch (e) {
      showError('派发失败: ' + e.message);
    } finally {
      hideLoading();
    }
  }

  function escapeAttr(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/`/g, '&#96;');
  }

  initRankingControls();
  loadSummary();
  loadCaseTypeChart();
  loadTrendChart();
  loadRiskLevelChart();
  loadRankingChart();
  loadAgeChart();
  loadHeatmap();
  loadAlerts();
  initAlertStream();

  setInterval(loadSummary, 60000);
})();
