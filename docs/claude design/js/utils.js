// ============================================================
// utils.js - 共享工具函数、常量、ECharts 暗色主题配置
// ============================================================

// ---- 风险等级配置 ----
const RISK_CONFIG = {
  extreme: { label: '极高', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)' },
  high:    { label: '高',   color: '#f97316', bg: 'rgba(249,115,22,0.12)', border: 'rgba(249,115,22,0.3)' },
  medium:  { label: '中',   color: '#eab308', bg: 'rgba(234,179,8,0.12)',  border: 'rgba(234,179,8,0.3)' },
  low:     { label: '低',   color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.3)' },
  normal:  { label: '正常', color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.3)' },
};

// ---- 案件类型配色 ----
const CRIME_COLORS = {
  '盗窃': '#38bdf8', '抢劫': '#ef4444', '抢夺': '#f97316',
  '诈骗': '#a855f7', '敲诈勒索': '#eab308',
};

// ---- 图谱节点配色 ----
const NODE_COLORS = {
  person:   '#38bdf8', case:     '#a855f7', school:   '#f59e0b',
  guardian: '#10b981', highrisk: '#ef4444',
};

// ---- 格式化数字（千分位） ----
function formatNum(n) {
  if (n == null) return '--';
  return Number(n).toLocaleString('zh-CN');
}

// ---- 数字滚动动画 ----
function animateNumber(el, target, duration, prefix, suffix) {
  duration = duration || 1200;
  prefix = prefix || '';
  suffix = suffix || '';
  var start = 0;
  var startTime = null;
  var isFloat = target % 1 !== 0;

  function step(ts) {
    if (!startTime) startTime = ts;
    var progress = Math.min((ts - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    var current = start + (target - start) * eased;
    el.textContent = prefix + (isFloat ? current.toFixed(1) : formatNum(Math.round(current))) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ---- 风险等级徽章 HTML ----
function riskBadge(level) {
  var c = RISK_CONFIG[level] || RISK_CONFIG.normal;
  return '<span class="risk-badge" style="background:' + c.bg + ';color:' + c.color + ';border:1px solid ' + c.border + ';">' + c.label + '</span>';
}

// ---- 风险色条 (3px 左侧竖条) ----
function riskBar(level) {
  var c = RISK_CONFIG[level] || RISK_CONFIG.normal;
  return 'border-left:3px solid ' + c.color;
}

// ---- 趋势箭头 (公安语境: 上升=红=坏, 下降=绿=好) ----
function trendArrow(val) {
  if (val > 0) return '<span style="color:#ef4444">▲ ' + Math.abs(val) + '%</span>';
  if (val < 0) return '<span style="color:#22c55e">▼ ' + Math.abs(val) + '%</span>';
  return '<span style="color:var(--text-muted)">— 0%</span>';
}

// ---- 骨架屏 HTML ----
function skeleton(lines) {
  lines = lines || 3;
  var html = '<div class="skeleton-wrap">';
  for (var i = 0; i < lines; i++) {
    var w = 60 + Math.random() * 35;
    html += '<div class="skeleton-line" style="width:' + w + '%;animation-delay:' + (i * 0.12) + 's"></div>';
  }
  return html + '</div>';
}

// ---- 空状态 HTML ----
function emptyState(iconName, title, subtitle) {
  return '<div class="empty-state">' +
    '<div class="empty-state-icon">' + icon(iconName || 'info', 48) + '</div>' +
    '<div class="empty-state-title">' + (title || '暂无数据') + '</div>' +
    (subtitle ? '<div class="empty-state-sub">' + subtitle + '</div>' : '') +
    '</div>';
}

// ---- 错误态 HTML ----
function errorState(title, subtitle) {
  return '<div class="empty-state">' +
    '<div class="empty-state-icon" style="color:#ef4444">' + icon('alertCircle', 48) + '</div>' +
    '<div class="empty-state-title">' + (title || '加载失败') + '</div>' +
    (subtitle ? '<div class="empty-state-sub">' + subtitle + '</div>' : '') +
    '</div>';
}

// ---- 防抖 ----
function debounce(fn, delay) {
  var t;
  return function() {
    var ctx = this, args = arguments;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(ctx, args); }, delay);
  };
}

// ---- 简易 Markdown → HTML (AI 对话用) ----
function renderMarkdown(text) {
  if (!text) return '';
  var html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="md-bold">$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
    .replace(/^- (.+)$/gm, '<li class="md-li">$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li class="md-li md-oli">$2</li>')
    .replace(/\n{2,}/g, '</p><p class="md-p">')
    .replace(/\n/g, '<br/>');
  html = '<p class="md-p">' + html + '</p>';
  // Wrap consecutive <li> in <ul>
  html = html.replace(/(<li class="md-li">[\s\S]*?<\/li>)(?=\s*(?:<li|<\/p>|$))/g, function(m) {
    return '<ul class="md-ul">' + m + '</ul>';
  });
  return html;
}

// ---- ECharts 通用暗色选项 ----
function echartBaseOption() {
  return {
    backgroundColor: 'transparent',
    textStyle: {
      color: '#94a3b8',
      fontFamily: '"PingFang SC","Microsoft YaHei","Hiragino Sans GB",system-ui,sans-serif',
      fontSize: 11,
    },
    tooltip: {
      backgroundColor: '#0f1729',
      borderColor: 'rgba(56,189,248,0.3)',
      borderWidth: 1,
      textStyle: { color: '#e6edf7', fontSize: 12 },
      extraCssText: 'box-shadow:0 0 12px rgba(56,189,248,0.15);',
    },
    grid: {
      containLabel: true,
      left: 12, right: 12, top: 24, bottom: 12,
    },
  };
}

// ---- ECharts 暗色坐标轴公共配置 ----
function echartAxisDefaults() {
  return {
    axisLine: { lineStyle: { color: '#1e293b' } },
    axisTick: { show: false },
    axisLabel: { color: '#94a3b8', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(148,163,184,0.08)' } },
  };
}

// ---- ECharts 青色渐变填充 (折线区域用) ----
function cyanAreaGradient(opacity) {
  opacity = opacity || 0.25;
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: 'rgba(56,189,248,' + opacity + ')' },
    { offset: 1, color: 'rgba(56,189,248,0)' },
  ]);
}

