(function () {
  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showError(message, title = '错误') {
    const html = `
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-ui-error>
        <div class="bg-white rounded-lg shadow-lg p-6 max-w-sm mx-4">
          <h3 class="text-lg font-bold text-red-600 mb-2">${escapeHtml(title)}</h3>
          <p class="text-sm text-slate-600 mb-4">${escapeHtml(message)}</p>
          <button type="button"
                  data-ui-error-close
                  class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
            关闭
          </button>
        </div>
      </div>
    `;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html.trim();
    const modal = wrapper.firstElementChild;
    document.body.appendChild(modal);
    const close = modal && modal.querySelector('[data-ui-error-close]');
    if (close) close.addEventListener('click', () => modal.remove());
  }

  function showLoading(text = '加载中...') {
    hideLoading();
    const html = `
      <div id="loading-spinner" class="fixed inset-0 bg-black/30 flex items-center justify-center z-40">
        <div class="text-center">
          <div class="animate-spin w-12 h-12 border-4 border-white border-t-blue-500 rounded-full mx-auto mb-2"></div>
          <p class="text-white text-sm">${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
  }

  function hideLoading() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.remove();
  }

  window.AppUI = Object.assign(window.AppUI || {}, {
    showError,
    showLoading,
    hideLoading
  });
  window.showError = showError;
  window.showLoading = showLoading;
  window.hideLoading = hideLoading;
})();
