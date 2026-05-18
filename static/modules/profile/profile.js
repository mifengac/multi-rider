(function () {
  const riskColors = { extreme: '#dc2626', high: '#ea580c', medium: '#ca8a04', low: '#2563eb', normal: '#16a34a' };
  const riskLabels = { extreme: '极高风险', high: '高风险', medium: '中风险', low: '低风险', normal: '正常' };

  async function load() {
    const res = await fetch(`/api/profile/${ZJHM}`);
    if (!res.ok) {
      document.getElementById('loadingState').textContent = '未找到该人员信息';
      return;
    }
    const data = await res.json();
    render(data);
  }

  function render(d) {
    const main = document.getElementById('profileMain');
    const basic = d.basic || {};
    const score = d.score || {};
    const family = d.family || {};
    const education = d.education || {};
    const cases = d.cases || [];
    const behaviors = d.behaviors || [];
    const trajectory = d.trajectory || {};
    const relations = d.relations || {};
    const suggestions = d.suggestions || [];
    const hotels = d.hotels || [];

    const riskLevel = score.risk_level || 'normal';
    const totalScore = score.total_score || 0;
    const riskColor = riskColors[riskLevel] || '#6b7280';

    main.innerHTML = `
      <!-- Header Card -->
      <div class="profile-card mb-4 flex items-start gap-6">
        <div class="w-20 h-20 rounded-full bg-slate-200 flex items-center justify-center text-2xl font-bold text-slate-500 shrink-0">
          ${(basic.xm || '?')[0]}
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-3 mb-1">
            <h2 class="text-2xl font-bold">${basic.xm || '--'}</h2>
            <span class="badge" style="background:${riskColor}">${riskLabels[riskLevel]}</span>
            <span class="text-sm text-slate-500">${basic.xb || ''} · ${calcAge(basic.csrq)}岁</span>
          </div>
          <div class="text-sm text-slate-500 mb-3">
            ${basic.zjhm || ''} · ${basic.hjdz || basic.xzdxz || ''}
          </div>
          <div class="flex items-center gap-4">
            <div class="flex-1 max-w-xs">
              <div class="flex justify-between text-xs mb-1">
                <span>风险评分</span><span class="font-bold" style="color:${riskColor}">${totalScore}/100</span>
              </div>
              <div class="risk-bar"><div class="risk-bar-fill" style="width:${totalScore}%;background:${riskColor}"></div></div>
            </div>
            <div class="text-xs text-slate-400">
              案件${score.dim_case || 0} · 行为${score.dim_behavior || 0} · 家庭${score.dim_family || 0} · 教育${score.dim_education || 0} · 社交${score.dim_social || 0}
            </div>
          </div>
        </div>
        <div class="shrink-0 flex gap-2">
          <a href="/graph?zjhm=${basic.zjhm || ''}" class="px-3 py-1.5 text-xs bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100">展开图谱</a>
        </div>
      </div>

      <!-- Content Grid -->
      <div class="grid grid-cols-3 gap-4">
        <!-- Left Column -->
        <div class="col-span-2 space-y-4">
          <!-- Cases -->
          <div class="profile-card">
            <div class="section-title">涉案记录 (${cases.length}起)</div>
            ${cases.length ? cases.map(c => `
              <div class="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <span class="text-xs text-slate-400 w-24 shrink-0">${formatDate(c.ajxx_fasj)}</span>
                <span class="text-sm font-medium">${c.ajxx_ay || c.ajxx_ajmc || '--'}</span>
                <span class="text-xs text-slate-400 ml-auto">${c.ajxx_cbdw_mc || ''}</span>
              </div>
            `).join('') : '<div class="text-sm text-slate-400">无涉案记录</div>'}
          </div>

          <!-- Behaviors -->
          <div class="profile-card">
            <div class="section-title">行为记录 (${behaviors.length}条)</div>
            ${behaviors.length ? behaviors.slice(0, 8).map(b => `
              <div class="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <span class="text-xs text-slate-400 w-24 shrink-0">${formatDate(b.wf_sj)}</span>
                <span class="text-sm">${b.wfxw_cn || b.blxwlx_cn || '--'}</span>
                <span class="text-xs text-slate-400 ml-auto">${b.fsdd || ''}</span>
              </div>
            `).join('') : '<div class="text-sm text-slate-400">无行为记录</div>'}
          </div>

          <!-- Trajectory -->
          <div class="profile-card">
            <div class="section-title">轨迹分析</div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <div class="text-xs text-slate-500 mb-2 font-semibold">高频出现地点</div>
                ${(trajectory.hotspots || []).slice(0, 5).map((h, i) => `
                  <div class="flex justify-between py-1 text-sm">
                    <span>${i + 1}. ${h.location || '--'}</span>
                    <span class="text-slate-400">${h.count}次</span>
                  </div>
                `).join('') || '<div class="text-sm text-slate-400">无数据</div>'}
              </div>
              <div>
                <div class="text-xs text-slate-500 mb-2 font-semibold">活动时段</div>
                <div id="chartTimePattern" style="height:120px"></div>
              </div>
            </div>
            ${trajectory.last_seen ? `
              <div class="mt-3 text-xs text-slate-400 border-t border-slate-100 pt-2">
                最近出现: ${formatDate(trajectory.last_seen.shot_time)} · ${trajectory.last_seen.device_name || ''}
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Right Column -->
        <div class="space-y-4">
          <!-- Family -->
          <div class="profile-card">
            <div class="section-title">家庭信息</div>
            <div class="space-y-2 text-sm">
              ${family ? `
                <div><span class="text-slate-500">监护人:</span> ${family.jhr1xm || '--'} ${family.jhr1lxdh ? '(' + family.jhr1lxdh + ')' : ''}</div>
                <div><span class="text-slate-500">家庭状况:</span> ${family.jtqk || '--'}</div>
                <div><span class="text-slate-500">困难类型:</span> ${family.knjtlx || '无'}</div>
                <div><span class="text-slate-500">儿童类别:</span> ${family.etlb || '普通'}</div>
              ` : '<div class="text-slate-400">无家庭信息</div>'}
            </div>
          </div>

          <!-- Education -->
          <div class="profile-card">
            <div class="section-title">教育状态</div>
            <div class="text-sm">
              <span class="tag">${eduLabel(education.status)}</span>
              ${education.yxx ? `<div class="mt-2 text-slate-500">学校: ${education.yxx}</div>` : ''}
              ${education.jxqk ? `<div class="text-slate-500">就学情况: ${education.jxqk}</div>` : ''}
            </div>
          </div>

          <!-- Relations -->
          <div class="profile-card">
            <div class="section-title">关系网络</div>
            ${(relations.co_suspects || []).length ? relations.co_suspects.slice(0, 5).map(c => `
              <div class="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                <a href="/profile/${c.zjhm}" class="text-sm text-blue-600 hover:underline">${c.xm || '--'}</a>
                <span class="text-xs text-slate-400">共犯${c.case_count || 1}次</span>
              </div>
            `).join('') : '<div class="text-sm text-slate-400">无关联人员</div>'}
          </div>

          <!-- Hotels -->
          ${hotels.length ? `
          <div class="profile-card">
            <div class="section-title">旅馆入住</div>
            ${hotels.slice(0, 3).map(h => `
              <div class="py-1.5 border-b border-slate-50 last:border-0 text-sm">
                <div>${h.lgmc || '--'}</div>
                <div class="text-xs text-slate-400">${formatDate(h.rzsj)} ${h.tfrxm ? '同房:' + h.tfrxm : '(独自)'}</div>
              </div>
            `).join('')}
          </div>` : ''}

          <!-- Suggestions -->
          <div class="profile-card">
            <div class="section-title">管控建议</div>
            <ul class="space-y-2">
              ${suggestions.map(s => `<li class="text-sm flex gap-2"><span class="text-blue-500 shrink-0">•</span>${s}</li>`).join('')}
            </ul>
          </div>
        </div>
      </div>
    `;

    renderTimeChart(trajectory.time_pattern);
  }

  function renderTimeChart(pattern) {
    const el = document.getElementById('chartTimePattern');
    if (!el || !pattern || !pattern.hourly_distribution) return;
    const chart = echarts.init(el);
    const hours = pattern.hourly_distribution || [];
    chart.setOption({
      grid: { left: 30, right: 10, top: 5, bottom: 20 },
      xAxis: { type: 'category', data: hours.map(h => h.hour + ':00'), axisLabel: { fontSize: 9, interval: 5 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 9 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [{ type: 'bar', data: hours.map(h => h.count), itemStyle: { color: '#3b82f6', borderRadius: [2, 2, 0, 0] } }]
    });
  }

  function calcAge(csrq) {
    if (!csrq) return '--';
    try {
      const y = parseInt(csrq.substring(0, 4));
      return new Date().getFullYear() - y;
    } catch { return '--'; }
  }

  function formatDate(d) {
    if (!d) return '--';
    try { return new Date(d).toLocaleDateString('zh-CN'); } catch { return d; }
  }

  function eduLabel(s) {
    const map = { dropout: '辍学', lost: '流失', truant: '旷课', enrolled: '在校', unknown: '未知' };
    return map[s] || s || '未知';
  }

  load();
})();
