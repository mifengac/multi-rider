(function () {
  // Demo helper: render a clickable "重点人员速览" grid on the profile landing
  // page so a presenter never has to look up an 身份证号 in the database.
  const riskColors = { extreme: '#dc2626', high: '#ea580c', medium: '#ca8a04', low: '#2563eb', normal: '#16a34a' };
  const riskLabels = { extreme: '极高风险', high: '高风险', medium: '中风险', low: '低风险', normal: '正常' };

  const grid = document.getElementById('featuredGrid');
  const randomBtn = document.getElementById('randomBtn');
  let people = [];

  async function load() {
    try {
      const res = await fetch('/api/profile/featured?limit=12');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      people = data.items || [];
      render();
    } catch (e) {
      grid.innerHTML = '<div class="col-span-3 py-10 text-center text-sm text-slate-400">重点人员列表加载失败，请直接输入身份证号查询</div>';
    }
  }

  function render() {
    if (!people.length) {
      grid.innerHTML = '<div class="col-span-3 py-10 text-center text-sm text-slate-400">暂无重点人员数据</div>';
      if (randomBtn) randomBtn.disabled = true;
      return;
    }
    grid.innerHTML = people.map(cardHtml).join('');
    grid.querySelectorAll('[data-zjhm]').forEach((el) => {
      el.addEventListener('click', () => openProfile(el.dataset.zjhm));
    });
  }

  function cardHtml(p) {
    const level = p.risk_level || 'normal';
    const color = riskColors[level] || '#6b7280';
    const score = Number(p.total_score || 0);
    const meta = [p.xb, calcAge(p.csrq) + '岁', p.area]
      .filter((v) => v && v !== '岁' && v !== '--岁')
      .map(escapeHtml)
      .join(' · ');
    return `
      <button type="button" data-zjhm="${escapeAttr(p.zjhm || '')}"
        class="text-left rounded-lg border border-slate-700 bg-slate-900 p-3 transition hover:border-blue-500 hover:bg-slate-800">
        <div class="flex items-center justify-between mb-2">
          <span class="text-base font-bold text-slate-100">${escapeHtml(p.xm || '未知')}</span>
          <span class="badge" style="background:${color}">${riskLabels[level] || level}</span>
        </div>
        <div class="flex items-end gap-1 mb-1">
          <span class="text-2xl font-bold leading-none" style="color:${color}">${score}</span>
          <span class="text-xs text-slate-500">/100</span>
        </div>
        <div class="text-xs text-slate-400 truncate">${meta || '--'}</div>
      </button>
    `;
  }

  function openProfile(zjhm) {
    if (zjhm) window.location.href = '/profile/' + encodeURIComponent(zjhm);
  }

  if (randomBtn) {
    randomBtn.addEventListener('click', () => {
      if (!people.length) return;
      const pick = people[Math.floor(Math.random() * people.length)];
      openProfile(pick.zjhm);
    });
  }

  function calcAge(csrq) {
    if (!csrq) return '--';
    try {
      const y = parseInt(String(csrq).substring(0, 4), 10);
      if (!y) return '--';
      return new Date().getFullYear() - y;
    } catch { return '--'; }
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
