// ============================================================
// workbench.js - 操作工作台
// ============================================================

var WorkbenchPage = (function() {
  var current = 'inspection';
  var rootEl = null;

  var NAV_ITEMS = [
    { key: 'inspection', title: '数据巡检', desc: '数据库批量研判', icon: 'database' },
    { key: 'materials', title: '本地素材', desc: '图片包 / 视频上传', icon: 'upload' },
    { key: 'dispatch', title: '任务下发', desc: '平台派单与短信', icon: 'send' },
    { key: 'training', title: '模型训练', desc: '样本闭环与发布', icon: 'layers' },
    { key: 'diagnostics', title: '系统诊断', desc: '队列 / Worker / 服务', icon: 'settings' },
  ];

  var MODULES = {
    inspection: {
      kicker: 'Data Inspection',
      title: '数据巡检',
      desc: '按时间范围、模型、置信度和时段过滤发起数据库巡检任务，实时查看队列进度、命中结果和后续流转入口。',
      primaryAction: '新建巡检任务',
      secondaryAction: '任务历史',
      kpis: [
        { label: '今日巡检', value: '18', sub: '较昨日 +4', tone: 'cyan' },
        { label: '命中素材', value: '126', sub: '待身份核验 23', tone: 'amber' },
        { label: '待下发对象', value: '9', sub: '一级高危 2', tone: 'red' },
        { label: 'Worker 状态', value: 'OK', sub: '队列延迟 12s', tone: 'green' },
      ],
    },
    materials: {
      kicker: 'Local Materials',
      title: '本地素材',
      desc: '接收民警现场采集的图片包和视频素材，完成上传、抽帧、识别、结果筛选和后续身份核验流转。',
      primaryAction: '上传素材',
      secondaryAction: '素材记录',
      kpis: [
        { label: '今日上传', value: '7', sub: '视频 3 / 图片包 4', tone: 'cyan' },
        { label: '保留帧', value: '342', sub: '可导入训练 91', tone: 'amber' },
        { label: '识别命中', value: '28', sub: '已入队 16', tone: 'red' },
        { label: '存储占用', value: '62%', sub: '剩余 186GB', tone: 'purple' },
      ],
    },
    dispatch: {
      kicker: 'Task Dispatch',
      title: '任务下发',
      desc: '承接识别命中对象，自动补全属地、联系方式和任务草稿，支持省厅任务平台派单、短信提醒和记录回看。',
      primaryAction: '通过平台下发',
      secondaryAction: '刷新队列',
      kpis: [
        { label: '待下发', value: '9', sub: '已选 3 人', tone: 'amber' },
        { label: '已认证', value: 'YES', sub: 'Token 剩余 42 分钟', tone: 'green' },
        { label: '今日下发', value: '21', sub: '平台 17 / 短信 4', tone: 'cyan' },
        { label: '逾期反馈', value: '2', sub: '需督办', tone: 'red' },
      ],
    },
    training: {
      kicker: 'Model Training',
      title: '模型训练',
      desc: '把巡检结果、人工复核和处置反馈沉淀为训练样本，完成数据集管理、预标注、训练评估和模型发布。',
      primaryAction: '创建训练任务',
      secondaryAction: '模型仓库',
      kpis: [
        { label: '数据集', value: '12', sub: '本月新增 3 个', tone: 'cyan' },
        { label: '已标注', value: '2,418', sub: '复核通过 81%', tone: 'green' },
        { label: '训练中', value: '2', sub: '低算力队列', tone: 'amber' },
        { label: '线上模型', value: 'v1.8', sub: '专项巡检模型', tone: 'purple' },
      ],
    },
    diagnostics: {
      kicker: 'System Diagnostics',
      title: '系统诊断',
      desc: '集中查看任务队列、Worker、数据库连接、模型文件和存储状态，快速定位阻塞任务并给出处置建议。',
      primaryAction: '刷新诊断',
      secondaryAction: '导出日志',
      kpis: [
        { label: '队列总数', value: '64', sub: '等待 11 / 运行 3', tone: 'cyan' },
        { label: '失败任务', value: '4', sub: '2 个可重试', tone: 'red' },
        { label: '服务健康', value: '92%', sub: 'Worker 正常', tone: 'green' },
        { label: '陈旧运行', value: '1', sub: '超过 30 分钟', tone: 'amber' },
      ],
    },
  };

  var JOBS = [
    { name: '夜间重点区域巡检', meta: 'detection · 68%', state: '运行中', tone: 'cyan' },
    { name: '校园周边素材复核', meta: 'upload · 已完成', state: '完成', tone: 'green' },
    { name: '结果图导入训练集', meta: 'train · 等待 Worker', state: '排队', tone: 'amber' },
    { name: '人脸库增量刷新', meta: 'face_library · 11分钟前', state: '待复核', tone: 'purple' },
  ];

  var FLOW = [
    { title: '巡检 / 上传命中', sub: '保留关键帧、摘要和命中说明', state: '已完成' },
    { title: '身份核验', sub: '匹配人脸库和人员档案', state: '进行中' },
    { title: '任务下发', sub: '自动补全属地和草稿', state: '待处理' },
    { title: '样本沉淀', sub: '正负样本回流训练集', state: '待入库' },
    { title: '模型迭代', sub: '评估通过后一键发布', state: '计划中' },
  ];

  function render(container) {
    rootEl = container;
    container.innerHTML =
      '<div class="workbench-layout">' +
        '<aside class="workbench-sidebar">' +
          '<div class="workbench-side-label">WORKBENCH</div>' +
          '<nav class="workbench-side-nav">' +
            NAV_ITEMS.map(function(item) {
              return '<button class="workbench-side-item' + (item.key === current ? ' active' : '') + '" data-workbench-key="' + item.key + '">' +
                '<span class="workbench-side-icon">' + icon(item.icon, 16) + '</span>' +
                '<span><span class="workbench-side-title">' + item.title + '</span><span class="workbench-side-desc">' + item.desc + '</span></span>' +
              '</button>';
            }).join('') +
          '</nav>' +
          '<div class="workbench-side-note">' +
            '<strong>闭环状态</strong>' +
            '<p>巡检命中结果可进入身份核验、任务下发和训练样本沉淀，形成实战反馈闭环。</p>' +
          '</div>' +
        '</aside>' +
        '<main class="workbench-main" id="workbench-main"></main>' +
      '</div>';
    renderActiveModule();
  }

  function init() {
    if (!rootEl) return;
    var sideNav = rootEl.querySelector('.workbench-side-nav');
    if (sideNav) {
      sideNav.addEventListener('click', handleSideClick);
    }
  }

  function destroy() {
    if (rootEl) {
      var sideNav = rootEl.querySelector('.workbench-side-nav');
      if (sideNav) sideNav.removeEventListener('click', handleSideClick);
    }
    rootEl = null;
  }

  function handleSideClick(e) {
    var btn = e.target.closest('[data-workbench-key]');
    if (!btn || !rootEl || !rootEl.contains(btn)) return;
    current = btn.dataset.workbenchKey || 'inspection';
    rootEl.querySelectorAll('.workbench-side-item').forEach(function(item) {
      item.classList.toggle('active', item.dataset.workbenchKey === current);
    });
    renderActiveModule();
  }

  function renderActiveModule() {
    if (!rootEl) return;
    var mod = MODULES[current] || MODULES.inspection;
    var main = rootEl.querySelector('#workbench-main');
    if (!main) return;
    main.innerHTML =
      renderModuleHeader(mod) +
      renderKpis(mod.kpis) +
      renderModuleBody(current);
  }

  function renderModuleHeader(mod) {
    return '<section class="workbench-module-header">' +
      '<div>' +
        '<div class="workbench-kicker">' + mod.kicker + '</div>' +
        '<h1 class="workbench-title">' + mod.title + '</h1>' +
        '<p class="workbench-subtitle">' + mod.desc + '</p>' +
      '</div>' +
      '<div class="workbench-actions">' +
        '<button class="btn-outline btn-sm">' + mod.secondaryAction + '</button>' +
        '<button class="btn-primary btn-sm">' + mod.primaryAction + '</button>' +
      '</div>' +
    '</section>';
  }

  function renderKpis(kpis) {
    return '<section class="workbench-kpi-row">' + kpis.map(function(kpi) {
      return '<div class="workbench-kpi">' +
        '<div class="workbench-kpi-label">' + kpi.label + '</div>' +
        '<div class="workbench-kpi-value tone-' + kpi.tone + '">' + kpi.value + '</div>' +
        '<div class="workbench-kpi-sub">' + kpi.sub + '</div>' +
      '</div>';
    }).join('') + '</section>';
  }

  function renderModuleBody(key) {
    if (key === 'materials') return renderMaterials();
    if (key === 'dispatch') return renderDispatch();
    if (key === 'training') return renderTraining();
    if (key === 'diagnostics') return renderDiagnostics();
    return renderInspection();
  }

  function renderInspection() {
    return '<section class="workbench-grid">' +
      renderCard('巡检参数', '套用夜间模板', renderFieldGrid([
        ['开始时间', '2026-05-18 00:00:00'],
        ['结束时间', '2026-05-18 23:59:59'],
        ['研判模型', '专项违法行为识别'],
        ['置信度阈值', '0.32'],
      ]) + renderChips(['夜游聚集', '飙车炸街', '校园周边', '重点区域']) + renderModuleStrip()) +
      renderQueueCard() +
      renderFlowCard() +
    '</section>';
  }

  function renderMaterials() {
    return '<section class="workbench-grid">' +
      renderCard('素材上传', '选择文件', '<div class="workbench-dropzone">' + icon('upload', 42) + '<strong>拖入图片 ZIP 或视频文件</strong><span>.zip / .mp4 / .avi / .mov / .mkv，单文件建议不超过 500MB</span></div>' + renderFieldGrid([
        ['识别模型', '通用人车要素识别'],
        ['抽帧间隔', '每 5 帧保留 1 帧'],
        ['置信度阈值', '0.18'],
        ['结果流转', '命中后自动进入身份核验'],
      ])) +
      renderCard('结果筛选', '导入训练集', renderResultList([
        ['夜间街面_00123.jpg', '疑似未戴头盔 · 0.87', '待核验'],
        ['校园周边_00048.jpg', '多人聚集 · 0.78', '已保留'],
        ['商圈入口_01342.jpg', '电动车载人 · 0.71', '待复核'],
        ['旅店门口_00412.jpg', '目标模糊 · 0.44', '低质量'],
      ])) +
      renderFlowCard() +
    '</section>';
  }

  function renderDispatch() {
    return '<section class="workbench-grid dispatch-grid">' +
      renderCard('待下发队列', '重查属地', renderResultList([
        ['张某辉', '高风险 · 新城区分局', '已选'],
        ['李某阳', '中风险 · 碑林区分局', '待选'],
        ['赵某杰', '极高风险 · 未央区分局', '已选'],
        ['陈某龙', '高风险 · 雁塔区分局', '待选'],
      ])) +
      renderCard('任务草稿', '格式化 JSON', renderFieldGrid([
        ['任务标题', '违法行为核查任务'],
        ['业务负责人', '治安支队研判岗'],
        ['签收时限', '2 小时内'],
        ['反馈时限', '24 小时内'],
      ]) + '<div class="workbench-editor">{"target":"张某辉","risk":"high","unit":"新城区分局","source":"AI巡检命中"}</div>') +
      renderCard('短信与记录', '刷新记录', '<div class="workbench-sms-preview">【提醒】请及时签收违法行为核查任务，关注高风险未成年人活动轨迹并反馈处置结果。</div>' + renderTimeline([
        ['05:11', '平台任务已下发', 'success'],
        ['05:12', '短信提醒已发送', 'success'],
        ['04:36', '任务草稿自动生成', 'info'],
      ])) +
    '</section>';
  }

  function renderTraining() {
    return '<section class="workbench-grid">' +
      renderCard('样本与数据集', '创建数据集', renderFieldGrid([
        ['数据集名称', '校园周边侵财风险_0518'],
        ['类别列表', 'multi_rider,no_helmet,gathering'],
        ['样本来源', '巡检命中 / 处置反馈'],
        ['复核策略', '仅确认样本进入训练'],
      ]) + renderChips(['AI 预标注', '人工复核', '负样本沉淀', '版本化导出'])) +
      renderCard('训练任务', '模型仓库', renderResultList([
        ['专项巡检 v1.8', 'mAP50 0.86 · 已发布', '线上'],
        ['校园周边 v0.3', 'Epoch 24 / 80', '训练中'],
        ['低光场景 v0.2', '等待 Worker', '排队'],
        ['误判样本回归集', '412 张 · 已复核', '可训练'],
      ])) +
      renderCard('发布门禁', '查看报告', renderTimeline([
        ['样本量', '确认样本不少于 500 张', 'success'],
        ['误检率', '不得高于当前线上模型', 'info'],
        ['审批', '发布前保留训练日志和评估图', 'warning'],
      ])) +
    '</section>';
  }

  function renderDiagnostics() {
    return '<section class="workbench-grid diagnostics-grid">' +
      renderCard('健康摘要', '刷新诊断', '<div class="workbench-health">' +
        renderHealth('Web 服务', '正常', 'green') +
        renderHealth('任务 Worker', '正常', 'green') +
        renderHealth('SQLite 队列', '轻微积压', 'amber') +
        renderHealth('模型文件', '缺少低光模型', 'red') +
      '</div>') +
      renderCard('最近队列任务', '清理陈旧任务', renderQueueList([
        ['detection', 'running', 'job_20260518_001', '12m'],
        ['upload', 'completed', 'job_20260518_002', '4m'],
        ['train', 'pending', 'job_20260518_003', '--'],
        ['auto_annotate', 'failed', 'job_20260517_119', '31m'],
      ])) +
      renderCard('修复建议', '导出日志', renderTimeline([
        ['建议一', '重试 auto_annotate 失败任务前先确认模型路径', 'warning'],
        ['建议二', 'Worker 正常但队列积压，可临时提高 batch_size', 'info'],
        ['建议三', '低光模型未配置，不影响通用巡检', 'success'],
      ])) +
    '</section>';
  }

  function renderCard(title, action, body) {
    return '<div class="card workbench-card">' +
      '<div class="card-head">' +
        '<span class="section-title">' + title + '</span>' +
        '<button class="btn-outline btn-sm">' + action + '</button>' +
      '</div>' +
      '<div class="workbench-card-body">' + body + '</div>' +
    '</div>';
  }

  function renderFieldGrid(fields) {
    return '<div class="workbench-field-grid">' + fields.map(function(pair) {
      return '<div class="workbench-field"><label>' + pair[0] + '</label><div class="workbench-input">' + pair[1] + '</div></div>';
    }).join('') + '</div>';
  }

  function renderChips(items) {
    return '<div class="workbench-chip-row">' + items.map(function(item) {
      return '<span class="workbench-chip">' + item + '</span>';
    }).join('') + '</div>';
  }

  function renderModuleStrip() {
    return '<div class="workbench-module-strip">' + NAV_ITEMS.map(function(item) {
      return '<div class="workbench-mini-module"><strong>' + item.title + '</strong><span>' + item.desc + '</span></div>';
    }).join('') + '</div>';
  }

  function renderQueueCard() {
    return renderCard('运行队列', '自动刷新', '<div class="workbench-job-list">' + JOBS.map(function(job) {
      return '<div class="workbench-job">' +
        '<span class="workbench-job-dot tone-bg-' + job.tone + '"></span>' +
        '<div><div class="workbench-job-name">' + job.name + '</div><div class="workbench-job-meta">' + job.meta + '</div></div>' +
        '<span class="workbench-status tone-' + job.tone + '">' + job.state + '</span>' +
      '</div>';
    }).join('') + '</div>');
  }

  function renderFlowCard() {
    return renderCard('闭环流转', '查看链路', '<div class="workbench-flow">' + FLOW.map(function(step, i) {
      return '<div class="workbench-flow-step">' +
        '<span class="workbench-step-num">' + (i + 1) + '</span>' +
        '<div><div class="workbench-step-title">' + step.title + '</div><div class="workbench-step-sub">' + step.sub + '</div></div>' +
        '<span class="workbench-step-state">' + step.state + '</span>' +
      '</div>';
    }).join('') + '</div>');
  }

  function renderResultList(items) {
    return '<div class="workbench-result-list">' + items.map(function(item) {
      return '<div class="workbench-result-item"><div><strong>' + item[0] + '</strong><span>' + item[1] + '</span></div><em>' + item[2] + '</em></div>';
    }).join('') + '</div>';
  }

  function renderTimeline(items) {
    return '<div class="workbench-timeline">' + items.map(function(item) {
      return '<div class="workbench-timeline-item tone-border-' + item[2] + '"><strong>' + item[0] + '</strong><span>' + item[1] + '</span></div>';
    }).join('') + '</div>';
  }

  function renderHealth(name, state, tone) {
    return '<div class="workbench-health-row"><span>' + name + '</span><strong class="tone-' + tone + '">' + state + '</strong></div>';
  }

  function renderQueueList(items) {
    return '<table class="workbench-table"><thead><tr><th>类型</th><th>状态</th><th>Job ID</th><th>耗时</th></tr></thead><tbody>' +
      items.map(function(item) {
        return '<tr><td>' + item[0] + '</td><td>' + item[1] + '</td><td>' + item[2] + '</td><td>' + item[3] + '</td></tr>';
      }).join('') +
    '</tbody></table>';
  }

  return { render: render, init: init, destroy: destroy };
})();

PageManager.register('workbench', WorkbenchPage);
