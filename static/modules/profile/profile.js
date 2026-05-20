(function () {
  const riskColors = { extreme: '#dc2626', high: '#ea580c', medium: '#ca8a04', low: '#2563eb', normal: '#16a34a' };
  const riskLabels = { extreme: '极高风险', high: '高风险', medium: '中风险', low: '低风险', normal: '正常' };
  const timelineLabels = { case: '案件', behavior: '行为', trajectory: '轨迹', hotel: '入住' };

  async function load() {
    const res = await fetch(`/api/profile/${ZJHM}`);
    if (!res.ok) {
      document.getElementById('loadingState').textContent = '未找到该人员信息';
      return;
    }
    const data = await res.json();
    const [timeline, photo] = await Promise.all([
      fetchJSONSafe(`/api/profile/${ZJHM}/timeline`),
      fetchJSONSafe(`/api/profile/${ZJHM}/photo`)
    ]);
    data.timeline = timeline.items || [];
    if (photo && photo.zp) {
      data.photo = photo;
    }
    render(data);
  }

  async function fetchJSONSafe(url) {
    try {
      const res = await fetch(url);
      if (!res.ok) return {};
      return await res.json();
    } catch {
      return {};
    }
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
    const timeline = d.timeline || [];
    const scoreTrend = d.score_trend || [];

    const riskLevel = score.risk_level || 'normal';
    const totalScore = score.total_score || 0;
    const riskColor = riskColors[riskLevel] || '#6b7280';

    main.innerHTML = `
      <div class="profile-card mb-4 flex items-start gap-6">
        <div class="w-20 h-20 rounded-full bg-slate-200 flex items-center justify-center text-2xl font-bold text-slate-500 shrink-0 overflow-hidden">
          ${renderAvatar(basic, d.photo)}
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-3 mb-1">
            <h2 class="text-2xl font-bold">${escapeHtml(basic.xm || '--')}</h2>
            <span class="badge" style="background:${riskColor}">${riskLabels[riskLevel]}</span>
            <span class="text-sm text-slate-500">${escapeHtml(basic.xb || '')} · ${calcAge(basic.csrq)}岁</span>
          </div>
          <div class="text-sm text-slate-500 mb-3">
            ${escapeHtml(basic.zjhm || '')} · ${escapeHtml(basic.hjdz || basic.xzdxz || '')}
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
          <a href="/graph?zjhm=${encodeURIComponent(basic.zjhm || '')}" class="px-3 py-1.5 text-xs bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100">展开图谱</a>
          <button type="button" data-action="dispatch-person" data-zjhm="${escapeAttr(basic.zjhm || ZJHM || '')}" class="px-3 py-1.5 text-xs bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100">派发任务</button>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div class="col-span-2 space-y-4">
          <div class="profile-card">
            <div class="section-title">涉案记录 (${cases.length}起)</div>
            ${cases.length ? cases.map(c => `
              <div class="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <span class="text-xs text-slate-400 w-24 shrink-0">${formatDate(c.ajxx_fasj)}</span>
                <span class="text-sm font-medium">${escapeHtml(c.ajxx_ay || c.ajxx_ajmc || '--')}</span>
                <span class="text-xs text-slate-400 ml-auto">${escapeHtml(c.ajxx_cbdw_mc || '')}</span>
              </div>
            `).join('') : '<div class="text-sm text-slate-400">无涉案记录</div>'}
          </div>

          <div class="profile-card">
            <div class="section-title">行为记录 (${behaviors.length}条)</div>
            ${behaviors.length ? behaviors.slice(0, 8).map(b => `
              <div class="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <span class="text-xs text-slate-400 w-24 shrink-0">${formatDate(b.wf_sj)}</span>
                <span class="text-sm">${escapeHtml(b.wfxw_cn || b.blxwlx_cn || '--')}</span>
                <span class="text-xs text-slate-400 ml-auto">${escapeHtml(b.fsdd || '')}</span>
              </div>
            `).join('') : '<div class="text-sm text-slate-400">无行为记录</div>'}
          </div>

          <div class="profile-card">
            <div class="section-title">轨迹分析</div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <div class="text-xs text-slate-500 mb-2 font-semibold">高频出现地点</div>
                ${(trajectory.hotspots || []).slice(0, 5).map((h, i) => `
                  <div class="flex justify-between py-1 text-sm">
                    <span>${i + 1}. ${escapeHtml(h.location || '--')}</span>
                    <span class="text-slate-400">${h.count || 0}次</span>
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
                最近出现: ${formatDate(trajectory.last_seen.shot_time)} · ${escapeHtml(trajectory.last_seen.device_name || '')}
              </div>
            ` : ''}
          </div>
        </div>

        <div class="space-y-4">
          <div class="profile-card">
            <div class="section-title">家庭信息</div>
            <div class="space-y-2 text-sm">
              ${family ? `
                <div><span class="text-slate-500">监护人:</span> ${escapeHtml(family.jhr1xm || '--')} ${family.jhr1lxdh ? '(' + escapeHtml(family.jhr1lxdh) + ')' : ''}</div>
                <div><span class="text-slate-500">家庭状况:</span> ${escapeHtml(family.jtqk || '--')}</div>
                <div><span class="text-slate-500">困难类型:</span> ${escapeHtml(family.knjtlx || '无')}</div>
                <div><span class="text-slate-500">儿童类别:</span> ${escapeHtml(family.etlb || '普通')}</div>
              ` : '<div class="text-slate-400">无家庭信息</div>'}
            </div>
          </div>

          <div class="profile-card">
            <div class="section-title">教育状态</div>
            <div class="text-sm">
              <span class="tag">${eduLabel(education.status)}</span>
              ${education.yxx ? `<div class="mt-2 text-slate-500">学校: ${escapeHtml(education.yxx)}</div>` : ''}
              ${education.jxqk ? `<div class="text-slate-500">就学情况: ${escapeHtml(education.jxqk)}</div>` : ''}
            </div>
          </div>

          <div class="profile-card">
            <div class="section-title">评分趋势</div>
            <div id="chartScoreTrend" style="height:150px"></div>
          </div>

          <div class="profile-card">
            <div class="section-title">关系网络</div>
            ${renderGang(relations.gang)}
            ${(relations.co_suspects || []).length ? relations.co_suspects.slice(0, 5).map(c => `
              <div class="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                <a href="/profile/${encodeURIComponent(c.zjhm || '')}" class="text-sm text-blue-600 hover:underline">${escapeHtml(c.xm || '--')}</a>
                <span class="text-xs text-slate-400">共犯${c.case_count || 1}次</span>
              </div>
            `).join('') : '<div class="text-sm text-slate-400">无关联人员</div>'}
          </div>

          ${hotels.length ? `
          <div class="profile-card">
            <div class="section-title">旅馆入住</div>
            ${hotels.slice(0, 3).map(h => `
              <div class="py-1.5 border-b border-slate-50 last:border-0 text-sm">
                <div>${escapeHtml(h.lgmc || '--')}</div>
                <div class="text-xs text-slate-400">${formatDate(h.rzsj)} ${h.tfrxm ? '同房:' + escapeHtml(h.tfrxm) : '(独自)'}</div>
              </div>
            `).join('')}
          </div>` : ''}

          <div class="profile-card">
            <div class="section-title">管控建议</div>
            <ul class="space-y-2">
              ${suggestions.map(s => `<li class="text-sm flex gap-2"><span class="text-blue-500 shrink-0">•</span>${escapeHtml(s)}</li>`).join('')}
            </ul>
          </div>
        </div>
      </div>

      <div class="profile-card mt-4">
        <div class="section-title">时间轴</div>
        ${renderTimeline(timeline)}
      </div>
    `;

    renderTimeChart(trajectory.time_pattern);
    renderScoreTrend(scoreTrend);
    const dispatchButton = main.querySelector('[data-action="dispatch-person"]');
    if (dispatchButton) {
      dispatchButton.addEventListener('click', () => dispatchPerson(dispatchButton.dataset.zjhm));
    }
  }

  async function dispatchPerson(zjhm) {
    if (!zjhm) {
      alert('缺少证件号，无法派发');
      return;
    }
    try {
      const res = await fetch('/api/dashboard/dispatch/from-person', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zjhm })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert('派发校验失败');
        return;
      }
      window.location.href = data.redirect || `/dispatch?zjhm=${encodeURIComponent(zjhm)}`;
    } catch (e) {
      alert('派发失败: ' + e.message);
    }
  }

  function renderAvatar(basic, photo) {
    const src = photoSrc(photo);
    if (src) {
      return `<img src="${escapeAttr(src)}" alt="" class="w-full h-full object-cover">`;
    }
    return escapeHtml((basic.xm || '?')[0]);
  }

  function photoSrc(photo) {
    const zp = photo && photo.zp;
    if (!zp) return '';
    if (/^(https?:|data:|\/)/i.test(zp)) return zp;
    return `data:image/jpeg;base64,${zp}`;
  }

  function renderGang(gang) {
    if (!gang || !gang.is_gang) return '';
    const members = gang.members || [];
    return `
      <div class="badge-extreme mb-3">团伙关联 ${gang.size || members.length} 人</div>
      <div class="mb-3 space-y-1">
        ${members.map(member => `
          <div class="text-xs text-slate-400">${escapeHtml(member.xm || member.zjhm || '--')}</div>
        `).join('')}
      </div>
    `;
  }

  function renderTimeline(items) {
    if (!items.length) {
      return '<div class="text-sm text-slate-400">暂无时间轴记录</div>';
    }
    return `
      <div class="space-y-0">
        ${items.map(item => `
          <div class="timeline-item">
            <div class="flex items-center gap-2 mb-1">
              <div class="text-sm font-semibold text-slate-100">${escapeHtml(item.title || '--')}</div>
              <span class="tag">${timelineLabels[item.type] || item.type || '记录'}</span>
            </div>
            <div class="text-xs text-slate-400">${formatDateTime(item.time)}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function renderTimeChart(pattern) {
    const el = document.getElementById('chartTimePattern');
    if (!el || !pattern || !pattern.hourly_distribution) return;
    const chart = echarts.init(el);
    const hours = pattern.hourly_distribution || [];
    chart.setOption({
      grid: { left: 30, right: 10, top: 5, bottom: 20 },
      xAxis: { type: 'category', data: hours.map(h => h.hour + ':00'), axisLabel: { fontSize: 9, interval: 5, color: '#94a3b8' } },
      yAxis: { type: 'value', axisLabel: { fontSize: 9, color: '#94a3b8' }, splitLine: { lineStyle: { color: '#334155' } } },
      series: [{ type: 'bar', data: hours.map(h => h.count), itemStyle: { color: '#3b82f6', borderRadius: [2, 2, 0, 0] } }]
    });
  }

  function renderScoreTrend(points) {
    const el = document.getElementById('chartScoreTrend');
    if (!el) return;
    if (!points || !points.length) {
      el.innerHTML = '<div class="text-sm text-slate-400 py-10 text-center">暂无趋势数据</div>';
      return;
    }
    const chart = echarts.init(el);
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 32, right: 12, top: 12, bottom: 24 },
      xAxis: {
        type: 'category',
        data: points.map(p => formatMonth(p.calc_time || p.time || p.month)),
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        axisLine: { lineStyle: { color: '#334155' } }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#334155' } }
      },
      series: [{
        type: 'line',
        smooth: true,
        data: points.map(p => Number(p.total_score || p.score || 0)),
        lineStyle: { color: '#3b82f6' },
        itemStyle: { color: '#3b82f6' },
        areaStyle: { color: 'rgba(59,130,246,0.15)' }
      }]
    });
  }

  function calcAge(csrq) {
    if (!csrq) return '--';
    try {
      const y = parseInt(String(csrq).substring(0, 4), 10);
      return new Date().getFullYear() - y;
    } catch { return '--'; }
  }

  function formatDate(d) {
    if (!d) return '--';
    try { return new Date(d).toLocaleDateString('zh-CN'); } catch { return d; }
  }

  function formatDateTime(d) {
    if (!d) return '--';
    try { return new Date(d).toLocaleString('zh-CN', { hour12: false }); } catch { return d; }
  }

  function formatMonth(d) {
    if (!d) return '--';
    try {
      const date = new Date(d);
      if (Number.isNaN(date.getTime())) return String(d);
      return `${date.getMonth() + 1}/${date.getDate()}`;
    } catch {
      return String(d);
    }
  }

  function eduLabel(s) {
    const map = { dropout: '辍学', lost: '流失', truant: '旷课', enrolled: '在校', unknown: '未知' };
    return map[s] || s || '未知';
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

  load();
})();
