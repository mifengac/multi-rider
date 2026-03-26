    const APP_CONFIG = window.INDEX_PAGE_BOOTSTRAP || {};
    const APP_URLS = APP_CONFIG.urls || {};

    const MODEL_UI = {
      bczj: {
        label: '类别过滤',
        placeholder: '0,1,2 或类别名',
        help: '按索引或类别名过滤飙车炸街模型结果；留空表示不过滤。',
        uploadDefaultConf: 0.80,
        presets: []
      },
      general: {
        label: '检测提示词',
        placeholder: 'person, motorcycle, bicycle, car, bus, truck',
        help: '英文逗号分隔。本地上传检测建议优先使用交通场景提示词组合，以提高 YOLOE 命中率。',
        uploadDefaultConf: 0.10,
        presets: [
          { label: '交通场景', value: 'person,motorcycle,bicycle,car,bus,truck' },
          { label: '摩托车', value: 'motorcycle' },
          { label: '未戴头盔', value: 'motorcycle, person, helmet' },
          { label: '人员', value: 'person' }
        ]
      }
    };

    const UPLOAD_MODEL_OPTIONS = Array.isArray(APP_CONFIG.uploadModels) ? APP_CONFIG.uploadModels : [];
    const UPLOAD_MODEL_MAP = Object.fromEntries(
      UPLOAD_MODEL_OPTIONS.map(function (item) {
        return [item.value, item];
      })
    );
    const UPLOAD_PROMPT_UI = {
      label: '检测提示词',
      placeholder: 'person, motorcycle, bicycle, car, bus, truck',
      help: '英文逗号分隔。开放词表模型可直接输入要检测的英文提示词。',
      uploadDefaultConf: 0.10,
      defaultClasses: 'person,motorcycle,bicycle,car,bus,truck',
      presets: [
        { label: '交通场景', value: 'person,motorcycle,bicycle,car,bus,truck' },
        { label: '反光衣人员', value: 'person wearing reflective vest,worker in reflective vest,traffic police in reflective vest' },
        { label: '摩托车', value: 'motorcycle' },
        { label: '人员', value: 'person' }
      ]
    };
    const UPLOAD_FILTER_UI = {
      label: '类别过滤',
      placeholder: '0,1,2 或类别名',
      help: '自定义模型使用类别索引或类别名过滤，留空表示不过滤。',
      uploadDefaultConf: 0.80,
      defaultClasses: '',
      presets: []
    };

    const STATUS_UI = {
      running: { label: '运行中', badge: 'bg-sky-100 text-sky-700 ring-sky-200', bar: 'bg-sky-500' },
      done: { label: '已完成', badge: 'bg-emerald-100 text-emerald-700 ring-emerald-200', bar: 'bg-emerald-500' },
      error: { label: '失败', badge: 'bg-rose-100 text-rose-700 ring-rose-200', bar: 'bg-rose-500' },
      canceled: { label: '已取消', badge: 'bg-slate-200 text-slate-700 ring-slate-300', bar: 'bg-slate-500' },
      interrupted: { label: '已中断', badge: 'bg-amber-100 text-amber-700 ring-amber-200', bar: 'bg-amber-500' }
    };

    function modelDisplay(modelKey) {
      if (UPLOAD_MODEL_MAP[modelKey] && UPLOAD_MODEL_MAP[modelKey].short_label) {
        return UPLOAD_MODEL_MAP[modelKey].short_label;
      }
      return modelKey === 'bczj' ? '飙车炸街' : '通用';
    }

    function statusMeta(status) {
      return STATUS_UI[status] || STATUS_UI.running;
    }

    function checkAllHours(checked) {
      document.querySelectorAll('input[name="hours"]').forEach(function (box) {
        box.checked = checked;
      });
    }

    function syncConfValue() {
      const range = document.getElementById('confRange');
      const value = document.getElementById('confValue');
      value.textContent = Number(range.value).toFixed(2);
    }

    function applyModelUI() {
      const modelKey = document.getElementById('model_key').value;
      const config = MODEL_UI[modelKey] || MODEL_UI.general;
      const label = document.getElementById('classesLabel');
      const input = document.getElementById('classes');
      const help = document.getElementById('classesHelp');
      const panel = document.getElementById('presetPanel');
      const box = document.getElementById('presetButtons');

      label.textContent = config.label;
      input.placeholder = config.placeholder;
      input.disabled = false;
      help.textContent = config.help;

      if (config.presets.length === 0) {
        panel.classList.add('hidden');
        box.innerHTML = '';
        return;
      }

      panel.classList.remove('hidden');
      box.innerHTML = config.presets.map(function (preset) {
        return '<button type="button" class="rounded-full border border-teal-200 bg-white px-3 py-1 text-xs font-medium text-teal-700 transition hover:border-teal-400 hover:bg-teal-50" data-value="' + preset.value + '">' + preset.label + '</button>';
      }).join('');

      box.querySelectorAll('button[data-value]').forEach(function (button) {
        button.addEventListener('click', function () {
          input.value = button.getAttribute('data-value') || '';
          input.focus();
        });
      });
    }

    function getUploadModelConfig(modelKey) {
      var meta = UPLOAD_MODEL_MAP[modelKey] || null;
      var base = meta && meta.ui_mode === 'filter' ? UPLOAD_FILTER_UI : UPLOAD_PROMPT_UI;
      return {
        label: base.label,
        placeholder: base.placeholder,
        help: meta && meta.description ? meta.description : base.help,
        uploadDefaultConf: meta && typeof meta.default_conf === 'number' ? meta.default_conf : base.uploadDefaultConf,
        defaultClasses: meta && meta.default_classes ? meta.default_classes : base.defaultClasses,
        presets: base.presets || [],
        uiMode: meta && meta.ui_mode ? meta.ui_mode : 'prompt'
      };
    }

    function formatPercent(processed, total) {
      if (!total) return 0;
      return Math.min(100, Math.max(0, Math.floor(processed * 100 / total)));
    }

    function setProgressState(job) {
      const processed = job.processed || 0;
      const total = job.total || 0;
      const kept = job.kept || 0;
      const notfound = job.notfound || 0;
      const failed = job.failed || 0;
      const pct = formatPercent(processed, total);
      const meta = statusMeta(job.status || 'running');

      document.getElementById('progressText').textContent = '已处理 ' + processed + ' / ' + total;
      document.getElementById('progressSubtext').textContent =
        '模型：' + modelDisplay(job.model_key || 'general') + ' · 保留 ' + kept + ' · 404 ' + notfound + ' · 失败 ' + failed;

      const bar = document.getElementById('progressBar');
      bar.style.width = pct + '%';
      bar.className = 'h-3 rounded-full transition-all duration-300 ' + meta.bar;

      const badge = document.getElementById('progressStatus');
      badge.textContent = meta.label;
      badge.className = 'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge;
    }

    function clearLastJob() {
      try {
        localStorage.removeItem('bczj_last_job');
      } catch (e) {}
    }

    function cancelJob(jobId) {
      if (!jobId) return;
      fetch((APP_URLS.cancelJob || '').replace('__J__', jobId), { method: 'POST' })
        .finally(function () {
          refreshJobs();
        });
    }

    function cancelCurrent() {
      let jobId = null;
      try {
        jobId = localStorage.getItem('bczj_last_job');
      } catch (e) {}
      if (!jobId) {
        alert('当前没有可取消的任务');
        return;
      }
      cancelJob(jobId);
    }

    function renderRunningJobs(items) {
      const box = document.getElementById('jobsInfo');
      if (!items || items.length === 0) {
        box.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-5 text-sm text-slate-500">当前没有运行中的任务。</div>';
        return;
      }

      box.innerHTML = items.map(function (job) {
        const pct = formatPercent(job.processed || 0, job.total || 0);
        const meta = statusMeta(job.status || 'running');
        return (
          '<div class="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm shadow-slate-200/60">' +
            '<div class="flex items-start justify-between gap-3">' +
              '<div>' +
                '<div class="text-xs uppercase tracking-[0.25em] text-slate-400">JOB</div>' +
                '<div class="mt-1 break-all font-mono text-xs text-slate-600">' + (job.id || '') + '</div>' +
              '</div>' +
              '<div class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge + '">' + meta.label + '</div>' +
            '</div>' +
            '<div class="mt-3 flex items-center justify-between text-sm text-slate-600">' +
              '<span>模型：' + modelDisplay(job.model_key || 'general') + '</span>' +
              '<span>' + (job.processed || 0) + '/' + (job.total || 0) + ' · ' + pct + '%</span>' +
            '</div>' +
            '<div class="mt-3 h-2 rounded-full bg-slate-100">' +
              '<div class="h-2 rounded-full ' + meta.bar + '" style="width:' + pct + '%"></div>' +
            '</div>' +
            '<div class="mt-4 flex justify-end">' +
              '<button type="button" class="rounded-full bg-rose-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-rose-600" onclick="cancelJob(\'' + (job.id || '') + '\')">停止任务</button>' +
            '</div>' +
          '</div>'
        );
      }).join('');
    }

    function refreshJobs() {
      fetch(APP_URLS.listJobs || '/jobs')
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          document.getElementById('runningCount').textContent = data.running_count || 0;
          renderRunningJobs(data.running || []);
        })
        .catch(function () {})
        .finally(function () {
          window.setTimeout(refreshJobs, 3000);
        });
    }

    function poll(jobId) {
      fetch((APP_URLS.jobProgress || '').replace('__J__', jobId))
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          const job = data.job || {};
          document.getElementById('progressBox').classList.remove('hidden');
          setProgressState(job);

          if (job.status === 'done') {
            const zipUrl = (APP_URLS.downloadZip || '').replace('__J__', jobId);
            const summaryUrl = (APP_URLS.downloadSummary || '').replace('__J__', jobId);
            document.getElementById('downloadLinks').classList.remove('hidden');
            document.getElementById('zipLink').href = zipUrl;
            document.getElementById('sumLink').href = summaryUrl;
            clearLastJob();
            loadResultGallery('oracle', jobId);
          } else if (job.status === 'canceled') {
            clearLastJob();
            alert('任务已取消');
          } else if (job.status === 'interrupted') {
            clearLastJob();
            alert('任务因服务重启而中断');
          } else if (job.status === 'error') {
            clearLastJob();
            alert('任务失败：' + (job.message || '未知错误'));
          } else {
            window.setTimeout(function () { poll(jobId); }, 1000);
          }
        })
        .catch(function () {
          window.setTimeout(function () { poll(jobId); }, 1500);
        });
    }

    function startJob(event) {
      if (event) event.preventDefault();
      const form = document.getElementById('jobForm');
      const data = new FormData(form);

      fetch(APP_URLS.startJob || '/start', {
        method: 'POST',
        body: data
      })
        .then(function (resp) { return resp.json(); })
        .then(function (payload) {
          if (!payload.ok) {
            alert(payload.error || '启动任务失败');
            return;
          }
          const jobId = payload.job_id;
          try {
            localStorage.setItem('bczj_last_job', jobId);
          } catch (e) {}
          document.getElementById('progressBox').classList.remove('hidden');
          document.getElementById('downloadLinks').classList.add('hidden');
          resetResultState('oracle');
          setProgressState({
            status: 'running',
            model_key: document.getElementById('model_key').value,
            total: payload.total || 0,
            processed: 0,
            kept: 0,
            notfound: 0,
            failed: 0
          });
          poll(jobId);
        })
        .catch(function () {
          alert('网络错误，任务未启动');
        });
      return false;
    }

    // ==================== UPLOAD TAB ====================

    function switchTab(tab) {
      var panels = {
        Oracle: document.getElementById('tabOracle'),
        Upload: document.getElementById('tabUpload'),
        Train: document.getElementById('tabTrain'),
        Dispatch: document.getElementById('tabDispatch'),
        Face: document.getElementById('tabFace')
      };
      var buttons = {
        Oracle: document.getElementById('tabBtnOracle'),
        Upload: document.getElementById('tabBtnUpload'),
        Train: document.getElementById('tabBtnTrain'),
        Dispatch: document.getElementById('tabBtnDispatch'),
        Face: document.getElementById('tabBtnFace')
      };
      Object.keys(panels).forEach(function (key) {
        if (panels[key]) panels[key].classList.add('hidden');
        if (buttons[key]) {
          buttons[key].classList.remove('bg-slate-900', 'text-white');
          buttons[key].classList.add('bg-white', 'text-slate-600', 'ring-1', 'ring-inset', 'ring-slate-200');
        }
      });
      if (panels[tab]) panels[tab].classList.remove('hidden');
      if (buttons[tab]) {
        buttons[tab].classList.add('bg-slate-900', 'text-white');
        buttons[tab].classList.remove('bg-white', 'text-slate-600', 'ring-1', 'ring-inset', 'ring-slate-200');
      }
      if (tab === 'Face') {
        refreshFaceTab();
      } else if (tab === 'Train') {
        refreshTrainTab();
      } else if (tab === 'Dispatch' && typeof refreshDispatchTab === 'function') {
        refreshDispatchTab();
      }
      try { localStorage.setItem('bczj_active_tab', tab); } catch (e) {}
    }

    function populateUploadModelSelect() {
      var select = document.getElementById('uploadModelKey');
      if (!select) return;
      if (!UPLOAD_MODEL_OPTIONS.length) {
        select.innerHTML = '<option value="" selected>未发现可用模型</option>';
        select.disabled = true;
        return;
      }
      select.disabled = false;
      select.innerHTML = UPLOAD_MODEL_OPTIONS.map(function (item) {
        return '<option value="' + item.value + '">' + item.label + '</option>';
      }).join('');
      var defaultValue = APP_CONFIG.uploadModelDefault || '';
      if (defaultValue && UPLOAD_MODEL_MAP[defaultValue]) {
        select.value = defaultValue;
      }
      if (!select.value && UPLOAD_MODEL_OPTIONS[0]) {
        select.value = UPLOAD_MODEL_OPTIONS[0].value;
      }
    }

    function applyUploadModelUI() {
      var modelKey = document.getElementById('uploadModelKey').value;
      var meta = UPLOAD_MODEL_MAP[modelKey] || null;
      var config = getUploadModelConfig(modelKey);
      var label = document.getElementById('uploadClassesLabel');
      var input = document.getElementById('uploadClasses');
      var help = document.getElementById('uploadClassesHelp');
      var modelHint = document.getElementById('uploadModelHint');
      if (!modelHint) {
        modelHint = document.createElement('p');
        modelHint.id = 'uploadModelHint';
        modelHint.className = 'mt-2 text-xs leading-6 text-slate-500';
        document.getElementById('uploadModelKey').insertAdjacentElement('afterend', modelHint);
      }
      var panel = document.getElementById('uploadPresetPanel');
      var box = document.getElementById('uploadPresetButtons');
      var confRange = document.getElementById('uploadConfRange');
      var confValue = document.getElementById('uploadConfValue');
      var previousMode = input.dataset.uiMode || '';
      var nextMode = config.uiMode || 'prompt';
      label.textContent = config.label;
      input.placeholder = config.placeholder;
      help.textContent = config.help;
      if (modelHint) {
        modelHint.textContent = meta && meta.description ? meta.description : '';
      }
      confRange.value = Number(config.uploadDefaultConf || 0.80).toFixed(2);
      confValue.textContent = confRange.value;
      if (nextMode === 'prompt') {
        if (!input.value.trim() || previousMode !== 'prompt') {
          input.value = config.defaultClasses || '';
        }
      } else if (previousMode !== 'filter') {
        input.value = '';
      }
      input.dataset.uiMode = nextMode;
      if (config.presets.length === 0) {
        panel.classList.add('hidden');
        box.innerHTML = '';
        return;
      }
      panel.classList.remove('hidden');
      box.innerHTML = config.presets.map(function (preset) {
        return '<button type="button" class="rounded-full border border-teal-200 bg-white px-3 py-1 text-xs font-medium text-teal-700 transition hover:border-teal-400 hover:bg-teal-50" data-value="' + preset.value + '">' + preset.label + '</button>';
      }).join('');
      box.querySelectorAll('button[data-value]').forEach(function (button) {
        button.addEventListener('click', function () {
          input.value = button.getAttribute('data-value') || '';
          input.focus();
        });
      });
    }

    function syncUploadConfValue() {
      document.getElementById('uploadConfValue').textContent = Number(document.getElementById('uploadConfRange').value).toFixed(2);
    }

    function onUploadFileChange(input) {
      var file = input.files && input.files[0];
      if (!file) return;
      var ext = file.name.split('.').pop().toLowerCase();
      var isVideo = ['mp4', 'avi', 'mov', 'mkv', 'mpg', 'mpeg'].includes(ext);
      document.getElementById('uploadFileName').textContent = file.name;
      document.getElementById('uploadFileSize').textContent = (file.size / 1024 / 1024).toFixed(1) + ' MB';
      document.getElementById('uploadFileInfo').classList.remove('hidden');
      document.getElementById('frameIntervalRow').classList.toggle('hidden', !isVideo);
    }

    function setUploadProgressState(job) {
      var processed = job.processed || 0;
      var total = job.total || 0;
      var kept = job.kept || 0;
      var pct = total ? Math.min(100, Math.floor(processed * 100 / total)) : 0;
      var meta = statusMeta(job.status || 'running');
      document.getElementById('uploadProgressText').textContent = '已处理 ' + processed + ' / ' + total;
      document.getElementById('uploadProgressSubtext').textContent =
        '模型：' + modelDisplay(job.model_key || 'general') + ' · 保留 ' + kept;
      var bar = document.getElementById('uploadProgressBar');
      bar.style.width = pct + '%';
      bar.className = 'h-3 rounded-full transition-all duration-300 ' + meta.bar;
      var badge = document.getElementById('uploadProgressStatus');
      badge.textContent = meta.label;
      badge.className = 'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge;
    }

    function pollUpload(jobId) {
      fetch('/upload/progress/' + jobId)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          var job = data.job || {};
          document.getElementById('uploadProgressBox').classList.remove('hidden');
          setUploadProgressState(job);
          if (job.status === 'done') {
            document.getElementById('uploadDownloadLinks').classList.remove('hidden');
            document.getElementById('uploadZipLink').href = '/upload/download/' + jobId;
            try { localStorage.removeItem('bczj_upload_job'); } catch (e) {}
            loadResultGallery('upload', jobId);
          } else if (job.status === 'canceled') {
            try { localStorage.removeItem('bczj_upload_job'); } catch (e) {}
            alert('任务已取消');
          } else if (job.status === 'error') {
            try { localStorage.removeItem('bczj_upload_job'); } catch (e) {}
            alert('任务失败：' + (job.message || '未知错误'));
          } else {
            window.setTimeout(function () { pollUpload(jobId); }, 1000);
          }
        })
        .catch(function () { window.setTimeout(function () { pollUpload(jobId); }, 1500); });
    }

    function startUploadJob(event) {
      if (event) event.preventDefault();
      var fileInput = document.getElementById('uploadFile');
      var modelSelect = document.getElementById('uploadModelKey');
      if (!fileInput.files || !fileInput.files[0]) {
        alert('请先选择文件');
        return false;
      }
      if (!modelSelect || !modelSelect.value) {
        alert('未发现可用模型');
        return false;
      }
      var form = document.getElementById('uploadForm');
      var data = new FormData(form);
      document.getElementById('uploadProgressBox').classList.remove('hidden');
      document.getElementById('uploadDownloadLinks').classList.add('hidden');
      resetResultState('upload');
      setUploadProgressState({ status: 'running', total: 0, processed: 0, kept: 0, model_key: document.getElementById('uploadModelKey').value });
      fetch('/upload/start', { method: 'POST', body: data })
        .then(function (resp) {
          return resp.text().then(function (text) {
            var payload = {};
            try {
              payload = text ? JSON.parse(text) : {};
            } catch (e) {
              payload = {};
            }
            payload.__http_status = resp.status;
            payload.__http_ok = resp.ok;
            return payload;
          });
        })
        .then(function (payload) {
          if (!payload.ok || payload.__http_ok === false) {
            if (payload.__http_status === 413) {
              alert(payload.error || '上传文件过大，请压缩后重试或调大 MAX_UPLOAD_BYTES。');
              return;
            }
            alert(payload.error || ('启动失败，HTTP ' + (payload.__http_status || 'unknown')));
            return;
          }
          try { localStorage.setItem('bczj_upload_job', payload.job_id); } catch (e) {}
          pollUpload(payload.job_id);
        })
        .catch(function () { alert('网络错误，任务未启动'); });
      return false;
    }

    function cancelUploadJob() {
      var jobId = null;
      try { jobId = localStorage.getItem('bczj_upload_job'); } catch (e) {}
      if (!jobId) { alert('当前没有可取消的上传任务'); return; }
      fetch('/upload/cancel/' + jobId, { method: 'POST' }).catch(function () {});
    }


