// ============================================================
// workbench.js - 统一工作台 (5 子页)
// 子页：oracle 数据巡检 / upload 本地素材 / dispatch 任务下发
//      train 模型训练 / diagnostics 系统诊断
// ============================================================

var WorkbenchPage = (function() {
  var charts = [];
  var activeTab = 'oracle';
  var selectedThumbs = new Set();
  var selectedQueue = null;

  // ============================================================
  // 演示数据
  // ============================================================
  var MODELS = ['yolov8n-pose-侵财行为v3', 'yolov8s-pose-侵财行为v2', 'yolo11m-detect-基线v1'];
  var PROMPT_PRESETS = ['夜间作案行为识别', '商业区可疑徘徊', 'ATM 附近滞留', '校园敲诈勒索', '群体共同出行'];

  var QUEUE_OBJECTS = [
    { name: '张某辉', area: '新城分局', risk: 'high' },
    { name: '李某阳', area: '新城分局', risk: 'high' },
    { name: '赵某杰', area: '雁塔分局', risk: 'extreme' },
    { name: '王某飞', area: '碑林分局', risk: 'medium' },
    { name: '陈某龙', area: '未央分局', risk: 'high' },
  ];

  var DATASETS = [
    { name: 'qz_intel_v3', count: 12450, labeled: 11200, reviewed: 9800, time: '2026-05-12' },
    { name: 'qz_intel_v2', count: 8230, labeled: 8230, reviewed: 8230, time: '2026-02-08' },
    { name: 'campus_extortion', count: 3500, labeled: 3120, reviewed: 2800, time: '2025-12-15' },
  ];

  var TRAINING_TASKS = [
    { name: 'qz_v3_yolov8n_e120', status: 'running',  progress: 67, time: '12:24:30' },
    { name: 'qz_v3_yolov8s_e80',  status: 'success',  progress: 100, time: '2026-05-14' },
    { name: 'campus_yolo11m_e60', status: 'failed',   progress: 24, time: '2026-05-13' },
    { name: 'qz_v2_yolov8n_e100', status: 'success',  progress: 100, time: '2026-05-10' },
  ];

  var QUEUE_DIAG = [
    { task: '夜间巡检 · 新城区',  status: 'success', jobId: 'job_8c4f2a31', duration: '00:23:45', owner: 'wuhan001', error: '' },
    { task: '校园周边研判',         status: 'running', jobId: 'job_a7b1c9e0', duration: '00:08:12', owner: 'wuhan001', error: '' },
    { task: 'ATM 高频区扫描',     status: 'failed',  jobId: 'job_3d2e8f54', duration: '00:01:33', owner: 'liming023', error: 'GPU 内存不足: CUDA out of memory' },
    { task: '商业街素材识别',      status: 'success', jobId: 'job_91a02d8c', duration: '00:15:20', owner: 'zhangwei', error: '' },
    { task: '辖区巡检 · 碑林',      status: 'waiting', jobId: 'job_5f6c4a82', duration: '--', owner: 'wuhan001', error: '' },
    { task: '历史回溯 · 4月',        status: 'stale',   status_label: '陈旧运行', jobId: 'job_27e3b1d4', duration: '03:42:00', owner: 'systemd', error: '心跳超时' },
    { task: '诈骗系列案串并',      status: 'success', jobId: 'job_8b4f7c20', duration: '00:42:08', owner: 'wuhan001', error: '' },
  ];

  var DISPATCH_AUDIT = [
    { time: '2026-05-16 14:23', type: '任务', target: '新城分局', content: '张某辉 重点管控', result: 'success' },
    { time: '2026-05-16 14:23', type: '短信', target: '138****5672', content: '管控通知', result: 'success' },
    { time: '2026-05-15 09:11', type: '任务', target: '雁塔分局', content: '赵某杰 立即核查', result: 'success' },
    { time: '2026-05-14 17:42', type: '短信', target: '139****8901', content: '协助通知',   result: 'failed' },
  ];

  // ============================================================
  // 通用组件 HTML
  // ============================================================
  function selectHTML(id, options, selected) {
    var opts = options.map(function(o) {
      return '<option value="' + o + '"' + (o === selected ? ' selected' : '') + '>' + o + '</option>';
    }).join('');
    return '<select class="wb-select" id="' + id + '">' + opts + '</select>';
  }

  function sliderHTML(id, min, max, val, step) {
    step = step || 1;
    var pct = (val - min) / (max - min) * 100;
    return '<div class="wb-slider-row">' +
      '<input type="range" class="wb-slider" id="' + id + '" min="' + min + '" max="' + max + '" step="' + step + '" value="' + val + '" style="--val:' + pct + '%">' +
      '<span class="wb-slider-val" id="' + id + '-val">' + val + '</span>' +
    '</div>';
  }

  function chipsHTML(targetId, presets) {
    return '<div class="wb-chips">' + presets.map(function(p) {
      return '<span class="wb-chip" data-target="' + targetId + '" data-val="' + p + '">+ ' + p + '</span>';
    }).join('') + '</div>';
  }

  function progressCard(label, percent, model) {
    return '<div class="card">' +
      '<div class="card-head"><span class="section-title">' + icon('activity',16) + ' ' + label + '</span></div>' +
      '<div class="wb-actions-row" style="margin-bottom:12px">' +
        '<span class="status-badge status-running">运行中</span>' +
        '<span class="status-badge status-waiting">' + (model || MODELS[0]) + '</span>' +
        '<span class="wb-result-meta">JOB: job_8c4f2a31</span>' +
      '</div>' +
      '<div class="glow-progress"><div class="glow-progress-fill" style="width:0%" data-target="' + percent + '%"></div></div>' +
      '<div class="wb-actions-row" style="margin-top:8px;justify-content:space-between">' +
        '<span class="glow-number" style="color:var(--accent-cyan);font-size:14px">' + percent + '%</span>' +
        '<span class="wb-result-meta">已处理 1,234 / 1,842 帧</span>' +
      '</div>' +
      '<div class="wb-divider"></div>' +
      '<div class="wb-actions-row">' +
        '<button class="btn-outline btn-sm">' + icon('download',14) + ' 下载摘要说明</button>' +
        '<button class="btn-outline btn-sm" style="color:#ef4444;border-color:rgba(239,68,68,0.3)">' + icon('stop',14) + ' 停止当前任务</button>' +
      '</div>' +
    '</div>';
  }

  function resultGridCard(count) {
    count = count || 12;
    if (count === 0) {
      return '<div class="card">' +
        '<div class="card-head"><span class="section-title">' + icon('image',16) + ' 结果图身份识别</span></div>' +
        emptyState('image', '暂无结果图', '运行巡检任务后，命中的结果图会出现在这里') +
      '</div>';
    }
    var thumbs = '';
    var rand = ['张某辉','李某阳','王某飞','赵某杰','陈某龙','未识别','刘某伟','周某浩'];
    for (var i = 0; i < count; i++) {
      var conf = (0.62 + Math.random() * 0.35).toFixed(2);
      var who = rand[i % rand.length];
      thumbs += '<div class="wb-result-thumb" data-idx="' + i + '">' +
        '<span style="position:absolute;font-size:32px;color:rgba(56,189,248,0.15)">' + icon('fileImage', 32) + '</span>' +
        '<div class="wb-result-thumb-check">' + icon('check', 12) + '</div>' +
        '<div class="wb-result-thumb-label"><span>' + who + '</span><span>' + conf + '</span></div>' +
      '</div>';
    }
    return '<div class="card">' +
      '<div class="card-head"><span class="section-title">' + icon('image',16) + ' 结果图身份识别</span><span class="wb-result-meta">命中 ' + count + ' 张</span></div>' +
      '<div class="wb-result-toolbar">' +
        '<button class="btn-outline btn-sm" data-action="select-all">全选</button>' +
        '<button class="btn-outline btn-sm" data-action="select-none">清空</button>' +
        '<span class="toolbar-spacer"></span>' +
        '<span class="wb-result-meta">已选 <span class="selected-count">0</span> / ' + count + '</span>' +
        '<button class="btn-outline btn-sm" data-action="add-dataset">' + icon('database',14) + ' 加入数据集</button>' +
        '<button class="btn-primary btn-sm" data-action="identify">' + icon('fingerprint',14) + ' 识别身份</button>' +
      '</div>' +
      '<div class="wb-result-grid">' + thumbs + '</div>' +
    '</div>';
  }

  // ============================================================
  // 子页 1: 数据巡检 (oracle)
  // ============================================================
  function renderOracle() {
    var now = new Date();
    var pad = function(n){ return String(n).padStart(2,'0'); };
    var endStr = now.getFullYear() + '-' + pad(now.getMonth()+1) + '-' + pad(now.getDate()) + 'T' + pad(now.getHours()) + ':' + pad(now.getMinutes());
    var startD = new Date(now - 7 * 24 * 3600 * 1000);
    var startStr = startD.getFullYear() + '-' + pad(startD.getMonth()+1) + '-' + pad(startD.getDate()) + 'T00:00';

    return '<div class="wb-2col-7-5">' +
      // Left column
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        // 配置卡
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('filter',16) + ' 配置检测参数</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col">' +
                '<label class="wb-form-label">开始时间<span class="req">*</span></label>' +
                '<input type="datetime-local" class="wb-input" id="oracle-start" value="' + startStr + '">' +
              '</div>' +
              '<div class="wb-form-row col">' +
                '<label class="wb-form-label">结束时间<span class="req">*</span></label>' +
                '<input type="datetime-local" class="wb-input" id="oracle-end" value="' + endStr + '">' +
              '</div>' +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">研判模型</label>' +
              selectHTML('oracle-model', MODELS, MODELS[0]) +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">检测提示词</label>' +
              '<textarea class="wb-textarea" id="oracle-prompt" placeholder="请输入研判提示词，描述需要识别的行为特征…">深夜在商业区域徘徊，多次接近店铺门锁；与已知高风险人员频繁接触。</textarea>' +
              '<div class="wb-form-label" style="margin-top:6px">常用预设</div>' +
              chipsHTML('oracle-prompt', PROMPT_PRESETS) +
            '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col">' +
                '<label class="wb-form-label">置信度阈值</label>' +
                sliderHTML('oracle-conf', 0, 100, 65) +
              '</div>' +
              '<div class="wb-2col">' +
                '<div class="wb-form-row col">' +
                  '<label class="wb-form-label">批大小</label>' +
                  '<input type="number" class="wb-input" value="32" min="1" max="128">' +
                '</div>' +
                '<div class="wb-form-row col">' +
                  '<label class="wb-form-label">图片尺寸</label>' +
                  '<input type="number" class="wb-input" value="640" min="320" max="1280" step="32">' +
                '</div>' +
              '</div>' +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<div class="wb-actions-row" style="justify-content:space-between">' +
                '<label class="wb-form-label">附加时段过滤</label>' +
                '<div class="wb-actions-row">' +
                  '<button class="btn-outline btn-sm" id="tw-add">' + icon('plus',12) + ' add</button>' +
                  '<button class="btn-outline btn-sm" id="tw-clear">清空</button>' +
                '</div>' +
              '</div>' +
              '<div class="wb-tw-list" id="tw-list">' +
                '<div class="wb-tw-row">' +
                  '<input type="time" class="wb-input" value="22:00">' +
                  '<span class="wb-tw-sep">至</span>' +
                  '<input type="time" class="wb-input" value="02:00">' +
                  '<div class="wb-tw-actions">' +
                    '<button class="wb-tw-icon-btn danger" data-remove>' + icon('minus',14) + '</button>' +
                  '</div>' +
                '</div>' +
              '</div>' +
            '</div>' +
            '<button class="btn-primary" style="align-self:flex-start;margin-top:4px">' + icon('play',14) + ' 开始巡检</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      // Right column
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        progressCard('任务进度', 67) +
        resultGridCard(12) +
      '</div>' +
    '</div>';
  }

  // ============================================================
  // 子页 2: 本地素材 (upload)
  // ============================================================
  function renderUpload() {
    return '<div class="wb-info-banner">' + icon('info',14) +
      '<span>办理提示：本地素材研判结果不会与公网数据库自动比对，请在「结果图身份识别」环节人工确认身份后再下发任务。每个素材包建议不超过 200 张图片或 30 秒视频。</span>' +
    '</div>' +
    '<div class="wb-2col-7-5">' +
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        // 上传卡
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('upload',16) + ' 上传现场素材</span></div>' +
          '<div class="wb-upload-zone" id="upload-zone">' +
            '<div class="wb-upload-icon">' + icon('upload', 36) + '</div>' +
            '<div class="wb-upload-title">点击选择文件，或将文件拖放至此</div>' +
            '<div class="wb-upload-sub">支持 JPG / PNG / MP4 / ZIP · 单文件最大 500MB</div>' +
          '</div>' +
          '<div class="wb-file-list" id="upload-files">' +
            '<div class="wb-file-item">' +
              '<span class="wb-file-icon">' + icon('fileImage',16) + '</span>' +
              '<span class="wb-file-name">site_20260516_2230.mp4</span>' +
              '<span class="wb-file-size">42.6 MB</span>' +
              '<button class="wb-file-remove">' + icon('x',14) + '</button>' +
            '</div>' +
            '<div class="wb-file-item">' +
              '<span class="wb-file-icon">' + icon('fileImage',16) + '</span>' +
              '<span class="wb-file-name">scene_capture_001.jpg</span>' +
              '<span class="wb-file-size">3.2 MB</span>' +
              '<button class="wb-file-remove">' + icon('x',14) + '</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        // 研判模型与参数
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('cpu',16) + ' 研判模型与参数</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">研判模型</label>' +
              selectHTML('up-model', MODELS, MODELS[0]) +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">检测提示词</label>' +
              '<textarea class="wb-textarea" id="up-prompt" placeholder="请输入研判提示词…"></textarea>' +
              '<div class="wb-form-label" style="margin-top:6px">常用预设</div>' +
              chipsHTML('up-prompt', PROMPT_PRESETS) +
            '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col">' +
                '<label class="wb-form-label">置信度阈值</label>' +
                sliderHTML('up-conf', 0, 100, 70) +
              '</div>' +
              '<div class="wb-form-row col">' +
                '<label class="wb-form-label">批大小</label>' +
                '<input type="number" class="wb-input" value="16">' +
              '</div>' +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">帧采样间隔（视频）</label>' +
              '<input type="number" class="wb-input" value="5" min="1" max="60">' +
              '<div class="wb-hint">每 N 帧采样一次，越小越精细但耗时增加</div>' +
            '</div>' +
            '<button class="btn-primary" style="align-self:flex-start">' + icon('zap',14) + ' 开始素材研判</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        progressCard('检测进度', 84) +
        resultGridCard(8) +
      '</div>' +
    '</div>';
  }

  // ============================================================
  // 子页 3: 任务下发 (dispatch)
  // ============================================================
  function renderDispatch() {
    var queueHtml = QUEUE_OBJECTS.map(function(q, i) {
      var c = RISK_CONFIG[q.risk];
      return '<div class="wb-queue-item" data-idx="' + i + '" style="border-left-color:' + c.color + '">' +
        '<span class="wb-queue-name">' + q.name + '</span>' +
        '<span class="wb-queue-meta">' + q.area + '</span>' +
        riskBadge(q.risk) +
      '</div>';
    }).join('');

    var auditRows = DISPATCH_AUDIT.map(function(a) {
      var statusCls = a.result === 'success' ? 'status-success' : 'status-failed';
      var statusLabel = a.result === 'success' ? '成功' : '失败';
      return '<tr>' +
        '<td class="mono col-meta">' + a.time + '</td>' +
        '<td>' + a.type + '</td>' +
        '<td>' + a.target + '</td>' +
        '<td class="truncate">' + a.content + '</td>' +
        '<td><span class="status-badge ' + statusCls + '">' + statusLabel + '</span></td>' +
      '</tr>';
    }).join('');

    return '<div class="wb-2col">' +
      // Left column
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        // 认证
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('lock',16) + ' 任务平台认证</span></div>' +
          '<div class="wb-actions-row" style="margin-bottom:12px">' +
            '<span class="status-badge status-unauth" id="auth-status">未认证</span>' +
            '<span class="wb-result-meta">Token 缓存时长：24h</span>' +
          '</div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-form-row"><label class="wb-form-label">平台账号</label><input type="text" class="wb-input" placeholder="请输入平台账号"></div>' +
            '<div class="wb-form-row"><label class="wb-form-label">平台密码</label><input type="password" class="wb-input" placeholder="请输入平台密码"></div>' +
          '</div>' +
          '<div class="wb-actions-row" style="margin-top:12px">' +
            '<button class="btn-outline btn-sm">' + icon('refresh',14) + ' 刷新状态</button>' +
            '<button class="btn-primary btn-sm" id="auth-btn">' + icon('check',14) + ' 认证并缓存 Token</button>' +
          '</div>' +
        '</div>' +
        // 待下发队列
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('list',16) + ' 待下发队列</span><span class="wb-result-meta">共 ' + QUEUE_OBJECTS.length + ' 人</span></div>' +
          '<div class="wb-actions-row" style="margin-bottom:10px">' +
            '<button class="btn-outline btn-sm">' + icon('refresh',14) + ' 刷新显示</button>' +
            '<button class="btn-outline btn-sm">' + icon('mapPin',14) + ' 重查属地</button>' +
          '</div>' +
          '<div class="wb-queue-list" id="dispatch-queue">' + queueHtml + '</div>' +
          '<div class="wb-collapse" id="auto-flow" style="margin-top:10px">' +
            '<div class="wb-collapse-head" onclick="this.parentNode.classList.toggle(\'open\')">' +
              '<span>' + icon('info',14) + ' 自动流转说明</span>' +
              '<span class="wb-collapse-arrow">' + icon('chevronRight',14) + '</span>' +
            '</div>' +
            '<div class="wb-collapse-body">' +
              '1. 任务下发后自动按属地匹配派出所代码；<br>' +
              '2. 24 小时内未签收将自动重新下发一次；<br>' +
              '3. 签收后启动反馈倒计时，逾期未反馈推送领导。' +
            '</div>' +
          '</div>' +
        '</div>' +
        // 短信提醒
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('phone',16) + ' 短信提醒配置</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-form-row"><label class="wb-form-label">短信号码</label><input type="text" class="wb-input" placeholder="138****5672，多个用逗号分隔"></div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">短信模板</label>' +
              '<textarea class="wb-textarea" id="sms-tpl">【未成年人侵财管控】{name}（{area}）已被列入重点管控，请于24小时内核实情况并反馈。</textarea>' +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">预览</label>' +
              '<div class="wb-sms-preview" id="sms-preview">请选择左侧待下发对象后预览短信内容</div>' +
            '</div>' +
          '</div>' +
          '<div class="wb-actions-row" style="margin-top:12px">' +
            '<button class="btn-outline btn-sm" id="sms-preview-btn">' + icon('eye',14) + ' 预览短信</button>' +
            '<button class="btn-primary btn-sm">' + icon('send',14) + ' 发送短信提醒</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      // Right column
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        // 草稿
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('fileText',16) + ' 任务下发草稿</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col"><label class="wb-form-label">任务标题</label><input type="text" class="wb-input" value="未成年人重点管控通知"></div>' +
              '<div class="wb-form-row col"><label class="wb-form-label">业务负责人</label><input type="text" class="wb-input" value="武汉同志"></div>' +
            '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col"><label class="wb-form-label">负责人电话</label><input type="text" class="wb-input" value="13800138000"></div>' +
              '<div class="wb-form-row col"><label class="wb-form-label">签收时限（小时）</label><input type="number" class="wb-input" value="24"></div>' +
            '</div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">任务内容</label>' +
              '<textarea class="wb-textarea">请贵单位对名单中未成年人开展核查走访，落实监护人责任，建立"一人一档"管控台账。</textarea>' +
            '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col"><label class="wb-form-label">开始时间</label><input type="datetime-local" class="wb-input" value="2026-05-17T08:00"></div>' +
              '<div class="wb-form-row col"><label class="wb-form-label">截止时间</label><input type="datetime-local" class="wb-input" value="2026-05-24T18:00"></div>' +
            '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col"><label class="wb-form-label">反馈时限（小时）</label><input type="number" class="wb-input" value="168"></div>' +
              '<div class="wb-form-row col"><label class="wb-form-label">市局代码 / 名称</label><input type="text" class="wb-input" value="6101 / 西安市公安局"></div>' +
            '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col"><label class="wb-form-label">分局代码 / 名称</label><input type="text" class="wb-input" value="610102 / 新城分局"></div>' +
              '<div class="wb-form-row col"><label class="wb-form-label">派出所代码 / 名称</label><input type="text" class="wb-input" value="610102001 / 解放门派出所"></div>' +
            '</div>' +
            '<div class="wb-form-row col"><label class="wb-form-label">地址</label><input type="text" class="wb-input" value="西安市新城区解放路 XX 号"></div>' +
          '</div>' +
        '</div>' +
        // JSON 负载
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('code',16) + ' 下发负载 (JSON)</span></div>' +
          '<div class="wb-json-wrap">' +
            '<div class="wb-json-header">' +
              '<span class="wb-json-title">' + icon('code',12) + ' payload.json</span>' +
              '<div class="wb-json-actions">' +
                '<button>' + icon('rotate',12) + ' 恢复精简默认</button>' +
                '<button>' + icon('sparkles',12) + ' 格式化 JSON</button>' +
                '<button>' + icon('refresh',12) + ' 重新生成草稿</button>' +
              '</div>' +
            '</div>' +
            '<div class="wb-json-body">' +
              '<div class="wb-json-gutter" id="json-gutter"></div>' +
              '<pre class="wb-json-code" id="json-code"></pre>' +
            '</div>' +
          '</div>' +
          '<div class="wb-actions-row" style="margin-top:12px;justify-content:flex-end">' +
            '<button class="btn-outline btn-sm">' + icon('copy',14) + ' 复制 JSON</button>' +
            '<button class="btn-primary">' + icon('send',14) + ' 通过任务平台下发</button>' +
          '</div>' +
        '</div>' +
        // 审计记录
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('clipboard',16) + ' 审计记录</span>' +
            '<button class="btn-outline btn-sm">' + icon('refresh',14) + ' 刷新记录</button>' +
          '</div>' +
          '<div class="wb-table-wrap">' +
            '<table class="wb-table"><thead><tr>' +
              '<th>时间</th><th>类型</th><th>目标</th><th>内容</th><th>结果</th>' +
            '</tr></thead><tbody>' + auditRows + '</tbody></table>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';
  }

  // ============================================================
  // 子页 4: 模型训练 (train)
  // ============================================================
  function renderTrain() {
    var dsRows = DATASETS.map(function(d) {
      return '<tr>' +
        '<td><strong>' + d.name + '</strong></td>' +
        '<td class="mono">' + formatNum(d.count) + '</td>' +
        '<td class="mono">' + formatNum(d.labeled) + '</td>' +
        '<td class="mono">' + formatNum(d.reviewed) + '</td>' +
        '<td class="mono col-meta">' + d.time + '</td>' +
      '</tr>';
    }).join('');

    var taskRows = TRAINING_TASKS.map(function(t) {
      var statusCls = 'status-' + t.status;
      var labelMap = { running:'运行中', success:'成功', failed:'失败', waiting:'等待中' };
      return '<tr>' +
        '<td><strong>' + t.name + '</strong></td>' +
        '<td><span class="status-badge ' + statusCls + '">' + labelMap[t.status] + '</span></td>' +
        '<td><div class="glow-progress" style="width:120px"><div class="glow-progress-fill" style="width:' + t.progress + '%"></div></div></td>' +
        '<td class="mono col-meta">' + t.time + '</td>' +
      '</tr>';
    }).join('');

    return '<div class="wb-mini-stats">' +
      '<div class="wb-mini-stat"><div class="wb-mini-stat-label">数据集</div><div class="wb-mini-stat-val glow-num-target" data-target="3">0</div></div>' +
      '<div class="wb-mini-stat"><div class="wb-mini-stat-label">图片数</div><div class="wb-mini-stat-val glow-num-target" data-target="24180">0</div></div>' +
      '<div class="wb-mini-stat"><div class="wb-mini-stat-label">已标注</div><div class="wb-mini-stat-val glow-num-target" data-target="22550">0</div></div>' +
      '<div class="wb-mini-stat"><div class="wb-mini-stat-label">已复核</div><div class="wb-mini-stat-val glow-num-target" data-target="20830">0</div></div>' +
    '</div>' +
    '<div class="wb-2col">' +
      // Left column
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        // 样本沉淀
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('database',16) + ' 样本沉淀与数据集管理</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-form-row col"><label class="wb-form-label">数据集名称</label><input type="text" class="wb-input" placeholder="qz_intel_v4"></div>' +
            '<div class="wb-form-row col">' +
              '<label class="wb-form-label">类别列表（逗号分隔）</label>' +
              '<input type="text" class="wb-input" placeholder="no_helmet,wheelie,multi_rider">' +
            '</div>' +
            '<div class="wb-form-row col"><label class="wb-form-label">备注</label><textarea class="wb-textarea" rows="2" placeholder="本数据集用途简述…"></textarea></div>' +
            '<button class="btn-primary" style="align-self:flex-start">' + icon('plus',14) + ' 创建数据集</button>' +
          '</div>' +
        '</div>' +
        // 批量导入
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('upload',16) + ' 批量导入图片</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-form-row"><label class="wb-form-label">目标数据集</label>' + selectHTML('train-ds', DATASETS.map(function(d){return d.name;})) + '</div>' +
            '<div class="wb-form-row"><label class="wb-form-label">ZIP 文件</label><input type="text" class="wb-input" placeholder="选择 ZIP 文件…" readonly></div>' +
            '<button class="btn-primary" style="align-self:flex-start">' + icon('package',14) + ' 导入 ZIP</button>' +
          '</div>' +
        '</div>' +
        // 数据集列表
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('list',16) + ' 数据集列表</span><button class="btn-outline btn-sm">' + icon('refresh',14) + ' 刷新</button></div>' +
          '<div class="wb-table-wrap">' +
            '<table class="wb-table"><thead><tr><th>名称</th><th>图片数</th><th>已标注</th><th>已复核</th><th>更新时间</th></tr></thead>' +
            '<tbody>' + dsRows + '</tbody></table>' +
          '</div>' +
        '</div>' +
      '</div>' +
      // Right column
      '<div style="display:flex;flex-direction:column;gap:14px">' +
        // 训练任务
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('zap',16) + ' 发起训练任务</span></div>' +
          '<div class="wb-form-grid">' +
            '<div class="wb-form-row"><label class="wb-form-label">训练数据集</label>' + selectHTML('t-ds', DATASETS.map(function(d){return d.name;})) + '</div>' +
            '<div class="wb-form-row"><label class="wb-form-label">基础模型</label>' + selectHTML('t-base', ['yolov8n.pt','yolov8s.pt','yolov8m.pt','yolo11n.pt','yolo11s.pt']) + '</div>' +
            '<div class="wb-form-row"><label class="wb-form-label">训练预设</label>' + selectHTML('t-preset', ['standard (默认)','fast (快速验证)','high-accuracy (高精度)']) + '</div>' +
            '<div class="wb-2col">' +
              '<div class="wb-form-row col"><label class="wb-form-label">Epochs</label><input type="number" class="wb-input" value="120"></div>' +
              '<div class="wb-form-row col"><label class="wb-form-label">imgsz</label><input type="number" class="wb-input" value="640"></div>' +
            '</div>' +
            '<div class="wb-form-row col"><label class="wb-form-label">Batch</label><input type="number" class="wb-input" value="32"></div>' +
            '<div class="wb-actions-row">' +
              '<button class="btn-outline btn-sm">' + icon('refresh',14) + ' 刷新任务</button>' +
              '<button class="btn-primary">' + icon('zap',14) + ' 创建训练任务</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        // 最近训练
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('activity',16) + ' 最近训练任务</span><button class="btn-outline btn-sm">' + icon('refresh',14) + ' 刷新</button></div>' +
          '<div class="wb-table-wrap">' +
            '<table class="wb-table"><thead><tr><th>任务名称</th><th>状态</th><th>进度</th><th>时间</th></tr></thead>' +
            '<tbody>' + taskRows + '</tbody></table>' +
          '</div>' +
        '</div>' +
        // 模型版本管理
        '<div class="card">' +
          '<div class="card-head"><span class="section-title">' + icon('layers',16) + ' 模型版本管理</span></div>' +
          '<div class="wb-entry-block">' +
            '<span class="wb-entry-icon">' + icon('package', 32) + '</span>' +
            '<div class="wb-entry-text">' +
              '<strong>已注册 8 个模型版本</strong><br>' +
              '管理模型版本、查看训练指标、发布上线、灰度切换与回滚操作。' +
            '</div>' +
            '<button class="btn-primary btn-sm">' + icon('arrowRight',14) + ' 管理页</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';
  }

  // ============================================================
  // 子页 5: 系统诊断 (diagnostics)
  // ============================================================
  function renderDiagnostics() {
    var stats = [
      { label:'队列总数', value:42, color:'#94a3b8', icon:'list', cls:'' },
      { label:'等待中',   value:8,  color:'#94a3b8', icon:'clock', cls:'' },
      { label:'运行中',   value:5,  color:'#38bdf8', icon:'activity', cls:'' },
      { label:'失败',     value:3,  color:'#ef4444', icon:'alertCircle', cls:'' },
      { label:'陈旧运行', value:1,  color:'#f97316', icon:'alertTriangle', cls:'' },
    ];
    var statHtml = stats.map(function(s) {
      return '<div class="wb-stat-card" style="border-left-color:' + s.color + '">' +
        '<div class="wb-stat-label"><span style="color:' + s.color + '">' + icon(s.icon,13) + '</span>' + s.label + '</div>' +
        '<div class="wb-stat-value glow-num-target" data-target="' + s.value + '" style="color:' + s.color + '">0</div>' +
      '</div>';
    }).join('');

    var healthItems = [
      { dot:'#22c55e', key:'API 服务',         val:'在线 · 延迟 12ms' },
      { dot:'#22c55e', key:'数据库连接',         val:'正常 · 5/100 连接' },
      { dot:'#22c55e', key:'Redis 缓存',        val:'在线 · 命中率 94.2%' },
      { dot:'#22c55e', key:'ECharts 渲染',      val:'正常' },
      { dot:'#f97316', key:'GPU 推理服务',      val:'1 节点心跳异常' },
      { dot:'#22c55e', key:'对象存储',          val:'正常 · 已用 38%' },
      { dot:'#ef4444', key:'外部任务平台 Token',  val:'未认证' },
    ];
    var healthHtml = healthItems.map(function(h) {
      return '<div class="wb-health-item">' +
        '<span class="wb-health-dot" style="background:' + h.dot + ';box-shadow:0 0 6px ' + h.dot + '99"></span>' +
        '<span class="wb-health-key">' + h.key + '</span>' +
        '<span class="wb-health-val">' + h.val + '</span>' +
      '</div>';
    }).join('');

    var queueRows = QUEUE_DIAG.map(function(q) {
      var statusCls = 'status-' + (q.status === 'stale' ? 'stale' : q.status);
      var labelMap = { running:'运行中', success:'成功', failed:'失败', waiting:'等待中', stale:'陈旧运行' };
      return '<tr>' +
        '<td><strong>' + q.task + '</strong></td>' +
        '<td><span class="status-badge ' + statusCls + '">' + labelMap[q.status] + '</span></td>' +
        '<td class="mono col-meta">' + q.jobId + '</td>' +
        '<td class="mono">' + q.duration + '</td>' +
        '<td class="col-meta">' + q.owner + '</td>' +
        '<td class="truncate" style="color:#ef4444" title="' + q.error + '">' + (q.error || '—') + '</td>' +
      '</tr>';
    }).join('');

    var summaryRow = '<tr><td colspan="6">' +
      '<div class="wb-actions-row" style="font-size:11px;color:var(--text-muted)">' +
        '<span>聚合：</span>' +
        '<span class="status-badge status-running">运行中 5</span>' +
        '<span class="status-badge status-waiting">等待 8</span>' +
        '<span class="status-badge status-success">成功 25</span>' +
        '<span class="status-badge status-failed">失败 3</span>' +
        '<span class="status-badge status-stale">陈旧 1</span>' +
      '</div>' +
    '</td></tr>';

    return '<div class="card-head" style="margin-bottom:0;border:none;padding:0;display:flex;justify-content:space-between;align-items:center">' +
      '<span class="section-title" style="font-size:14px;letter-spacing:2px">' + icon('serverIcon',16) + ' 任务队列诊断</span>' +
      '<button class="btn-primary btn-sm">' + icon('refresh',14) + ' 刷新诊断</button>' +
    '</div>' +
    '<div class="wb-stat-strip">' + statHtml + '</div>' +
    '<div class="wb-2col">' +
      '<div class="card">' +
        '<div class="card-head"><span class="section-title">' + icon('heart',16) + ' 系统健康</span>' +
          '<span class="status-badge status-running">整体状态 · 轻微异常</span>' +
        '</div>' +
        '<div class="wb-health-list">' + healthHtml + '</div>' +
      '</div>' +
      '<div class="card">' +
        '<div class="card-head"><span class="section-title">' + icon('target',16) + ' 任务状态分布</span></div>' +
        '<div id="chart-diag-pie" style="width:100%;height:220px"></div>' +
      '</div>' +
    '</div>' +
    '<div class="card">' +
      '<div class="card-head"><span class="section-title">' + icon('list',16) + ' 最近队列任务</span>' +
        '<span class="wb-result-meta">最近 24 小时 · 共 42 条</span>' +
      '</div>' +
      '<div class="wb-table-wrap">' +
        '<table class="wb-table"><thead><tr>' +
          '<th>任务</th><th>状态</th><th>Job ID</th><th>耗时</th><th>Owner</th><th>错误</th>' +
        '</tr></thead><tbody>' + queueRows + '</tbody><tfoot>' + summaryRow + '</tfoot></table>' +
      '</div>' +
    '</div>';
  }

  // ============================================================
  // 主渲染 + 子页切换
  // ============================================================
  var SUBPAGES = [
    { id: 'oracle',     label: '数据巡检', icon: 'search',    render: renderOracle },
    { id: 'upload',     label: '本地素材', icon: 'upload',    render: renderUpload },
    { id: 'dispatch',   label: '任务下发', icon: 'send',      render: renderDispatch },
    { id: 'train',      label: '模型训练', icon: 'cpu',       render: renderTrain },
    { id: 'diagnostics', label: '系统诊断', icon: 'serverIcon', render: renderDiagnostics },
  ];

  function render(container) {
    var subnav = SUBPAGES.map(function(p) {
      return '<button class="wb-subnav-tab' + (p.id === activeTab ? ' active' : '') + '" data-subtab="' + p.id + '">' +
        icon(p.icon, 16) + ' ' + p.label +
      '</button>';
    }).join('');

    var subpages = SUBPAGES.map(function(p) {
      return '<div class="wb-subpage' + (p.id === activeTab ? ' active' : '') + '" id="wb-sub-' + p.id + '">' +
        p.render() +
      '</div>';
    }).join('');

    container.innerHTML =
      '<div class="wb-subnav">' + subnav + '</div>' +
      '<div class="wb-body">' + subpages + '</div>';
  }

  // ============================================================
  // 初始化 / 交互
  // ============================================================
  function init() {
    // 子导航切换
    delegate(document.querySelector('.wb-subnav'), '.wb-subnav-tab', 'click', function(e, btn) {
      var id = btn.dataset.subtab;
      document.querySelectorAll('.wb-subnav-tab').forEach(function(t) { t.classList.remove('active'); });
      btn.classList.add('active');
      document.querySelectorAll('.wb-subpage').forEach(function(s) { s.classList.remove('active'); });
      document.getElementById('wb-sub-' + id).classList.add('active');
      activeTab = id;
      // 重新初始化该子页的交互
      afterSwitch(id);
    });

    afterSwitch(activeTab);

    // 全局事件（事件委托到 wb-body）
    var body = document.querySelector('.wb-body');

    // chips 点击 → 追加到目标 textarea
    delegate(body, '.wb-chip', 'click', function(e, chip) {
      var t = document.getElementById(chip.dataset.target);
      if (t) {
        var v = t.value;
        t.value = (v && !v.endsWith('；') && !v.endsWith('\n') ? v + '；' : v) + chip.dataset.val;
      }
    });

    // sliders → 实时更新 val 显示与渐变填充
    delegate(body, '.wb-slider', 'input', function(e, sl) {
      var pct = (sl.value - sl.min) / (sl.max - sl.min) * 100;
      sl.style.setProperty('--val', pct + '%');
      var valEl = document.getElementById(sl.id + '-val');
      if (valEl) valEl.textContent = sl.value;
    });

    // 时段过滤 add/remove/clear
    delegate(body, '#tw-add', 'click', function() {
      var list = document.getElementById('tw-list');
      var row = document.createElement('div');
      row.className = 'wb-tw-row';
      row.innerHTML = '<input type="time" class="wb-input" value="20:00">' +
        '<span class="wb-tw-sep">至</span>' +
        '<input type="time" class="wb-input" value="23:00">' +
        '<div class="wb-tw-actions"><button class="wb-tw-icon-btn danger" data-remove>' + icon('minus',14) + '</button></div>';
      list.appendChild(row);
    });
    delegate(body, '[data-remove]', 'click', function(e, btn) {
      btn.closest('.wb-tw-row').remove();
    });
    delegate(body, '#tw-clear', 'click', function() {
      document.getElementById('tw-list').innerHTML = '';
    });

    // 结果图选中
    delegate(body, '.wb-result-thumb', 'click', function(e, thumb) {
      thumb.classList.toggle('selected');
      updateSelectedCount(thumb.closest('.card'));
    });
    delegate(body, '[data-action="select-all"]', 'click', function(e, btn) {
      var card = btn.closest('.card');
      card.querySelectorAll('.wb-result-thumb').forEach(function(t) { t.classList.add('selected'); });
      updateSelectedCount(card);
    });
    delegate(body, '[data-action="select-none"]', 'click', function(e, btn) {
      var card = btn.closest('.card');
      card.querySelectorAll('.wb-result-thumb').forEach(function(t) { t.classList.remove('selected'); });
      updateSelectedCount(card);
    });

    // 待下发队列选中
    delegate(body, '.wb-queue-item', 'click', function(e, item) {
      item.parentNode.querySelectorAll('.wb-queue-item').forEach(function(i) { i.classList.remove('selected'); });
      item.classList.add('selected');
      selectedQueue = parseInt(item.dataset.idx);
      // 自动更新短信预览
      updateSmsPreview();
    });

    // 短信预览
    delegate(body, '#sms-preview-btn', 'click', updateSmsPreview);

    // 文件移除
    delegate(body, '.wb-file-remove', 'click', function(e, btn) {
      btn.closest('.wb-file-item').remove();
    });

    // 认证按钮
    delegate(body, '#auth-btn', 'click', function() {
      var s = document.getElementById('auth-status');
      s.textContent = '已认证';
      s.className = 'status-badge status-online';
    });
  }

  function updateSelectedCount(card) {
    var sel = card.querySelectorAll('.wb-result-thumb.selected').length;
    var el = card.querySelector('.selected-count');
    if (el) el.textContent = sel;
  }

  function updateSmsPreview() {
    var tpl = document.getElementById('sms-tpl');
    var preview = document.getElementById('sms-preview');
    if (!tpl || !preview) return;
    if (selectedQueue === null) {
      preview.textContent = '请选择左侧待下发对象后预览短信内容';
      preview.style.color = 'var(--text-muted)';
      return;
    }
    var obj = QUEUE_OBJECTS[selectedQueue];
    preview.textContent = tpl.value.replace('{name}', obj.name).replace('{area}', obj.area);
    preview.style.color = 'var(--text-primary)';
  }

  // 在子页切换或首次进入时触发该子页的额外初始化
  function afterSwitch(id) {
    // 进度条动画
    setTimeout(function() {
      document.querySelectorAll('#wb-sub-' + id + ' .glow-progress-fill').forEach(function(bar) {
        if (bar.dataset.target) bar.style.width = bar.dataset.target;
      });
    }, 50);

    // 数字滚动 (训练页/诊断页统计)
    document.querySelectorAll('#wb-sub-' + id + ' .glow-num-target').forEach(function(el) {
      if (el.dataset.animated) return;
      el.dataset.animated = '1';
      animateNumber(el, parseFloat(el.dataset.target), 1200);
    });

    // JSON 高亮 (dispatch 页)
    if (id === 'dispatch') renderJSON();

    // 诊断分布饼图
    if (id === 'diagnostics') renderDiagPie();
  }

  function renderJSON() {
    var code = document.getElementById('json-code');
    var gutter = document.getElementById('json-gutter');
    if (!code) return;
    var obj = {
      task_title: '未成年人重点管控通知',
      owner: '武汉同志',
      owner_phone: '13800138000',
      content: '请贵单位对名单中未成年人开展核查走访…',
      start_time: '2026-05-17T08:00:00',
      end_time: '2026-05-24T18:00:00',
      receipt_hours: 24,
      feedback_hours: 168,
      city: { code: '6101', name: '西安市公安局' },
      district: { code: '610102', name: '新城分局' },
      station: { code: '610102001', name: '解放门派出所' },
      targets: [
        { name: '张某辉', id_card: '610102****', risk: 'high' },
        { name: '李某阳', id_card: '610102****', risk: 'high' }
      ]
    };
    var jsonStr = JSON.stringify(obj, null, 2);
    var highlighted = jsonStr
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/("[^"]+")(\s*:)/g, '<span class="json-key">$1</span>$2')
      .replace(/:\s*("[^"]+")/g, ': <span class="json-str">$1</span>')
      .replace(/:\s*(\d+)/g, ': <span class="json-num">$1</span>')
      .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
      .replace(/:\s*null/g, ': <span class="json-null">null</span>');
    code.innerHTML = highlighted;
    var lines = jsonStr.split('\n').length;
    var gh = '';
    for (var i = 1; i <= lines; i++) gh += '<div>' + i + '</div>';
    gutter.innerHTML = gh;
  }

  function renderDiagPie() {
    var el = document.getElementById('chart-diag-pie');
    if (!el) return;
    var chart = echarts.init(el);
    charts.push(chart);
    var data = [
      { value: 25, name: '成功', itemStyle: { color: '#22c55e' } },
      { value: 8,  name: '等待中', itemStyle: { color: '#94a3b8' } },
      { value: 5,  name: '运行中', itemStyle: { color: '#38bdf8' } },
      { value: 3,  name: '失败',   itemStyle: { color: '#ef4444' } },
      { value: 1,  name: '陈旧',   itemStyle: { color: '#f97316' } },
    ];
    var total = data.reduce(function(s,d){return s+d.value;}, 0);
    chart.setOption(Object.assign({}, echartBaseOption(), {
      tooltip: Object.assign({}, echartBaseOption().tooltip, { trigger:'item', formatter:'{b}: {c} ({d}%)' }),
      series: [{
        type:'pie', radius:['45%','70%'], center:['50%','55%'],
        data: data,
        label:{ show:true, color:'#94a3b8', fontSize:11, formatter:'{b}\n{d}%' },
        labelLine:{ lineStyle:{ color:'rgba(148,163,184,0.3)' } },
        emphasis:{ scaleSize:6 },
        animationDuration: 800,
      }],
      graphic: [{
        type:'group', left:'center', top:'50%',
        children: [
          { type:'text', style:{ text: formatNum(total), fill:'#e6edf7', fontSize:22, fontWeight:'bold', fontFamily:'ui-monospace,"SF Mono",Consolas,monospace', textAlign:'center', textVerticalAlign:'bottom' }, left:'center', top:-8 },
          { type:'text', style:{ text:'总任务', fill:'#5b6b80', fontSize:11, textAlign:'center', textVerticalAlign:'top' }, left:'center', top:8 },
        ],
      }],
    }));

    var resizeHandler = debounce(function(){ if(!chart.isDisposed()) chart.resize(); }, 200);
    window.addEventListener('resize', resizeHandler);
  }

  function destroy() {
    charts.forEach(function(c) { if (!c.isDisposed()) c.dispose(); });
    charts = [];
    selectedQueue = null;
  }

  return { render: render, init: init, destroy: destroy };
})();

PageManager.register('workbench', WorkbenchPage);
