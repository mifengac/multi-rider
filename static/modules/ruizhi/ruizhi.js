const RUIZHI_STATE = {
  sessionId: '',
  kbNames: []
};

function rzEscapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function rzFormatTs(ts) {
  var n = Number(ts || 0);
  if (!n) return '--';
  return new Date(n * 1000).toLocaleString('zh-CN', { hour12: false });
}

function rzSetText(id, value) {
  var el = document.getElementById(id);
  if (el) el.textContent = value;
}

function rzSetJson(id, value) {
  var el = document.getElementById(id);
  if (el) el.textContent = JSON.stringify(value || {}, null, 2);
}

function rzRenderAlert(id, message, tone) {
  var el = document.getElementById(id);
  if (!el) return;
  if (!message) {
    el.classList.add('hidden');
    el.textContent = '';
    return;
  }
  var classes = {
    error: 'mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700',
    ok: 'mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700',
    warn: 'mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800'
  };
  el.className = classes[tone] || classes.warn;
  el.textContent = message;
}

function refreshRuizhiStatus() {
  return fetch('/ruizhi/api/status')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      var config = payload.config || {};
      rzSetText('rzStatusText', payload.status || '--');
      rzSetText('rzBaseUrl', config.base_url || '--');
      rzSetText('rzProject', config.project || '未配置');
      rzSetText('rzVerifySsl', String(config.verify_ssl));
      rzSetText('rzChatModel', (payload.defaults || {}).chat_model || '--');
      rzRenderAlert(
        'rzStatusAlert',
        config.configured ? '锐智 AI 已配置，可尝试刷新模型或发起会话。' : '锐智 AI 未启用或未配置 API Key，页面将保持可用但不会真实调用平台。',
        config.configured ? 'ok' : 'warn'
      );
    });
}

function refreshRuizhiModels(btn) {
  if (btn) btn.disabled = true;
  return fetch('/ruizhi/api/models')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      rzSetJson('rzModelsJson', payload);
      if (!payload.ok) {
        rzRenderAlert('rzModelsAlert', payload.error || '模型列表获取失败', 'error');
      } else {
        rzRenderAlert('rzModelsAlert', '模型列表已刷新。', 'ok');
      }
    })
    .catch(function (error) {
      rzRenderAlert('rzModelsAlert', error.message || '模型列表获取失败', 'error');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function appendChatMessage(role, text, docsRefs) {
  var box = document.getElementById('rzChatMessages');
  if (!box) return;
  var isUser = role === 'user';
  var docs = (docsRefs || []).length
    ? '<div class="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">引用：' + rzEscapeHtml((docsRefs || []).join('\n\n').slice(0, 1200)) + '</div>'
    : '';
  box.insertAdjacentHTML(
    'beforeend',
    '<div class="flex ' + (isUser ? 'justify-end' : 'justify-start') + '">' +
      '<div class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-7 ' + (isUser ? 'bg-slate-900 text-white' : 'bg-white border border-slate-200 text-slate-800') + '">' +
        '<div class="mb-1 text-[10px] font-bold uppercase tracking-widest ' + (isUser ? 'text-slate-300' : 'text-[#c96442]') + '">' + rzEscapeHtml(role) + '</div>' +
        '<div class="whitespace-pre-wrap">' + rzEscapeHtml(text || '') + '</div>' +
        docs +
      '</div>' +
    '</div>'
  );
  box.scrollTop = box.scrollHeight;
}

function sendRuizhiChat(btn) {
  var input = document.getElementById('rzChatInput');
  var scenario = document.getElementById('rzScenario');
  var kbNames = document.getElementById('rzChatKbNames');
  var message = (input && input.value || '').trim();
  if (!message) return false;
  appendChatMessage('user', message);
  if (input) input.value = '';
  if (btn) btn.disabled = true;
  var payload = {
    message: message,
    scenario_code: scenario && scenario.value || 'general',
    session_id: RUIZHI_STATE.sessionId || '',
    kb_names: (kbNames && kbNames.value || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean)
  };
  return fetch('/ruizhi/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) throw new Error(data.error || 'AI 会话失败');
      RUIZHI_STATE.sessionId = data.session_id || RUIZHI_STATE.sessionId;
      rzSetText('rzCurrentSession', RUIZHI_STATE.sessionId || '--');
      appendChatMessage('assistant', data.message || '', data.docs_refs || []);
      refreshRuizhiSessions();
      refreshRuizhiLogs();
    })
    .catch(function (error) {
      appendChatMessage('assistant', '调用失败：' + (error.message || '未知错误'));
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function refreshRuizhiSessions() {
  return fetch('/ruizhi/api/sessions?limit=20')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      var box = document.getElementById('rzSessionList');
      if (!box) return;
      var items = payload.items || [];
      if (!items.length) {
        box.innerHTML = '<div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">暂无会话</div>';
        return;
      }
      box.innerHTML = items.map(function (item) {
        return (
          '<button type="button" class="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm hover:bg-slate-50" onclick="loadRuizhiSession(\'' + rzEscapeHtml(item.id) + '\')">' +
            '<div class="font-semibold text-slate-800">' + rzEscapeHtml(item.title || 'AI 研判会话') + '</div>' +
            '<div class="mt-1 text-xs text-slate-500">' + rzEscapeHtml(item.scenario_code || '') + ' · ' + rzEscapeHtml(rzFormatTs(item.updated_ts)) + '</div>' +
          '</button>'
        );
      }).join('');
    });
}

function loadRuizhiSession(sessionId) {
  return fetch('/ruizhi/api/sessions/' + encodeURIComponent(sessionId))
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      if (!payload.ok) throw new Error(payload.error || '加载会话失败');
      RUIZHI_STATE.sessionId = sessionId;
      rzSetText('rzCurrentSession', sessionId);
      var box = document.getElementById('rzChatMessages');
      if (box) box.innerHTML = '';
      (payload.messages || []).forEach(function (msg) {
        appendChatMessage(msg.role, msg.content_text, msg.docs_ref || []);
      });
    })
    .catch(function (error) {
      alert(error.message || '加载会话失败');
    });
}

