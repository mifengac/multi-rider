const STATISTICS_STATE = {
  lastPayload: null
};

function statsEscapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function statsFormatNumber(value) {
  var n = Number(value || 0);
  return n.toLocaleString('zh-CN');
}

function statsFormatPercent(value) {
  var n = Number(value || 0);
  return (n * 100).toFixed(1) + '%';
}

function statsFormatTs(ts) {
  var n = Number(ts || 0);
  if (!n) return '--';
  return new Date(n * 1000).toLocaleString('zh-CN', { hour12: false });
}

function statsSetText(id, value) {
  var el = document.getElementById(id);
  if (el) el.textContent = value;
}

function statsParams() {
  var params = new URLSearchParams();
  var start = document.getElementById('statsStart');
  var end = document.getElementById('statsEnd');
  if (start && start.value) params.set('start', start.value);
  if (end && end.value) params.set('end', end.value);
  return params;
}

function statsRenderDistribution(id, rows, labelKey, valueKey) {
  var box = document.getElementById(id);
  if (!box) return;
  if (!rows || !rows.length) {
    box.innerHTML = '<div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">暂无数据</div>';
    return;
  }
  var max = rows.reduce(function (acc, item) { return Math.max(acc, Number(item[valueKey] || item.count || 0)); }, 1);
  box.innerHTML = rows.map(function (item) {
    var label = item[labelKey] || item.status || item.model_key || item.job_type || item.gang_id || '--';
    var value = Number(item[valueKey] || item.count || 0);
    var width = Math.max(6, Math.round(value / max * 100));
    return (
      '<div class="space-y-1">' +
        '<div class="flex items-center justify-between gap-3 text-xs">' +
          '<span class="font-semibold text-slate-700">' + statsEscapeHtml(label) + '</span>' +
          '<span class="font-mono text-slate-500">' + statsEscapeHtml(statsFormatNumber(value)) + '</span>' +
        '</div>' +
        '<div class="h-2 overflow-hidden rounded-full bg-slate-100">' +
          '<div class="h-full rounded-full bg-[#c96442]" style="width:' + width + '%"></div>' +
        '</div>' +
      '</div>'
    );
  }).join('');
}

function statsRenderRecentJobs(rows) {
  var body = document.getElementById('statsRecentJobs');
  if (!body) return;
  if (!rows || !rows.length) {
    body.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-sm text-slate-500">暂无检测任务</td></tr>';
    return;
  }
  body.innerHTML = rows.map(function (job) {
    return (
      '<tr class="border-b border-slate-100 align-top">' +
        '<td class="px-4 py-3 font-mono text-xs text-slate-700">' + statsEscapeHtml(job.id || '') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-600">' + statsEscapeHtml(job.job_type || '--') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-600">' + statsEscapeHtml(job.status || '--') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-600">' + statsFormatNumber(job.total || 0) + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-600">' + statsFormatNumber(job.kept || 0) + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-500">' + statsEscapeHtml(statsFormatTs(job.start_ts)) + '</td>' +
      '</tr>'
    );
  }).join('');
}

function statsRenderNotes(notes) {
  var box = document.getElementById('statsNotes');
  if (!box) return;
  box.innerHTML = (notes || []).map(function (note) {
    return '<li>' + statsEscapeHtml(note) + '</li>';
  }).join('');
}

function renderStatistics(payload) {
  STATISTICS_STATE.lastPayload = payload;
  var overview = payload.overview || {};
  statsSetText('statsDetectionTasks', statsFormatNumber(overview.detection_tasks));
  statsSetText('statsProcessedItems', statsFormatNumber(overview.processed_items));
  statsSetText('statsHitItems', statsFormatNumber(overview.hit_items));
  statsSetText('statsHitRate', statsFormatPercent(overview.hit_rate));
  statsSetText('statsDispatchQueue', statsFormatNumber(overview.dispatch_queue_total));
  statsSetText('statsDispatchPeople', statsFormatNumber(overview.dispatch_person_count));
  statsSetText('statsDispatchRecords', statsFormatNumber(overview.dispatch_records_total));
  statsSetText('statsSmsRecords', statsFormatNumber(overview.sms_records_total));
  statsSetText('statsGangCount', statsFormatNumber(overview.gang_count));
  statsSetText('statsGangMembers', statsFormatNumber(overview.gang_member_count));
  statsSetText('statsPeriodText', (payload.period || {}).start + ' 至 ' + (payload.period || {}).end);
  statsSetText('statsRefreshTime', '刷新：' + statsFormatTs(payload.generated_ts));

  var detection = payload.detection || {};
  var dispatch = payload.dispatch || {};
  var gang = payload.gang || {};
  statsRenderDistribution('statsByStatus', detection.by_status || [], 'status', 'count');
  statsRenderDistribution('statsByModel', detection.by_model || [], 'model_key', 'count');
  statsRenderDistribution('statsDispatchStatus', dispatch.queue_by_dispatch_status || [], 'status', 'count');
  statsRenderDistribution('statsSmsStatus', dispatch.queue_by_sms_status || [], 'status', 'count');
  statsRenderDistribution('statsGangTop', gang.top_gangs || [], 'gang_id', 'member_count');
  statsRenderRecentJobs(detection.recent_jobs || []);
  statsRenderNotes(payload.notes || []);
}

function refreshStatistics(btn) {
  if (btn) btn.disabled = true;
  return fetch('/statistics/api/overview?' + statsParams().toString())
    .then(function (resp) {
      return resp.json().then(function (payload) {
        payload.__http_ok = resp.ok;
        return payload;
      });
    })
    .then(function (payload) {
      if (!payload.ok || payload.__http_ok === false) throw new Error(payload.error || '态势统计加载失败');
      renderStatistics(payload);
    })
    .catch(function (error) {
      var box = document.getElementById('statsError');
      if (box) {
        box.classList.remove('hidden');
        box.textContent = error.message || '态势统计加载失败';
      }
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function generateStatisticsReport(btn) {
  if (btn) btn.disabled = true;
  var payload = {
    title: '猎影哨兵态势统计报告',
    report_type: 'custom',
    start: (document.getElementById('statsStart') || {}).value || '',
    end: (document.getElementById('statsEnd') || {}).value || ''
  };
  return fetch('/statistics/api/reports/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) throw new Error(data.error || '生成报告失败');
      var box = document.getElementById('statsReportResult');
      if (box) {
        box.classList.remove('hidden');
        box.textContent = '已生成报告：' + data.report_id;
      }
    })
    .catch(function (error) {
      alert(error.message || '生成报告失败');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

window.addEventListener('load', function () {
  refreshStatistics();
});

