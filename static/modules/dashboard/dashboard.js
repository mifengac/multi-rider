(function () {
  const API = '/api/dashboard';

  function updateClock() {
    const el = document.getElementById('clock');
    if (el) el.textContent = new Date().toLocaleString('zh-CN', { hour12: false });
  }
  setInterval(updateClock, 1000);
  updateClock();

  async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
  }

  async function loadSummary() {
    const d = await fetchJSON(`${API}/summary`);
    document.getElementById('statTotal').textContent = (d.total_persons || 0).toLocaleString();
    document.getElementById('statHighRisk').textContent = (d.high_risk_count || 0).toLocaleString();
    document.getElementById('statMonthCases').textContent = (d.month_cases || 0).toLocaleString();
    document.getElementById('statAvgScore').textContent = d.avg_score || '--';
  }

  async function loadCaseTypeChart() {
    const d = await fetchJSON(`${API}/distribution?dim=case_type`);
    const chart = echarts.init(document.getElementById('chartCaseType'));
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['35%', '65%'],
        label: { color: '#94a3b8', fontSize: 11 },
        data: (d.items || []).map(i => ({ name: i.label, value: i.value }))
      }]
    });
    window.addEventListener('resize', () => chart.resize());
  }

  async function loadTrendChart() {
    const d = await fetchJSON(`${API}/trend?months=12&metric=cases`);
    const chart = echarts.init(document.getElementById('chartTrend'));
    const points = d.points || [];
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: points.map(p => p.month), axisLabel: { color: '#94a3b8', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10 }, splitLine: { lineStyle: { color: '#334155' } } },
      series: [{ type: 'line', smooth: true, data: points.map(p => p.count), areaStyle: { color: 'rgba(59,130,246,0.15)' }, lineStyle: { color: '#3b82f6' }, itemStyle: { color: '#3b82f6' } }]
    });
    window.addEventListener('resize', () => chart.resize());
  }

  async function loadRiskLevelChart() {
    const d = await fetchJSON(`${API}/distribution?dim=risk_level`);
    const chart = echarts.init(document.getElementById('chartRiskLevel'));
    const colorMap = { extreme: '#dc2626', high: '#ea580c', medium: '#ca8a04', low: '#2563eb', normal: '#16a34a' };
    const labelMap = { extreme: '极高', high: '高', medium: '中', low: '低', normal: '正常' };
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        label: { color: '#94a3b8', fontSize: 11 },
        data: (d.items || []).map(i => ({
          name: labelMap[i.label] || i.label,
          value: i.value,
          itemStyle: { color: colorMap[i.label] || '#6b7280' }
        }))
      }]
    });
    window.addEventListener('resize', () => chart.resize());
  }

  async function loadRankingChart() {
    const d = await fetchJSON(`${API}/ranking?metric=risk_count`);
    const chart = echarts.init(document.getElementById('chartRanking'));
    const items = (d.items || []).slice(0, 8).reverse();
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 80, right: 20, top: 10, bottom: 20 },
      xAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10 }, splitLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'category', data: items.map(i => i.label || ''), axisLabel: { color: '#94a3b8', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
      series: [{ type: 'bar', data: items.map(i => i.value), itemStyle: { color: '#3b82f6', borderRadius: [0, 4, 4, 0] } }]
    });
    window.addEventListener('resize', () => chart.resize());
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
    window.addEventListener('resize', () => chart.resize());
  }

  async function loadAlerts() {
    const d = await fetchJSON(`${API}/alerts?limit=15`);
    const container = document.getElementById('alertList');
    const items = d.items || [];
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
        <a href="/profile/${a.zjhm}" class="text-xs text-blue-400 hover:underline shrink-0">详情</a>
      </div>
    `).join('');
  }

  loadSummary();
  loadCaseTypeChart();
  loadTrendChart();
  loadRiskLevelChart();
  loadRankingChart();
  loadAgeChart();
  loadAlerts();

  setInterval(loadAlerts, 30000);
  setInterval(loadSummary, 60000);
})();
