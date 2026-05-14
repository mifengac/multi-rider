    const FACE_RESULT_STATE = {
      oracle: { jobId: '', items: [], selected: new Set(), identifyResults: {}, identitySummary: {}, library: null, loading: false },
      upload: { jobId: '', items: [], selected: new Set(), identifyResults: {}, identitySummary: {}, library: null, loading: false }
    };
    const RESULT_DETAIL_STATE = {
      prefix: '',
      assetId: '',
      lineageRequestKey: '',
      lineageAssetId: '',
      lineageLoading: false,
      lineageError: '',
      lineageAsset: null,
      lineageParent: null,
      lineageChildren: []
    };

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
        identifyBtn: document.getElementById(prefix + 'IdentifySelectedBtn'),
        addBtn: document.getElementById(prefix + 'AddDatasetBtn')
      };
    }

    function getResultItem(prefix, assetId) {
      var state = FACE_RESULT_STATE[prefix];
      for (var i = 0; i < state.items.length; i++) {
        if (state.items[i].id === assetId) return state.items[i];
      }
      return null;
    }

    function resetResultDetailLineage() {
      RESULT_DETAIL_STATE.lineageRequestKey = '';
      RESULT_DETAIL_STATE.lineageAssetId = '';
      RESULT_DETAIL_STATE.lineageLoading = false;
      RESULT_DETAIL_STATE.lineageError = '';
      RESULT_DETAIL_STATE.lineageAsset = null;
      RESULT_DETAIL_STATE.lineageParent = null;
      RESULT_DETAIL_STATE.lineageChildren = [];
    }

    function summarizeStructuredMediaAsset(asset, roleLabel) {
      if (!asset) {
        return '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">暂无' + roleLabel + '。</div>';
      }

      var sourceRowKey = '';
      if (asset.source_row_key) {
        sourceRowKey = typeof asset.source_row_key === 'string'
          ? asset.source_row_key
          : JSON.stringify(asset.source_row_key);
      }

      return (
        '<div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-4">' +
          '<div class="flex items-start justify-between gap-3">' +
            '<div>' +
              '<div class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">' + roleLabel + '</div>' +
              '<div class="mt-2 break-all text-sm font-semibold text-slate-900">' + escapeHtml(asset.asset_id || '') + '</div>' +
            '</div>' +
            '<span class="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-200">' + escapeHtml(asset.media_type || '--') + '</span>' +
          '</div>' +
          '<div class="mt-3 text-xs leading-6 text-slate-600">状态：' + escapeHtml(asset.detect_status || '--') + ' · 检测框 ' + escapeHtml(asset.detection_count || 0) + ' · 子资源 ' + escapeHtml(asset.child_count || 0) + '</div>' +
          '<div class="mt-2 break-all text-xs leading-6 text-slate-500">媒体地址：' + escapeHtml(asset.media_uri || '--') + '</div>' +
          (sourceRowKey ? '<div class="mt-2 break-all text-xs leading-6 text-slate-500">来源键：' + escapeHtml(sourceRowKey) + '</div>' : '') +
        '</div>'
      );
    }

    function renderResultLineage(item) {
      var box = document.getElementById('resultDetailLineage');
      if (!box) return;
      if (!item || !item.structured_asset_id) {
        box.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">当前结果暂未关联结构化媒体链路。</div>';
        return;
      }

      if (RESULT_DETAIL_STATE.lineageLoading) {
        box.innerHTML = '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">正在加载媒体链路...</div>';
        return;
      }

      if (RESULT_DETAIL_STATE.lineageError) {
        box.innerHTML = '<div class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">' + escapeHtml(RESULT_DETAIL_STATE.lineageError) + '</div>';
        return;
      }

      var children = RESULT_DETAIL_STATE.lineageChildren || [];
      var childrenHtml = children.length
        ? children.map(function (child, index) { return summarizeStructuredMediaAsset(child, '子资源 ' + (index + 1)); }).join('')
        : '<div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm text-slate-500">当前资源没有子资产。</div>';

      box.innerHTML = [
        '<div class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">Media Lineage</div>',
        summarizeStructuredMediaAsset(RESULT_DETAIL_STATE.lineageParent, '父资源'),
        summarizeStructuredMediaAsset(RESULT_DETAIL_STATE.lineageAsset, '当前资源'),
        '<div class="space-y-3"><div class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">子资源</div>' + childrenHtml + '</div>'
      ].join('');
    }

    function loadResultLineage(prefix, item) {
      if (!item || !item.structured_asset_id) {
        resetResultDetailLineage();
        renderResultLineage(item);
        return;
      }

      if (RESULT_DETAIL_STATE.lineageAssetId === item.structured_asset_id) {
        renderResultLineage(item);
        return;
      }

      var requestKey = prefix + ':' + item.id;
      RESULT_DETAIL_STATE.lineageRequestKey = requestKey;
      RESULT_DETAIL_STATE.lineageAssetId = item.structured_asset_id;
      RESULT_DETAIL_STATE.lineageLoading = true;
      RESULT_DETAIL_STATE.lineageError = '';
      RESULT_DETAIL_STATE.lineageAsset = null;
      RESULT_DETAIL_STATE.lineageParent = null;
      RESULT_DETAIL_STATE.lineageChildren = [];
      renderResultLineage(item);

      fetch(item.structured_lineage_url || ('/detection/api/structured/assets/' + encodeURIComponent(item.structured_asset_id) + '/lineage'))
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (RESULT_DETAIL_STATE.lineageRequestKey !== requestKey) {
            return;
          }
          if (!data.ok) {
            throw new Error(data.error || '加载媒体链路失败');
          }
          RESULT_DETAIL_STATE.lineageLoading = false;
          RESULT_DETAIL_STATE.lineageError = '';
          RESULT_DETAIL_STATE.lineageAsset = data.asset || null;
          RESULT_DETAIL_STATE.lineageParent = data.parent || null;
          RESULT_DETAIL_STATE.lineageChildren = data.children || [];
          renderResultLineage(getResultItem(prefix, item.id));
        })
        .catch(function (err) {
          if (RESULT_DETAIL_STATE.lineageRequestKey !== requestKey) {
            return;
          }
          RESULT_DETAIL_STATE.lineageLoading = false;
          RESULT_DETAIL_STATE.lineageError = err.message || '加载媒体链路失败';
          renderResultLineage(getResultItem(prefix, item.id));
        });
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
      if (dom.addBtn) dom.addBtn.disabled = true;
      if (RESULT_DETAIL_STATE.prefix === prefix) closeResultDetail();
    }

    function closeResultDetail() {
      RESULT_DETAIL_STATE.prefix = '';
      RESULT_DETAIL_STATE.assetId = '';
      resetResultDetailLineage();
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
      renderResultLineage(item);
      loadResultLineage(prefix, item);

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

      var addDatasetBtn = document.getElementById('resultDetailAddDatasetBtn');
      if (addDatasetBtn) {
        addDatasetBtn.onclick = function () {
          openResultImportModal(prefix, encodeURIComponent(assetId));
        };
      }

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
        dom.summary.textContent += ' · 已识别 ' + identitySummary.recognized_asset_count + ' 张';
        if (identitySummary.matched_asset_count) {
          dom.summary.textContent += ' · 命中 ' + identitySummary.matched_asset_count + ' 张';
        }
      }
      if (dom.identifyBtn) dom.identifyBtn.disabled = state.selected.size === 0 || state.loading;
      if (dom.addBtn) dom.addBtn.disabled = state.selected.size === 0 || TRAIN_DATASET_STATE.loading || RESULT_IMPORT_STATE.submitting;

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
                  '<button type="button" class="rounded-full border border-teal-200 bg-white px-3 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-50" onclick="openResultImportModal(\'' + prefix + '\', \'' + encodeURIComponent(item.id) + '\')">加入数据集</button>' +
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
          if (typeof refreshDispatchTab === 'function') {
            refreshDispatchTab();
          }
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
