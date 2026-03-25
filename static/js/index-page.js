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
        Face: document.getElementById('tabFace')
      };
      var buttons = {
        Oracle: document.getElementById('tabBtnOracle'),
        Upload: document.getElementById('tabBtnUpload'),
        Train: document.getElementById('tabBtnTrain'),
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

    const TRAIN_DATASET_STATE = { items: [], loading: false, importing: false };

    function setTrainDatasetFeedback(message, tone) {
      var box = document.getElementById('trainDatasetFeedback');
      if (!box) return;
      if (!message) {
        box.className = 'hidden';
        box.textContent = '';
        return;
      }
      box.textContent = message;
      box.className = 'rounded-2xl border px-4 py-3 text-sm';
      if (tone === 'error') {
        box.classList.add('border-rose-200', 'bg-rose-50', 'text-rose-700');
      } else {
        box.classList.add('border-emerald-200', 'bg-emerald-50', 'text-emerald-700');
      }
    }

    function setTrainImportFeedback(message, tone) {
      var box = document.getElementById('trainImportFeedback');
      if (!box) return;
      if (!message) {
        box.className = 'hidden';
        box.textContent = '';
        return;
      }
      box.textContent = message;
      box.className = 'rounded-2xl border px-4 py-3 text-sm';
      if (tone === 'error') {
        box.classList.add('border-rose-200', 'bg-rose-50', 'text-rose-700');
      } else {
        box.classList.add('border-emerald-200', 'bg-emerald-50', 'text-emerald-700');
      }
    }

    function renderTrainSummary(summary) {
      var data = summary || {};
      var metrics = {
        trainMetricDatasets: data.dataset_count || 0,
        trainMetricImages: data.image_count || 0,
        trainMetricLabeled: data.labeled_count || 0,
        trainMetricReviewed: data.reviewed_count || 0
      };
      Object.keys(metrics).forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.textContent = metrics[id];
      });
    }

    function renderTrainDatasetOptions(items) {
      var select = document.getElementById('trainImportDataset');
      var fileInput = document.getElementById('trainImportFile');
      var submitBtn = document.getElementById('trainImportSubmit');
      if (!select) return;

      var previousValue = select.value;
      var hasItems = !!(items && items.length);
      if (!hasItems) {
        select.innerHTML = '<option value="">请先创建数据集</option>';
        select.disabled = true;
        if (fileInput) {
          fileInput.disabled = true;
          fileInput.value = '';
        }
        if (submitBtn) submitBtn.disabled = true;
        return;
      }

      select.innerHTML = items.map(function (item) {
        return '<option value="' + escapeHtml(item.id || '') + '">' + escapeHtml(item.name || item.id || '') + '</option>';
      }).join('');

      var matched = items.some(function (item) {
        return item.id === previousValue;
      });
      if (matched) {
        select.value = previousValue;
      } else if (items[0]) {
        select.value = items[0].id;
      }

      select.disabled = false;
      if (fileInput) fileInput.disabled = false;
      if (submitBtn) submitBtn.disabled = TRAIN_DATASET_STATE.importing;
    }

    function renderTrainDatasets(items) {
      var box = document.getElementById('trainDatasetList');
      if (!box) return;
      if (!items || !items.length) {
        box.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-sm text-slate-500">暂无数据集。先创建一个数据集，再继续做 ZIP 导入、历史结果回流和标注。</div>';
        return;
      }

      box.innerHTML = items.map(function (item) {
        var classBadges = (item.class_names || []).map(function (name) {
          return '<span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">' + escapeHtml(name) + '</span>';
        }).join('');
        if (!classBadges) {
          classBadges = '<span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 ring-1 ring-inset ring-slate-200">未设置类别</span>';
        }

        var recentAssets = item.recent_assets || [];
        var previewGrid = recentAssets.map(function (asset) {
          var imageUrl = asset.asset_url || '#';
          var assetName = asset.origin_name || asset.filename || 'image';
          return (
            '<a href="' + escapeHtml(imageUrl) + '" target="_blank" rel="noreferrer" class="group overflow-hidden rounded-2xl border border-slate-200 bg-white transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-sm">' +
              '<div class="aspect-[4/3] overflow-hidden bg-slate-100">' +
                '<img src="' + escapeHtml(imageUrl) + '" alt="' + escapeHtml(assetName) + '" loading="lazy" class="h-full w-full object-cover transition duration-200 group-hover:scale-[1.02]" />' +
              '</div>' +
              '<div class="px-3 py-3">' +
                '<div class="truncate text-sm font-medium text-slate-800">' + escapeHtml(assetName) + '</div>' +
                '<div class="mt-1 text-xs text-slate-500">' + escapeHtml(asset.width || 0) + ' × ' + escapeHtml(asset.height || 0) + ' · ' + escapeHtml(formatBytes(asset.size_bytes || 0)) + '</div>' +
              '</div>' +
            '</a>'
          );
        }).join('');

        var updatedAt = item.updated_ts ? new Date(item.updated_ts * 1000).toLocaleString('zh-CN') : '--';
        return (
          '<div class="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-200/60">' +
            '<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">' +
              '<div class="min-w-0 flex-1">' +
                '<div class="flex flex-wrap items-center gap-2">' +
                  '<div class="truncate text-base font-semibold text-slate-900">' + escapeHtml(item.name || item.id || '') + '</div>' +
                  '<span class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">' + escapeHtml(item.status || 'draft') + '</span>' +
                '</div>' +
                '<div class="mt-2 break-all font-mono text-xs text-slate-400">' + escapeHtml(item.id || '') + '</div>' +
                '<div class="mt-3 flex flex-wrap gap-2">' + classBadges + '</div>' +
              '</div>' +
              '<div class="grid min-w-[260px] grid-cols-2 gap-3 text-sm">' +
                '<div class="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3"><div class="text-xs text-slate-400">图片数</div><div class="mt-1 font-semibold text-slate-800">' + escapeHtml(item.image_count || 0) + '</div></div>' +
                '<div class="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3"><div class="text-xs text-slate-400">已标注</div><div class="mt-1 font-semibold text-slate-800">' + escapeHtml(item.labeled_count || 0) + '</div></div>' +
                '<div class="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3"><div class="text-xs text-slate-400">已复核</div><div class="mt-1 font-semibold text-slate-800">' + escapeHtml(item.reviewed_count || 0) + '</div></div>' +
                '<div class="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3"><div class="text-xs text-slate-400">版本数</div><div class="mt-1 font-semibold text-slate-800">' + escapeHtml(item.version_count || 0) + '</div></div>' +
              '</div>' +
            '</div>' +
            (item.notes ? '<div class="mt-4 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-6 text-slate-600">' + escapeHtml(item.notes) + '</div>' : '') +
            '<div class="mt-4 flex flex-col gap-2 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between">' +
              '<span>更新时间：' + escapeHtml(updatedAt) + '</span>' +
              '<span class="break-all">目录：' + escapeHtml(item.root_dir || '') + '</span>' +
            '</div>' +
            '<div class="mt-5 border-t border-slate-100 pt-5">' +
              '<div class="flex items-center justify-between gap-3">' +
                '<div class="text-sm font-semibold text-slate-800">最近导入</div>' +
                '<div class="text-xs text-slate-400">显示最近 ' + escapeHtml(recentAssets.length || 0) + ' 张</div>' +
              '</div>' +
              (previewGrid
                ? '<div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">' + previewGrid + '</div>'
                : '<div class="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-5 text-sm text-slate-500">还没有导入图片，可从上方选择 ZIP 包导入。</div>') +
            '</div>' +
          '</div>'
        );
      }).join('');
    }

    function applyTrainDatasetPayload(payload) {
      TRAIN_DATASET_STATE.items = payload.items || [];
      renderTrainSummary(payload.summary || {});
      renderTrainDatasetOptions(TRAIN_DATASET_STATE.items);
      renderTrainDatasets(TRAIN_DATASET_STATE.items);
    }

    function refreshTrainDatasets() {
      var box = document.getElementById('trainDatasetList');
      TRAIN_DATASET_STATE.loading = true;
      setTrainDatasetFeedback('', '');
      setTrainImportFeedback('', '');
      if (box && !TRAIN_DATASET_STATE.items.length) {
        box.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-sm text-slate-500">正在加载数据集...</div>';
      }

      fetch('/train/datasets')
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) {
            throw new Error(data.error || '加载数据集失败');
          }
          applyTrainDatasetPayload(data);
        })
        .catch(function (err) {
          if (box && !TRAIN_DATASET_STATE.items.length) {
            box.innerHTML = '<div class="rounded-2xl border border-dashed border-rose-200 bg-rose-50 px-4 py-6 text-sm text-rose-700">' + escapeHtml(err.message || '加载数据集失败') + '</div>';
          }
        })
        .finally(function () {
          TRAIN_DATASET_STATE.loading = false;
        });
    }

    function createTrainDataset(event) {
      if (event) event.preventDefault();
      var nameInput = document.getElementById('trainDatasetName');
      var classesInput = document.getElementById('trainDatasetClasses');
      var notesInput = document.getElementById('trainDatasetNotes');
      var submitBtn = document.getElementById('trainDatasetSubmit');
      if (!nameInput || !classesInput || !submitBtn) return false;

      var payload = {
        name: nameInput.value.trim(),
        class_names: classesInput.value.trim(),
        notes: notesInput ? notesInput.value.trim() : ''
      };

      submitBtn.disabled = true;
      setTrainDatasetFeedback('', '');

      fetch('/train/datasets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(function (resp) {
          return resp.text().then(function (text) {
            var data = {};
            try {
              data = text ? JSON.parse(text) : {};
            } catch (e) {
              data = {};
            }
            data.__http_ok = resp.ok;
            data.__http_status = resp.status;
            return data;
          });
        })
        .then(function (data) {
          if (!data.ok || data.__http_ok === false) {
            throw new Error(data.error || ('创建数据集失败，HTTP ' + (data.__http_status || 'unknown')));
          }
          applyTrainDatasetPayload(data);
          document.getElementById('trainDatasetForm').reset();
          if (data.dataset_id) {
            var datasetSelect = document.getElementById('trainImportDataset');
            if (datasetSelect) datasetSelect.value = data.dataset_id;
          }
          setTrainImportFeedback('', '');
          setTrainDatasetFeedback('数据集已创建，可继续导入 ZIP 图片。', 'success');
        })
        .catch(function (err) {
          setTrainDatasetFeedback(err.message || '创建数据集失败', 'error');
        })
        .finally(function () {
          submitBtn.disabled = false;
        });
      return false;
    }

    function importTrainZip(event) {
      if (event) event.preventDefault();
      var datasetSelect = document.getElementById('trainImportDataset');
      var fileInput = document.getElementById('trainImportFile');
      var submitBtn = document.getElementById('trainImportSubmit');
      if (!datasetSelect || !fileInput || !submitBtn) return false;

      var datasetId = datasetSelect.value;
      var file = fileInput.files && fileInput.files[0];
      if (!datasetId) {
        setTrainImportFeedback('请先选择一个数据集。', 'error');
        return false;
      }
      if (!file) {
        setTrainImportFeedback('请选择要导入的 ZIP 文件。', 'error');
        return false;
      }

      TRAIN_DATASET_STATE.importing = true;
      submitBtn.disabled = true;
      setTrainImportFeedback('', '');

      var formData = new FormData();
      formData.append('file', file);

      fetch('/train/datasets/' + encodeURIComponent(datasetId) + '/import-zip', {
        method: 'POST',
        body: formData
      })
        .then(function (resp) {
          return resp.text().then(function (text) {
            var data = {};
            try {
              data = text ? JSON.parse(text) : {};
            } catch (e) {
              data = {};
            }
            data.__http_ok = resp.ok;
            data.__http_status = resp.status;
            return data;
          });
        })
        .then(function (data) {
          if (!data.ok || data.__http_ok === false) {
            throw new Error(data.error || ('ZIP 导入失败，HTTP ' + (data.__http_status || 'unknown')));
          }
          applyTrainDatasetPayload(data);
          document.getElementById('trainImportForm').reset();
          if (data.dataset_id) {
            var select = document.getElementById('trainImportDataset');
            if (select) select.value = data.dataset_id;
          }
          setTrainDatasetFeedback('', '');
          setTrainImportFeedback(data.message || 'ZIP 导入完成', 'success');
        })
        .catch(function (err) {
          setTrainImportFeedback(err.message || 'ZIP 导入失败', 'error');
        })
        .finally(function () {
          TRAIN_DATASET_STATE.importing = false;
          renderTrainDatasetOptions(TRAIN_DATASET_STATE.items);
        });
      return false;
    }

    function refreshTrainTab() {
      refreshTrainDatasets();
      return false;
    }

    const FACE_RESULT_STATE = {
      oracle: { jobId: '', items: [], selected: new Set(), identifyResults: {}, identitySummary: {}, library: null, loading: false },
      upload: { jobId: '', items: [], selected: new Set(), identifyResults: {}, identitySummary: {}, library: null, loading: false }
    };
    const FACE_LIBRARY_TASK_STATE = { id: '', status: '', message: '', action: '', processed: 0, total: 0 };
    const FACE_LIBRARY_STATE = { library: null };
    const RESULT_DETAIL_STATE = { prefix: '', assetId: '' };

    function escapeHtml(value) {
      return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function formatBytes(size) {
      var value = Number(size || 0);
      if (!value) return '0 B';
      if (value < 1024) return value + ' B';
      if (value < 1024 * 1024) return (value / 1024).toFixed(1) + ' KB';
      return (value / 1024 / 1024).toFixed(1) + ' MB';
    }

    function faceStatusMeta(status) {
      var map = {
        matched: { label: '已匹配', badge: 'bg-emerald-100 text-emerald-700 ring-emerald-200' },
        no_match: { label: '无匹配', badge: 'bg-slate-100 text-slate-700 ring-slate-200' },
        no_face: { label: '无人脸', badge: 'bg-amber-100 text-amber-700 ring-amber-200' },
        low_quality: { label: '低质量', badge: 'bg-orange-100 text-orange-700 ring-orange-200' },
        library_unavailable: { label: '人脸库未就绪', badge: 'bg-rose-100 text-rose-700 ring-rose-200' },
        error: { label: '识别失败', badge: 'bg-rose-100 text-rose-700 ring-rose-200' }
      };
      return map[status] || map.no_match;
    }

    function getResultDom(prefix) {
      return {
        panel: document.getElementById(prefix + 'ResultPanel'),
        summary: document.getElementById(prefix + 'ResultSummary'),
        library: document.getElementById(prefix + 'LibraryStatus'),
        task: document.getElementById(prefix + 'LibraryTask'),
        grid: document.getElementById(prefix + 'ResultGrid'),
        identifyBtn: document.getElementById(prefix + 'IdentifySelectedBtn')
      };
    }

    function getFaceLibraryDom() {
      return {
        status: document.getElementById('faceLibraryStatusGlobal'),
        task: document.getElementById('faceLibraryTaskGlobal')
      };
    }

    function resetResultState(prefix) {
      FACE_RESULT_STATE[prefix] = { jobId: '', items: [], selected: new Set(), identifyResults: {}, identitySummary: {}, library: null, loading: false };
      var dom = getResultDom(prefix);
      if (dom.panel) dom.panel.classList.add('hidden');
      if (dom.grid) dom.grid.innerHTML = '';
      if (dom.summary) dom.summary.textContent = '暂无结果图';
      if (dom.library) dom.library.textContent = '';
      if (dom.task) dom.task.textContent = '';
      if (dom.identifyBtn) dom.identifyBtn.disabled = true;
      if (RESULT_DETAIL_STATE.prefix === prefix) closeResultDetail();
    }

    function setFaceLibraryTask(task) {
      if (!task) {
        FACE_LIBRARY_TASK_STATE.id = '';
        FACE_LIBRARY_TASK_STATE.status = '';
        FACE_LIBRARY_TASK_STATE.message = '';
        FACE_LIBRARY_TASK_STATE.action = '';
        FACE_LIBRARY_TASK_STATE.processed = 0;
        FACE_LIBRARY_TASK_STATE.total = 0;
      } else {
        FACE_LIBRARY_TASK_STATE.id = task.id || '';
        FACE_LIBRARY_TASK_STATE.status = task.status || '';
        FACE_LIBRARY_TASK_STATE.message = task.message || '';
        FACE_LIBRARY_TASK_STATE.action = task.action || '';
        FACE_LIBRARY_TASK_STATE.processed = task.processed || 0;
        FACE_LIBRARY_TASK_STATE.total = task.total || 0;
      }
      renderLibraryTaskState();
    }

    function renderLibraryTaskState() {
      var globalDom = getFaceLibraryDom();
      if (globalDom.task) {
        if (!FACE_LIBRARY_TASK_STATE.id) {
          globalDom.task.textContent = '';
        } else {
          var globalText = '人脸库任务：' + (FACE_LIBRARY_TASK_STATE.action === 'sync' ? '同步' : '重建') + ' · ' +
            (FACE_LIBRARY_TASK_STATE.message || FACE_LIBRARY_TASK_STATE.status || '运行中');
          if (FACE_LIBRARY_TASK_STATE.total) {
            globalText += ' · ' + FACE_LIBRARY_TASK_STATE.processed + '/' + FACE_LIBRARY_TASK_STATE.total;
          }
          globalDom.task.textContent = globalText;
        }
      }
      ['oracle', 'upload'].forEach(function (prefix) {
        var dom = getResultDom(prefix);
        if (!dom.task) return;
        if (!FACE_LIBRARY_TASK_STATE.id) {
          dom.task.textContent = '';
          return;
        }
        var text = '人脸库任务：' + (FACE_LIBRARY_TASK_STATE.action === 'sync' ? '同步' : '重建') + ' · ' +
          (FACE_LIBRARY_TASK_STATE.message || FACE_LIBRARY_TASK_STATE.status || '运行中');
        if (FACE_LIBRARY_TASK_STATE.total) {
          text += ' · ' + FACE_LIBRARY_TASK_STATE.processed + '/' + FACE_LIBRARY_TASK_STATE.total;
        }
        dom.task.textContent = text;
      });
    }

    function pollFaceLibraryTask(taskId) {
      if (!taskId) return;
      fetch('/face/library/task/' + taskId)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          var task = data.task || {};
          setFaceLibraryTask(task);
          if (task.status === 'running') {
            window.setTimeout(function () { pollFaceLibraryTask(taskId); }, 1200);
            return;
          }
          refreshFaceLibraryStatus('oracle');
          refreshFaceLibraryStatus('upload');
          if (task.status === 'done') {
            alert((task.action === 'sync' ? '人脸库同步完成' : '人脸特征重建完成'));
          } else if (task.status === 'error') {
            alert(task.error || task.message || '人脸库任务失败');
          }
          window.setTimeout(function () { setFaceLibraryTask(null); }, 1500);
        })
        .catch(function () {
          window.setTimeout(function () { pollFaceLibraryTask(taskId); }, 2000);
        });
    }

    function renderLibraryStatus(prefix) {
      var dom = getResultDom(prefix);
      var state = FACE_RESULT_STATE[prefix];
      if (!dom.library) return;
      if (!state.library) {
        dom.library.textContent = '正在读取人脸库状态...';
        return;
      }
      var lib = state.library;
      dom.library.textContent =
        '人脸库：' + (lib.ready ? '已就绪' : '未就绪') +
        ' · 有效人员 ' + (lib.valid_person_count || 0) +
        ' · 底库照片 ' + (lib.photo_count || 0) +
        ' · 特征文件 ' + (lib.feature_count || 0);
    }

    function renderGlobalFaceLibraryStatus() {
      var dom = getFaceLibraryDom();
      if (!dom.status) return;
      if (!FACE_LIBRARY_STATE.library) {
        dom.status.textContent = '正在读取人脸库状态...';
        return;
      }
      var lib = FACE_LIBRARY_STATE.library;
      var text =
        '人脸库：' + (lib.ready ? '已就绪' : '未就绪') +
        ' · 有效人员 ' + (lib.valid_person_count || 0) +
        ' · 底库照片 ' + (lib.photo_count || 0) +
        ' · 特征文件 ' + (lib.feature_count || 0);
      if (!lib.sql_configured) {
        text += ' · 未配置内网数据库连接';
      }
      dom.status.textContent = text;
    }

    function getResultItem(prefix, assetId) {
      var state = FACE_RESULT_STATE[prefix];
      for (var i = 0; i < state.items.length; i++) {
        if (state.items[i].id === assetId) return state.items[i];
      }
      return null;
    }

    function closeResultDetail() {
      RESULT_DETAIL_STATE.prefix = '';
      RESULT_DETAIL_STATE.assetId = '';
      var overlay = document.getElementById('resultDetailOverlay');
      var drawer = document.getElementById('resultDetailDrawer');
      if (overlay) overlay.classList.add('hidden');
      if (drawer) drawer.classList.add('translate-x-full');
    }

    function renderResultDetail() {
      var prefix = RESULT_DETAIL_STATE.prefix;
      var assetId = RESULT_DETAIL_STATE.assetId;
      var overlay = document.getElementById('resultDetailOverlay');
      var drawer = document.getElementById('resultDetailDrawer');
      if (!prefix || !assetId || !overlay || !drawer) {
        closeResultDetail();
        return;
      }

      var item = getResultItem(prefix, assetId);
      if (!item) {
        closeResultDetail();
        return;
      }

      var state = FACE_RESULT_STATE[prefix];
      var identify = state.identifyResults[assetId] || null;
      var meta = identify ? faceStatusMeta(identify.status) : null;
      var selected = state.selected.has(assetId);

      document.getElementById('resultDetailSource').textContent = prefix === 'oracle' ? '数据库检测结果' : '本地上传检测结果';
      document.getElementById('resultDetailTitle').textContent = item.origin_name || item.name;
      document.getElementById('resultDetailPreview').src = item.asset_url;
      document.getElementById('resultDetailPreview').alt = item.name;
      document.getElementById('resultDetailMeta').textContent = '文件：' + item.name + ' · 大小：' + formatBytes(item.size_bytes);

      var selectBtn = document.getElementById('resultDetailSelectBtn');
      selectBtn.textContent = selected ? '移出批量识别' : '加入批量识别';
      selectBtn.onclick = function () {
        var currentState = FACE_RESULT_STATE[prefix];
        if (currentState.selected.has(assetId)) currentState.selected.delete(assetId);
        else currentState.selected.add(assetId);
        renderResultGrid(prefix);
        renderResultDetail();
      };

      var identifyBtn = document.getElementById('resultDetailIdentifyBtn');
      identifyBtn.onclick = function () {
        identifySingleResult(prefix, encodeURIComponent(assetId));
      };

      var statusBox = document.getElementById('resultDetailStatus');
      var facesBox = document.getElementById('resultDetailFaces');
      if (!identify) {
        statusBox.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">尚未对这张图片执行身份识别。</div>';
        facesBox.innerHTML = '';
      } else {
        statusBox.innerHTML =
          '<div class="flex items-center gap-3">' +
            '<span class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge + '">' + meta.label + '</span>' +
            '<span class="text-xs text-slate-500">检测到人脸 ' + (identify.face_count || 0) + ' 张</span>' +
          '</div>' +
          (identify.error ? '<div class="mt-3 text-sm text-rose-600">' + escapeHtml(identify.error) + '</div>' : '');

        facesBox.innerHTML = (identify.faces || []).map(function (face, index) {
          var matches = face.top_matches || [];
          var similarityScore = matches.length && matches[0].score ? matches[0].score : '-';
          var matchesHtml = matches.length ? matches.map(function (match) {
            var photo = match.photo_url ? '<img src="' + match.photo_url + '" alt="' + escapeHtml(match.name || '') + '" class="h-12 w-12 rounded-2xl object-cover ring-1 ring-inset ring-slate-200" />' : '';
            return (
              '<div class="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-3">' +
                photo +
                '<div class="min-w-0 flex-1">' +
                  '<div class="truncate text-sm font-semibold text-slate-800">' + escapeHtml(match.name || '') + '</div>' +
                  '<div class="truncate text-xs text-slate-500">' + escapeHtml(match.id_number || '') + '</div>' +
                '</div>' +
                '<div class="text-right text-xs font-semibold text-slate-500">检测分 ' + escapeHtml(face.det_score || '-') + '</div>' +
              '</div>'
            );
          }).join('') : '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">该人脸暂无匹配结果。</div>';

          return (
            '<div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-4">' +
              '<div class="flex items-center justify-between gap-3">' +
                '<div class="text-sm font-semibold text-slate-800">人脸 ' + (index + 1) + '</div>' +
                '<span class="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-200">框：' + escapeHtml((face.bbox || []).join(', ')) + '</span>' +
              '</div>' +
              '<div class="mt-2 text-xs leading-6 text-slate-500">相似度 ' + escapeHtml(similarityScore) + ' · 清晰度 ' + escapeHtml(face.blur_score || '') + ' · 对齐 ' + (face.used_align ? '是' : '否') + '</div>' +
              '<div class="mt-3 space-y-3">' + matchesHtml + '</div>' +
            '</div>'
          );
        }).join('');
      }

      overlay.classList.remove('hidden');
      drawer.classList.remove('translate-x-full');
    }

    function openResultDetail(prefix, encodedAssetId) {
      RESULT_DETAIL_STATE.prefix = prefix;
      RESULT_DETAIL_STATE.assetId = decodeURIComponent(encodedAssetId);
      renderResultDetail();
    }

    function renderResultGrid(prefix) {
      var state = FACE_RESULT_STATE[prefix];
      var dom = getResultDom(prefix);
      if (!dom.grid || !dom.summary) return;

      dom.summary.textContent = '结果图 ' + state.items.length + ' 张，已选 ' + state.selected.size + ' 张';
      var identitySummary = state.identitySummary || {};
      if (identitySummary.recognized_asset_count) {
        dom.summary.textContent += ' 路 宸茶瘑鍒? ' + identitySummary.recognized_asset_count + ' 寮?';
        if (identitySummary.matched_asset_count) {
          dom.summary.textContent += ' 路 鍛戒腑 ' + identitySummary.matched_asset_count + ' 寮?';
        }
      }
      if (dom.identifyBtn) dom.identifyBtn.disabled = state.selected.size === 0 || state.loading;

      if (!state.items.length) {
        dom.grid.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-sm text-slate-500">当前任务没有可用于身份识别的结果图。</div>';
        return;
      }

      dom.grid.innerHTML = state.items.map(function (item) {
        var checked = state.selected.has(item.id);
        var identify = state.identifyResults[item.id] || null;
        var statusHtml = '';
        var detailHtml = '<div class="mt-3 text-xs text-slate-500">大小：' + escapeHtml(formatBytes(item.size_bytes)) + '</div>';
        if (identify) {
          var meta = faceStatusMeta(identify.status);
          statusHtml = '<div class="mt-3 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge + '">' + meta.label + '</div>';
          if (identify.status === 'matched' && identify.faces && identify.faces[0] && identify.faces[0].top_matches && identify.faces[0].top_matches[0]) {
            var top = identify.faces[0].top_matches[0];
            detailHtml += '<div class="mt-2 text-xs leading-5 text-emerald-700">命中：' + escapeHtml(top.name || '') + ' · ' + escapeHtml(top.id_number || '') + ' · 相似度 ' + escapeHtml(top.score || '') + '</div>';
          } else if (identify.error) {
            detailHtml += '<div class="mt-2 text-xs leading-5 text-rose-600">' + escapeHtml(identify.error) + '</div>';
          } else {
            detailHtml += '<div class="mt-2 text-xs leading-5 text-slate-500">检测到人脸 ' + escapeHtml(identify.face_count || 0) + ' 张</div>';
          }
        }
        return (
          '<div class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm shadow-slate-200/60">' +
            '<label class="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">' +
              '<span class="min-w-0 flex-1 truncate text-sm font-medium text-slate-700">' + escapeHtml(item.origin_name || item.name) + '</span>' +
              '<input type="checkbox" class="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500" ' + (checked ? 'checked ' : '') + 'onchange="toggleResultSelection(\'' + prefix + '\', \'' + encodeURIComponent(item.id) + '\', this.checked)">' +
            '</label>' +
            '<button type="button" class="block w-full" onclick="openResultDetail(\'' + prefix + '\', \'' + encodeURIComponent(item.id) + '\')">' +
              '<img src="' + item.asset_url + '" alt="' + escapeHtml(item.name) + '" class="h-40 w-full bg-slate-100 object-cover" />' +
            '</button>' +
            '<div class="p-4">' +
              '<div class="flex items-center justify-between gap-2">' +
                '<div class="truncate text-xs text-slate-400">' + escapeHtml(item.name) + '</div>' +
                '<div class="flex items-center gap-2">' +
                  '<button type="button" class="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50" onclick="openResultDetail(\'' + prefix + '\', \'' + encodeURIComponent(item.id) + '\')">查看详情</button>' +
                  '<button type="button" class="rounded-full bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700" onclick="identifySingleResult(\'' + prefix + '\', \'' + encodeURIComponent(item.id) + '\')">识别身份</button>' +
                '</div>' +
              '</div>' +
              statusHtml +
              detailHtml +
            '</div>' +
          '</div>'
        );
      }).join('');
    }

    function toggleResultSelection(prefix, encodedAssetId, checked) {
      var assetId = decodeURIComponent(encodedAssetId);
      var state = FACE_RESULT_STATE[prefix];
      if (checked) {
        state.selected.add(assetId);
      } else {
        state.selected.delete(assetId);
      }
      renderResultGrid(prefix);
      if (RESULT_DETAIL_STATE.prefix === prefix && RESULT_DETAIL_STATE.assetId === assetId) {
        renderResultDetail();
      }
    }

    function toggleAllResults(prefix, checked) {
      var state = FACE_RESULT_STATE[prefix];
      state.selected = new Set(checked ? state.items.map(function (item) { return item.id; }) : []);
      renderResultGrid(prefix);
      if (RESULT_DETAIL_STATE.prefix === prefix && RESULT_DETAIL_STATE.assetId) {
        renderResultDetail();
      }
    }

    function refreshFaceLibraryStatus(prefix) {
      var targetPrefixes = FACE_RESULT_STATE[prefix] ? [prefix] : ['oracle', 'upload'];
      fetch('/face/library/status')
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          targetPrefixes.forEach(function (itemPrefix) {
            FACE_RESULT_STATE[itemPrefix].library = data.library || null;
            renderLibraryStatus(itemPrefix);
          });
          FACE_LIBRARY_STATE.library = data.library || null;
          if (data.task) {
            var shouldPoll = data.task.status === 'running' && FACE_LIBRARY_TASK_STATE.id !== data.task.id;
            setFaceLibraryTask(data.task);
            if (shouldPoll) pollFaceLibraryTask(data.task.id);
          }
          renderGlobalFaceLibraryStatus();
          renderFaceTabStatus();
          renderFaceTabTask();
        })
        .catch(function () {
          var fallbackLibrary = { ready: false, valid_person_count: 0, photo_count: 0, feature_count: 0 };
          targetPrefixes.forEach(function (itemPrefix) {
            FACE_RESULT_STATE[itemPrefix].library = fallbackLibrary;
            renderLibraryStatus(itemPrefix);
          });
          FACE_LIBRARY_STATE.library = fallbackLibrary;
          renderGlobalFaceLibraryStatus();
        });
    }

    function loadResultGallery(prefix, jobId) {
      var dom = getResultDom(prefix);
      if (!dom.panel) return;
      dom.panel.classList.remove('hidden');
      FACE_RESULT_STATE[prefix] = { jobId: jobId, items: [], selected: new Set(), identifyResults: {}, identitySummary: {}, library: null, loading: false };
      dom.summary.textContent = '正在加载结果图...';
      dom.grid.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-sm text-slate-500">正在加载结果图...</div>';
      refreshFaceLibraryStatus(prefix);

      fetch('/face/results/' + jobId)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) {
            dom.summary.textContent = data.error || '未找到结果图';
            dom.grid.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-sm text-slate-500">' + escapeHtml(data.error || '未找到结果图') + '</div>';
            return;
          }
          FACE_RESULT_STATE[prefix].items = data.items || [];
          FACE_RESULT_STATE[prefix].identifyResults = {};
          (data.items || []).forEach(function (item) {
            if (item.identity) {
              FACE_RESULT_STATE[prefix].identifyResults[item.id] = item.identity;
            }
          });
          FACE_RESULT_STATE[prefix].identitySummary = data.identity_summary || {};
          renderResultGrid(prefix);
          if (RESULT_DETAIL_STATE.prefix === prefix && RESULT_DETAIL_STATE.assetId) {
            renderResultDetail();
          }
        })
        .catch(function () {
          dom.summary.textContent = '加载结果图失败';
          dom.grid.innerHTML = '<div class="rounded-2xl border border-dashed border-rose-200 bg-rose-50 px-4 py-6 text-sm text-rose-600">加载结果图失败，请稍后重试。</div>';
        });
    }

    function identifySelectedResults(prefix) {
      var state = FACE_RESULT_STATE[prefix];
      var selected = Array.from(state.selected);
      if (!state.jobId) {
        alert('当前没有可识别的任务结果');
        return;
      }
      if (!selected.length) {
        alert('请先勾选至少一张结果图');
        return;
      }

      state.loading = true;
      renderResultGrid(prefix);
      fetch('/face/identify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: state.jobId, asset_ids: selected, top_k: 5 })
      })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          state.loading = false;
          if (!data.ok) {
            alert(data.error || '身份识别失败');
            renderResultGrid(prefix);
            return;
          }
          (data.items || []).forEach(function (item) {
            state.identifyResults[item.asset_id] = item;
          });
          state.identitySummary = data.identity_summary || state.identitySummary;
          state.library = data.library || state.library;
          renderLibraryStatus(prefix);
          renderResultGrid(prefix);
          if (selected.length === 1) {
            openResultDetail(prefix, encodeURIComponent(selected[0]));
          } else if (RESULT_DETAIL_STATE.prefix === prefix && RESULT_DETAIL_STATE.assetId) {
            renderResultDetail();
          }
        })
        .catch(function () {
          state.loading = false;
          renderResultGrid(prefix);
          alert('身份识别请求失败');
        });
    }

    function identifySingleResult(prefix, encodedAssetId) {
      var assetId = decodeURIComponent(encodedAssetId);
      FACE_RESULT_STATE[prefix].selected = new Set([assetId]);
      renderResultGrid(prefix);
      openResultDetail(prefix, encodedAssetId);
      identifySelectedResults(prefix);
    }

    function runFaceLibraryAction(prefix, action) {
      var url = action === 'sync' ? '/face/library/sync' : '/face/library/rebuild';
      var tips = action === 'sync' ? '开始同步人脸库？当前环境若无法连接内网 SQL，会返回失败提示。' : '开始重建本地人脸特征？';
      if (!confirm(tips)) return;
      fetch(url, { method: 'POST' })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) {
            alert(data.error || '操作失败');
            return;
          }
          var task = data.task || null;
          if (task) {
            setFaceLibraryTask(task);
            if (data.started === false) {
              alert('已有进行中的人脸库任务，已切换为查看当前进度。');
            }
            pollFaceLibraryTask(task.id);
          } else {
            refreshFaceLibraryStatus('oracle');
            refreshFaceLibraryStatus('upload');
          }
        })
        .catch(function () {
          alert('请求失败，请稍后重试');
        });
    }

    function initUploadDragDrop() {
      var label = document.getElementById('uploadDropZone');
      if (!label) return;
      label.addEventListener('dragover', function (e) {
        e.preventDefault();
        label.classList.add('border-teal-400', 'bg-teal-50');
      });
      label.addEventListener('dragleave', function () {
        label.classList.remove('border-teal-400', 'bg-teal-50');
      });
      label.addEventListener('drop', function (e) {
        e.preventDefault();
        label.classList.remove('border-teal-400', 'bg-teal-50');
        var files = e.dataTransfer && e.dataTransfer.files;
        if (files && files[0]) {
          try {
            var dt = new DataTransfer();
            dt.items.add(files[0]);
            document.getElementById('uploadFile').files = dt.files;
          } catch (ex) {}
          onUploadFileChange(document.getElementById('uploadFile'));
        }
      });
    }


    // ==================== FACE TAB ====================
    const PERSON_STATE = { page: 1, pages: 1, total: 0, keyword: '', items: [] };
    let _personSearchTimer = null;

    function debouncePersonSearch() {
      clearTimeout(_personSearchTimer);
      _personSearchTimer = setTimeout(function () {
        PERSON_STATE.keyword = (document.getElementById('personSearchInput').value || '').trim();
        loadPersonDirectory(1);
      }, 400);
    }

    function loadPersonDirectory(page) {
      page = page || 1;
      var keyword = PERSON_STATE.keyword || '';
      var url = '/face/library/persons?page=' + page + '&page_size=12';
      if (keyword) url += '&keyword=' + encodeURIComponent(keyword);
      fetch(url)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          PERSON_STATE.page = data.page || 1;
          PERSON_STATE.pages = data.pages || 1;
          PERSON_STATE.total = data.total || 0;
          PERSON_STATE.items = data.items || [];
          renderPersonGrid();
        })
        .catch(function () {
          PERSON_STATE.items = [];
          renderPersonGrid();
        });
    }

    function renderPersonGrid() {
      var grid = document.getElementById('personGrid');
      var pageInfo = document.getElementById('personPageInfo');
      var prevBtn = document.getElementById('personPrevBtn');
      var nextBtn = document.getElementById('personNextBtn');
      if (!grid) return;

      pageInfo.textContent = '共 ' + PERSON_STATE.total + ' 人 · 第 ' + PERSON_STATE.page + ' / ' + PERSON_STATE.pages + ' 页';
      prevBtn.disabled = PERSON_STATE.page <= 1;
      nextBtn.disabled = PERSON_STATE.page >= PERSON_STATE.pages;

      if (!PERSON_STATE.items.length) {
        grid.innerHTML = '<div class="col-span-full rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-sm text-slate-500">暂无人员数据。同步人脸库后可在此浏览。</div>';
        return;
      }

      var avatarColors = ['bg-teal-100 text-teal-700','bg-sky-100 text-sky-700','bg-amber-100 text-amber-700','bg-rose-100 text-rose-700','bg-violet-100 text-violet-700','bg-emerald-100 text-emerald-700'];
      grid.innerHTML = PERSON_STATE.items.map(function (p, i) {
        var ac = avatarColors[i % avatarColors.length];
        var initial = (p.name || '?')[0];
        var statusBadge = p.status === 'valid'
          ? '<span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">有效</span>'
          : '<span class="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">特征缺失</span>';
        return (
          '<div class="overflow-hidden rounded-3xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/60 transition hover:shadow-md hover:shadow-slate-200/80 cursor-pointer" onclick="openPersonDetail(\'' + escapeHtml(p.id || '') + '\')">' +
            '<div class="flex items-center gap-4">' +
              '<div class="flex h-[52px] w-[52px] flex-shrink-0 items-center justify-center rounded-full ' + ac + ' text-lg font-bold">' + escapeHtml(initial) + '</div>' +
              '<div class="min-w-0 flex-1">' +
                '<div class="truncate text-base font-semibold text-slate-900">' + escapeHtml(p.name || '') + '</div>' +
                '<div class="truncate text-xs text-slate-500">' + escapeHtml(p.id_number || '') + '</div>' +
              '</div>' +
            '</div>' +
            '<div class="mt-4 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2.5">' +
              '<div class="text-xs text-slate-500">照片 ' + (p.has_photo ? '有' : '无') + ' · 特征 ' + (p.has_feature ? '已提取' : '缺失') + '</div>' +
            '</div>' +
            '<div class="mt-4 flex items-center justify-between">' +
              statusBadge +
              '<button type="button" class="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50" onclick="event.stopPropagation();openPersonDetail(\'' + escapeHtml(p.id || '') + '\')">查看</button>' +
            '</div>' +
          '</div>'
        );
      }).join('');
    }

    function openPersonDetail(personId) {
      var person = null;
      for (var i = 0; i < PERSON_STATE.items.length; i++) {
        if (PERSON_STATE.items[i].id === personId) { person = PERSON_STATE.items[i]; break; }
      }
      if (!person) return;

      document.getElementById('personDetailName').textContent = person.name || '';
      document.getElementById('personDetailFullName').textContent = person.name || '';
      document.getElementById('personDetailIdNumber').textContent = person.id_number || '';
      document.getElementById('personDetailAvatar').textContent = (person.name || '?')[0];
      document.getElementById('personDetailIdType').textContent = person.id_type || '--';
      document.getElementById('personDetailIdNum2').textContent = person.id_number || '--';

      var featureEl = document.getElementById('personDetailFeature');
      if (person.has_feature) {
        featureEl.textContent = '已提取';
        featureEl.className = 'font-medium text-emerald-600';
      } else {
        featureEl.textContent = '缺失';
        featureEl.className = 'font-medium text-amber-600';
      }
      document.getElementById('personDetailPhotoStatus').textContent = person.has_photo ? '有' : '无';

      var photoBox = document.getElementById('personDetailPhoto');
      if (person.has_photo) {
        photoBox.innerHTML = '<img src="/face/library/photo/' + encodeURIComponent(personId) + '" alt="底库照片" class="aspect-square rounded-2xl border border-slate-200 object-cover" style="min-height:160px" />';
      } else {
        photoBox.innerHTML = '<div class="col-span-2 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-6 text-center text-sm text-slate-500">暂无底库照片</div>';
      }

      document.getElementById('personDetailOverlay').classList.remove('hidden');
      document.getElementById('personDetailDrawer').classList.remove('translate-x-full');
    }

    function closePersonDetail() {
      document.getElementById('personDetailOverlay').classList.add('hidden');
      document.getElementById('personDetailDrawer').classList.add('translate-x-full');
    }

    function loadOperationHistory() {
      fetch('/face/library/tasks')
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.ok) return;
          renderOperationHistory(data.tasks || []);
        })
        .catch(function () {});
    }

    function renderOperationHistory(tasks) {
      var box = document.getElementById('faceHistoryRows');
      if (!box) return;
      if (!tasks.length) {
        box.innerHTML = '<div class="px-5 py-5 text-center text-sm text-slate-500">暂无操作记录。</div>';
        return;
      }
      box.innerHTML = tasks.map(function (t) {
        var actionLabel = t.action === 'sync' ? '同步' : '重建特征';
        var statusMap = {
          done: '<span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">已完成</span>',
          running: '<span class="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-1 text-xs font-semibold text-sky-700 ring-1 ring-inset ring-sky-200">运行中</span>',
          error: '<span class="inline-flex items-center rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700 ring-1 ring-inset ring-rose-200">失败</span>'
        };
        var statusHtml = statusMap[t.status] || '<span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">' + escapeHtml(t.status || '--') + '</span>';
        var timeStr = t.start_ts ? new Date(t.start_ts * 1000).toLocaleString('zh-CN') : '--';
        var countStr = (t.processed || 0) + ' / ' + (t.total || 0);
        var remark = t.error || t.message || '—';
        return (
          '<div class="grid grid-cols-12 items-center gap-3 border-t border-slate-100 px-5 py-3.5" style="' + (tasks.indexOf(t) % 2 === 1 ? 'background:rgba(248,250,252,0.6)' : '') + '">' +
            '<div class="col-span-2 text-sm font-medium text-slate-900">' + escapeHtml(actionLabel) + '</div>' +
            '<div class="col-span-2">' + statusHtml + '</div>' +
            '<div class="col-span-3 text-sm text-slate-600">' + escapeHtml(timeStr) + '</div>' +
            '<div class="col-span-2 text-sm text-slate-600">' + escapeHtml(countStr) + '</div>' +
            '<div class="col-span-3 text-sm text-slate-400">' + escapeHtml(remark) + '</div>' +
          '</div>'
        );
      }).join('');
    }

    function renderFaceTabStatus() {
      var lib = FACE_LIBRARY_STATE.library;
      if (!lib) return;
      var readyEl = document.getElementById('faceMetricReady');
      if (readyEl) {
        readyEl.textContent = lib.ready ? '已就绪' : '未就绪';
        readyEl.className = 'mt-2 text-xl font-bold ' + (lib.ready ? 'text-emerald-600' : 'text-amber-600');
      }
      var personsEl = document.getElementById('faceMetricPersons');
      if (personsEl) personsEl.textContent = lib.valid_person_count || 0;
      var photosEl = document.getElementById('faceMetricPhotos');
      if (photosEl) photosEl.textContent = lib.photo_count || 0;
      var featuresEl = document.getElementById('faceMetricFeatures');
      if (featuresEl) featuresEl.textContent = lib.feature_count || 0;
      var sqlEl = document.getElementById('faceMetricSql');
      if (sqlEl) {
        sqlEl.textContent = lib.sql_configured ? '已配置' : '未配置';
        sqlEl.className = 'mt-2 text-xl font-bold ' + (lib.sql_configured ? 'text-emerald-600' : 'text-amber-600');
      }
    }

    function renderFaceTabTask() {
      var section = document.getElementById('faceTaskSection');
      if (!section) return;
      if (!FACE_LIBRARY_TASK_STATE.id) {
        section.classList.add('hidden');
        return;
      }
      section.classList.remove('hidden');
      var t = FACE_LIBRARY_TASK_STATE;
      var actionLabel = t.action === 'sync' ? '同步' : '重建特征';
      var meta = statusMeta(t.status || 'running');
      document.getElementById('faceTaskTitle').textContent = '人脸库任务：' + actionLabel;
      document.getElementById('faceTaskMessage').textContent = t.message || t.status || '';
      var badge = document.getElementById('faceTaskBadge');
      badge.textContent = meta.label;
      badge.className = 'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ' + meta.badge;
      var pct = t.total ? Math.min(100, Math.floor(t.processed * 100 / t.total)) : 0;
      document.getElementById('faceTaskBar').style.width = pct + '%';
      document.getElementById('faceTaskBar').className = 'h-3 rounded-full transition-all ' + meta.bar;
      document.getElementById('faceTaskPct').textContent = '进度 ' + pct + '%';
      document.getElementById('faceTaskCount').textContent = t.processed + ' / ' + t.total;
    }

    function refreshFaceTab() {
      refreshFaceLibraryStatus('oracle');
      setTimeout(function () {
        renderFaceTabStatus();
        renderFaceTabTask();
      }, 500);
      loadPersonDirectory(PERSON_STATE.page);
      loadOperationHistory();
    }

    window.addEventListener('load', function () {
      document.getElementById('model_key').addEventListener('change', applyModelUI);
      document.getElementById('confRange').addEventListener('input', syncConfValue);
      applyModelUI();
      syncConfValue();
      refreshJobs();

      // Upload tab init
      populateUploadModelSelect();
      document.getElementById('uploadModelKey').addEventListener('change', applyUploadModelUI);
      document.getElementById('uploadConfRange').addEventListener('input', syncUploadConfValue);
      applyUploadModelUI();
      syncUploadConfValue();
      initUploadDragDrop();
      resetResultState('oracle');
      resetResultState('upload');
      refreshFaceLibraryStatus('oracle');
      refreshFaceLibraryStatus('upload');

      try {
        var activeTab = localStorage.getItem('bczj_active_tab');
        if (activeTab === 'Upload') {
          switchTab('Upload');
        } else if (activeTab === 'Train') {
          switchTab('Train');
        } else if (activeTab === 'Face') {
          switchTab('Face');
        }
      } catch (e) {}

      try {
        const lastJob = localStorage.getItem('bczj_last_job');
        if (lastJob) {
          document.getElementById('progressBox').classList.remove('hidden');
          poll(lastJob);
        }
      } catch (e) {}

      try {
        var lastUploadJob = localStorage.getItem('bczj_upload_job');
        if (lastUploadJob) {
          switchTab('Upload');
          document.getElementById('uploadProgressBox').classList.remove('hidden');
          pollUpload(lastUploadJob);
        }
      } catch (e) {}
    });