// ---- ECharts 青蓝柱状渐变 ----
function cyanBarGradient() {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: '#38bdf8' },
    { offset: 1, color: '#3b82f6' },
  ]);
}

// ---- 简易事件委托 ----
function delegate(container, selector, event, handler) {
  container.addEventListener(event, function(e) {
    var target = e.target.closest(selector);
    if (target && container.contains(target)) handler(e, target);
  });
}

// ---- 实时时钟 ----
function startClock(el) {
  function tick() {
    var now = new Date();
    el.textContent = [now.getHours(), now.getMinutes(), now.getSeconds()]
      .map(function(n) { return String(n).padStart(2, '0'); }).join(':');
  }
  tick();
  return setInterval(tick, 1000);
}

// ---- 页面管理器 ----
var PageManager = {
  current: null,
  pages: {},
  register: function(name, mod) { this.pages[name] = mod; },
  switchTo: function(name) {
    if (this.current === name) return;
    // Destroy old page
    if (this.current && this.pages[this.current] && this.pages[this.current].destroy) {
      this.pages[this.current].destroy();
    }
    // Hide all
    document.querySelectorAll('.page-container').forEach(function(el) {
      el.classList.add('hidden');
    });
    // Show target
    var container = document.getElementById('page-' + name);
    if (container) {
      container.classList.remove('hidden');
      // Render & init
      var mod = this.pages[name];
      if (mod) {
        if (!container.dataset.rendered) {
          mod.render(container);
          container.dataset.rendered = '1';
        }
        if (mod.init) mod.init();
      }
    }
    // Update nav
    document.querySelectorAll('.nav-tab').forEach(function(tab) {
      tab.classList.toggle('active', tab.dataset.page === name);
    });
    // Update subtitle
    var subtitles = {
      dashboard: '态势总览', profile: '个人画像',
      graph: '关系图谱', analyst: 'AI 研判助手',
      workbench: '工作台'
    };
    var subEl = document.getElementById('page-subtitle');
    if (subEl) subEl.textContent = subtitles[name] || '';
    this.current = name;
  }
};
