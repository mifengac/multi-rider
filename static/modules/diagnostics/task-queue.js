const TASK_QUEUE_DIAGNOSTICS = {
  timer: null,
  lastPayload: null
};

function diagEscapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function diagFormatTs(ts) {
  var value = Number(ts || 0);
  if (!value) return '--';
  try {
    return new Date(value * 1000).toLocaleString('zh-CN', { hour12: false });
  } catch (e) {
    return '--';
  }
}

function diagFormatDuration(seconds) {
  var value = Number(seconds || 0);
  if (!value) return '--';
  if (value < 60) return value + ' 秒';
  if (value < 3600) return Math.floor(value / 60) + ' 分 ' + (value % 60) + ' 秒';
  return Math.floor(value / 3600) + ' 小时 ' + Math.floor((value % 3600) / 60) + ' 分';
}

function diagStatusMeta(status, stale) {
  if (stale) {
    return { label: '陈旧运行', badge: 'bg-amber-100 text-amber-700 ring-amber-200' };
  }
  var map = {
    pending: { label: '等待中', badge: 'bg-slate-100 text-slate-700 ring-slate-200' },
    running: { label: '运行中', badge: 'bg-sky-100 text-sky-700 ring-sky-200' },
    completed: { label: '已完成', badge: 'bg-emerald-100 text-emerald-700 ring-emerald-200' },
    failed: { label: '失败', badge: 'bg-rose-100 text-rose-700 ring-rose-200' }
  };
  return map[status] || { label: status || '--', badge: 'bg-slate-100 text-slate-700 ring-slate-200' };
}

function diagSetText(id, value) {
  var el = document.getElementById(id);
  if (el) el.textContent = value;
}

function diagRenderDistribution(id, items, formatter) {
  var box = document.getElementById(id);
  if (!box) return;
  if (!items || !items.length) {
    box.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">暂无数据</div>';
    return;
  }
  box.innerHTML = items.map(function (item) {
    return (
      '<div class="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3">' +
        '<span class="text-sm font-semibold text-slate-700">' + diagEscapeHtml(formatter(item)) + '</span>' +
        '<span class="font-mono text-sm text-slate-500">' + diagEscapeHtml(item.count || 0) + '</span>' +
      '</div>'
    );
  }).join('');
}

function diagRenderHealth(payload) {
  var health = payload.health || {};
  var taskQueue = health.task_queue || {};
  var badge = document.getElementById('diagHealthBadge');
  var details = document.getElementById('diagHealthDetails');
  if (badge) {
    var ok = health.ok && taskQueue.ok !== false;
    badge.textContent = ok ? '正常' : '需关注';
    badge.className = 'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ' + (ok ? 'bg-emerald-100 text-emerald-700 ring-emerald-200' : 'bg-amber-100 text-amber-700 ring-amber-200');
  }
  if (details) {
    details.innerHTML =
      '<div>运行中：' + diagEscapeHtml(taskQueue.running_count || 0) + ' 个</div>' +
      '<div>陈旧运行：' + diagEscapeHtml(taskQueue.stale_running_count || 0) + ' 个</div>' +
      '<div>陈旧阈值：' + diagFormatDuration(taskQueue.stale_after_seconds || payload.stale_after_seconds || 0) + '</div>' +
      ((taskQueue.sample_task_ids || []).length
        ? '<div class="mt-2 break-all text-amber-700">样例：' + diagEscapeHtml((taskQueue.sample_task_ids || []).join(', ')) + '</div>'
        : '');
  }
}