function createRuizhiKb(btn) {
  var name = (document.getElementById('rzKbName') || {}).value || '';
  var desc = (document.getElementById('rzKbDesc') || {}).value || '';
  if (!name.trim()) {
    rzRenderAlert('rzKbAlert', '请填写知识库名称。', 'error');
    return false;
  }
  if (btn) btn.disabled = true;
  return fetch('/ruizhi/api/kbs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name.trim(), description: desc.trim() })
  })
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      if (!payload.ok) throw new Error(payload.error || '创建知识库失败');
      rzRenderAlert('rzKbAlert', '知识库创建请求已提交。', 'ok');
      refreshRuizhiKbs();
      refreshRuizhiLogs();
    })
    .catch(function (error) {
      rzRenderAlert('rzKbAlert', error.message || '创建知识库失败', 'error');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function uploadRuizhiKbFile(btn) {
  var kbName = (document.getElementById('rzUploadKbName') || {}).value || '';
  var fileInput = document.getElementById('rzKbFile');
  if (!kbName.trim() || !fileInput || !fileInput.files.length) {
    rzRenderAlert('rzKbAlert', '请填写知识库名称并选择文件。', 'error');
    return false;
  }
  var form = new FormData();
  form.append('file', fileInput.files[0]);
  form.append('purpose', 'kbs');
  if (btn) btn.disabled = true;
  return fetch('/ruizhi/api/kbs/' + encodeURIComponent(kbName.trim()) + '/files', {
    method: 'POST',
    body: form
  })
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      if (!payload.ok) throw new Error(payload.error || ((payload.association || {}).error) || '上传关联失败');
      rzRenderAlert('rzKbAlert', '文件已上传并提交知识库解析。', 'ok');
      refreshRuizhiKbs();
      refreshRuizhiLogs();
    })
    .catch(function (error) {
      rzRenderAlert('rzKbAlert', error.message || '上传关联失败', 'error');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function refreshRuizhiKbs() {
  return fetch('/ruizhi/api/kbs')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      var box = document.getElementById('rzKbList');
      if (!box) return;
      var items = payload.local_items || [];
      if (!items.length) {
        box.innerHTML = '<div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">暂无本地知识库映射</div>';
      } else {
        box.innerHTML = items.map(function (item) {
          return '<div class="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm"><div class="font-semibold">' + rzEscapeHtml(item.display_name || item.kb_name) + '</div><div class="mt-1 text-xs text-slate-500">' + rzEscapeHtml(item.kb_name) + ' · ' + rzEscapeHtml(item.status || '') + '</div></div>';
        }).join('');
      }
      rzSetJson('rzKbRemoteJson', payload.remote || { note: payload.remote_error || '未获取远端知识库列表' });
    });
}

function runRuizhiOcr(btn) {
  var fileInput = document.getElementById('rzOcrFile');
  var engine = document.getElementById('rzOcrEngine');
  if (!fileInput || !fileInput.files.length) {
    rzRenderAlert('rzOcrAlert', '请选择图片。', 'error');
    return false;
  }
  var form = new FormData();
  form.append('image', fileInput.files[0]);
  form.append('engine', engine && engine.value || 'paddle');
  if (btn) btn.disabled = true;
  return fetch('/ruizhi/api/ocr', { method: 'POST', body: form })
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      rzSetJson('rzOcrResult', payload);
      if (!payload.ok) throw new Error(payload.error || 'OCR 失败');
      rzRenderAlert('rzOcrAlert', 'OCR 已完成。', 'ok');
      refreshRuizhiLogs();
    })
    .catch(function (error) {
      rzRenderAlert('rzOcrAlert', error.message || 'OCR 失败', 'error');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function refreshRuizhiLogs() {
  return fetch('/ruizhi/api/call-logs?limit=80')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      var body = document.getElementById('rzCallLogRows');
      if (!body) return;
      var rows = payload.items || [];
      if (!rows.length) {
        body.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-sm text-slate-500">暂无调用日志</td></tr>';
        return;
      }
      body.innerHTML = rows.map(function (item) {
        return (
          '<tr class="border-b border-slate-100 align-top">' +
            '<td class="px-4 py-3 text-xs text-slate-500">' + rzEscapeHtml(rzFormatTs(item.created_ts)) + '</td>' +
            '<td class="px-4 py-3 text-xs text-slate-700">' + rzEscapeHtml(item.module_code || '') + '</td>' +
            '<td class="px-4 py-3 text-xs text-slate-700">' + rzEscapeHtml(item.operation || '') + '</td>' +
            '<td class="px-4 py-3 text-xs text-slate-700">' + rzEscapeHtml(item.model_name || '') + '</td>' +
            '<td class="px-4 py-3 text-xs ' + (item.success ? 'text-emerald-700' : 'text-rose-600') + '">' + (item.success ? '成功' : '失败') + '</td>' +
            '<td class="px-4 py-3 text-xs text-slate-500">' + rzEscapeHtml(item.elapsed_ms || 0) + 'ms</td>' +
            '<td class="px-4 py-3 text-xs text-rose-600">' + rzEscapeHtml(item.error_msg || '') + '</td>' +
          '</tr>'
        );
      }).join('');
    });
}

function generateRuizhiReport(btn) {
  var sourceText = (document.getElementById('rzReportSource') || {}).value || '{}';
  var source = {};
  try {
    source = JSON.parse(sourceText || '{}');
  } catch (e) {
    rzRenderAlert('rzReportAlert', '报告上下文必须是 JSON。', 'error');
    return false;
  }
  if (btn) btn.disabled = true;
  return fetch('/ruizhi/api/reports/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report_type: 'clue', source: source })
  })
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      rzSetJson('rzReportResult', payload);
      if (!payload.ok) throw new Error(payload.error || '生成报告失败');
      rzRenderAlert('rzReportAlert', '报告草稿已生成。', 'ok');
      refreshRuizhiLogs();
    })
    .catch(function (error) {
      rzRenderAlert('rzReportAlert', error.message || '生成报告失败', 'error');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

window.addEventListener('load', function () {
  refreshRuizhiStatus();
  refreshRuizhiSessions();
  refreshRuizhiKbs();
  refreshRuizhiLogs();
});

