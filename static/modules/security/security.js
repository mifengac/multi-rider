function securityEscapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function securityFormatTs(ts) {
  var n = Number(ts || 0);
  if (!n) return '--';
  return new Date(n * 1000).toLocaleString('zh-CN', { hour12: false });
}

function refreshSecurityMe() {
  return fetch('/security/api/me')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      if (!payload.ok) return;
      var user = payload.user || {};
      var box = document.getElementById('securityCurrentUser');
      if (box) {
        box.innerHTML =
          '<div class="font-semibold text-slate-900">' + securityEscapeHtml(user.display_name || user.username || '--') + '</div>' +
          '<div class="mt-1 text-xs text-slate-500">' + securityEscapeHtml(user.org_name || '') + ' · ' + securityEscapeHtml((user.roles || []).join(', ')) + '</div>';
      }
      var perm = document.getElementById('securityPermissions');
      if (perm) {
        perm.innerHTML = (user.permissions || []).map(function (item) {
          return '<span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">' + securityEscapeHtml(item) + '</span>';
        }).join('');
      }
    });
}

function refreshAuditLogs(btn) {
  if (btn) btn.disabled = true;
  var params = new URLSearchParams();
  ['module_code', 'action_code', 'username'].forEach(function (name) {
    var el = document.getElementById('audit_' + name);
    if (el && el.value) params.set(name, el.value);
  });
  params.set('limit', '100');
  return fetch('/security/api/audit-logs?' + params.toString())
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      if (!payload.ok) throw new Error(payload.error || '审计日志加载失败');
      renderAuditRows(payload.items || []);
    })
    .catch(function (error) {
      renderAuditError(error.message || '审计日志加载失败');
    })
    .finally(function () {
      if (btn) btn.disabled = false;
    });
}

function renderAuditRows(items) {
  var body = document.getElementById('securityAuditRows');
  if (!body) return;
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-sm text-slate-500">暂无审计记录</td></tr>';
    return;
  }
  body.innerHTML = items.map(function (item) {
    return (
      '<tr class="border-b border-slate-100 align-top">' +
        '<td class="px-4 py-3 text-xs text-slate-500">' + securityEscapeHtml(securityFormatTs(item.created_ts)) + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-700">' + securityEscapeHtml(item.display_name || item.username || '--') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-700">' + securityEscapeHtml(item.module_code || '') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-700">' + securityEscapeHtml(item.action_code || '') + '</td>' +
        '<td class="px-4 py-3 text-xs text-slate-700">' + securityEscapeHtml(item.result_status || '') + '</td>' +
        '<td class="px-4 py-3 font-mono text-xs text-slate-500">' + securityEscapeHtml(item.request_method || '') + ' ' + securityEscapeHtml(item.request_path || '') + '</td>' +
        '<td class="px-4 py-3 text-xs text-rose-600">' + securityEscapeHtml(item.error_msg || '') + '</td>' +
      '</tr>'
    );
  }).join('');
}

function renderAuditError(message) {
  var body = document.getElementById('securityAuditRows');
  if (body) {
    body.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-sm text-rose-600">' + securityEscapeHtml(message) + '</td></tr>';
  }
}

function refreshSensitiveAccess() {
  return fetch('/security/api/sensitive-access?limit=50')
    .then(function (resp) { return resp.json(); })
    .then(function (payload) {
      var box = document.getElementById('securitySensitiveRows');
      if (!box) return;
      var rows = payload.items || [];
      if (!rows.length) {
        box.innerHTML = '<div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">暂无敏感字段访问记录</div>';
        return;
      }
      box.innerHTML = rows.map(function (item) {
        return (
          '<div class="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">' +
            '<div class="font-semibold text-slate-800">' + securityEscapeHtml(item.username || '--') + ' · ' + securityEscapeHtml(item.field_codes || '') + '</div>' +
            '<div class="mt-1 text-xs text-slate-500">' + securityEscapeHtml(securityFormatTs(item.created_ts)) + ' · ' + securityEscapeHtml(item.purpose || '') + '</div>' +
          '</div>'
        );
      }).join('');
    });
}

window.addEventListener('load', function () {
  refreshSecurityMe();
  refreshAuditLogs();
  refreshSensitiveAccess();
});