function diagRenderTasks(tasks) {
  var body = document.getElementById('diagTaskRows');
  if (!body) return;
  if (!tasks || !tasks.length) {
    body.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-sm text-slate-500">暂无符合筛选条件的队列任务</td></tr>';
    return;
  }
  body.innerHTML = tasks.map(function (task) {
    var meta = diagStatusMeta(task.status, task.stale);
    var owner = task.owner_key || task.owner_ip || '--';
    var elapsed = task.status === 'running' ? task.run_seconds : task.total_seconds;
    return (
      '<tr class="align-top">' +
        '<td class="px-4 py-3">' +
          '<div class="font-mono text-xs font-semibold text-slate-900">' + diagEscapeHtml(task.task_id || '') + '</div>' +
          '<div class="mt-1 text-xs text-slate-500">' + diagEscapeHtml(task.task_type || '') + ' · retries ' + diagEscapeHtml(task.retries || 0) + '</div>' +
          '<div class="mt-1 text-xs text-slate-400">' + diagEscapeHtml(diagFormatTs(task.created_ts)) + '</div>' +
        '</td>' +
        '<td class="px-4 py-3"><span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge + '">' + meta.label + '</span></td>' +
        '<td class="px-4 py-3 font-mono text-xs text-slate-600">' + diagEscapeHtml(task.job_id || '--') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-600">' +
          '<div>等待：' + diagFormatDuration(task.wait_seconds) + '</div>' +
          '<div>执行：' + diagFormatDuration(elapsed) + '</div>' +
        '</td>' +
        '<td class="px-4 py-3 font-mono text-xs text-slate-500">' + diagEscapeHtml(owner) + '</td>' +
        '<td class="max-w-[260px] px-4 py-3 text-xs leading-6 text-rose-600">' + diagEscapeHtml(task.error || '') + '</td>' +
      '</tr>'
    );
  }).join('');
}

function renderTaskQueueDiagnostics(payload) {
  TASK_QUEUE_DIAGNOSTICS.lastPayload = payload;
  var totals = payload.totals || {};
  diagSetText('diagQueueTotal', totals.total || 0);
  diagSetText('diagQueuePending', totals.pending || 0);
  diagSetText('diagQueueRunning', totals.running || 0);
  diagSetText('diagQueueFailed', totals.failed || 0);
  diagSetText('diagQueueStale', totals.stale_running || 0);
  diagSetText('diagLastRefresh', '刷新时间：' + diagFormatTs(payload.generated_ts));
  diagRenderHealth(payload);
  diagRenderDistribution('diagByStatus', payload.by_status || [], function (item) {
    return item.status || '--';
  });
  diagRenderDistribution('diagByTypeStatus', payload.by_type_status || [], function (item) {
    return (item.task_type || '--') + ' / ' + (item.status || '--');
  });
  diagRenderTasks(payload.tasks || []);
}

function refreshTaskQueueDiagnostics() {
  var params = new URLSearchParams();
  var typeEl = document.getElementById('diagTaskTypeFilter');
  var statusEl = document.getElementById('diagStatusFilter');
  var limitEl = document.getElementById('diagLimitFilter');
  if (typeEl && typeEl.value) params.set('task_type', typeEl.value);
  if (statusEl && statusEl.value) params.set('status', statusEl.value);
  params.set('limit', (limitEl && limitEl.value) || '60');

  return fetch('/diagnostics/task-queue?' + params.toString())
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      if (!payload.ok) {
        throw new Error(payload.error || '诊断接口返回失败');
      }
      renderTaskQueueDiagnostics(payload);
    })
    .catch(function (error) {
      var body = document.getElementById('diagTaskRows');
      if (body) {
        body.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-sm text-rose-600">' + diagEscapeHtml(error.message || '诊断加载失败') + '</td></tr>';
      }
    });
}

function setTaskQueueAutoRefresh(enabled) {
  if (TASK_QUEUE_DIAGNOSTICS.timer) {
    clearInterval(TASK_QUEUE_DIAGNOSTICS.timer);
    TASK_QUEUE_DIAGNOSTICS.timer = null;
  }
  if (enabled) {
    TASK_QUEUE_DIAGNOSTICS.timer = setInterval(refreshTaskQueueDiagnostics, 10000);
  }
}

function initTaskQueueDiagnostics() {
  ['diagTaskTypeFilter', 'diagStatusFilter', 'diagLimitFilter'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('change', refreshTaskQueueDiagnostics);
  });
  var auto = document.getElementById('diagAutoRefresh');
  if (auto) {
    auto.addEventListener('change', function () {
      setTaskQueueAutoRefresh(auto.checked && !document.getElementById('tabDiagnostics').classList.contains('hidden'));
    });
  }
}

window.addEventListener('load', initTaskQueueDiagnostics);
