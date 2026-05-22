// ============================================================
// profile.js - 个人画像 Profile
// ============================================================

var ProfilePage = (function() {
  var charts = [];

  // ---- 演示数据 ----
  var PERSON = {
    name: '张某辉', gender: '男', age: 16, idCard: '610102200812****',
    huji: '陕西省西安市新城区', riskScore: 78, riskLevel: 'high',
    avatar: null,
    dimensions: { case: 24, behavior: 18, family: 16, education: 12, social: 8 },
    dimMax:     { case: 30, behavior: 25, family: 20, education: 15, social: 10 },
  };

  var CASES = [
    { time: '2026-03-15', name: '新城区系列盗窃案', reason: '盗窃', unit: '新城分局刑侦大队' },
    { time: '2025-11-22', name: '碑林区电动车盗窃案', reason: '盗窃', unit: '碑林分局刑侦大队' },
    { time: '2025-08-07', name: '雁塔区商场扒窃案', reason: '盗窃', unit: '雁塔分局派出所' },
    { time: '2025-04-12', name: '未央区敲诈勒索案', reason: '敲诈勒索', unit: '未央分局刑侦大队' },
  ];

  var BEHAVIORS = [
    { time: '2026-05-16 22:30', desc: '深夜在商业街区域徘徊，多次接近店铺门锁', place: '新城区东大街商圈' },
    { time: '2026-05-12 01:15', desc: '凌晨在ATM取款区逗留约40分钟', place: '碑林区南稍门建行ATM' },
    { time: '2026-05-08 23:45', desc: '与已知高风险人员李某阳在网吧会面', place: '雁塔区某网吧' },
    { time: '2026-04-28 20:10', desc: '携带可疑工具在居民区出现', place: '新城区幸福路小区' },
    { time: '2026-04-15 19:30', desc: '在学校周边向低年级学生索要财物', place: '碑林区某中学门口' },
  ];

  var TOP_PLACES = [
    { place: '新城区东大街商圈', count: 23 },
    { place: '碑林区南稍门', count: 18 },
    { place: '雁塔区小寨', count: 14 },
    { place: '未央区凤城五路', count: 9 },
    { place: '新城区幸福路', count: 7 },
  ];

  var HOUR_DATA = [1,0,2,1,0,0,0,1,3,5,4,3,2,4,5,6,8,7,9,12,15,11,8,4];

  var FAMILY = {
    guardian: '张某国（父亲）', phone: '138****5672',
    situation: '离异家庭，父亲外出务工',
    difficulty: '低保家庭', childType: '困境儿童',
  };

  var EDUCATION = {
    status: '辍学', school: '西安市第XX中学',
    detail: '2025年9月起未到校，联系家长无有效反馈',
  };

  var ASSOCIATES = [
    { name: '李某阳', times: 5, risk: 'high' },
    { name: '王某飞', times: 3, risk: 'medium' },
    { name: '赵某杰', times: 2, risk: 'extreme' },
  ];

  var HOTELS = [
    { hotel: '新城区某快捷酒店', time: '2026-05-10 23:20', companion: '李某阳' },
    { hotel: '碑林区某旅馆', time: '2026-04-22 22:45', companion: '无' },
  ];

  var SUGGESTIONS = [
    '建议列入重点管控名单，加强日常巡查和轨迹监控',
    '联系其父亲张某国，督促履行监护职责',
    '协调教育部门，推动复学或职业培训安置',
    '关注其与李某阳、赵某杰的交往，防止团伙作案',
    '定期开展谈话教育，评估心理状态和行为变化',
  ];

  // ---- 头像生成 ----
  function avatarHTML(name, size) {
    size = size || 72;
    var firstChar = name ? name.charAt(0) : '?';
    return '<div class="avatar-circle" style="width:' + size + 'px;height:' + size + 'px;font-size:' + (size * 0.4) + 'px">' + firstChar + '</div>';
  }

  // ---- 风险分进度条 ----
  function riskProgressBar(score) {
    var level = score >= 80 ? 'extreme' : score >= 60 ? 'high' : score >= 40 ? 'medium' : score >= 20 ? 'low' : 'normal';
    var c = RISK_CONFIG[level];
    return '<div class="risk-progress">' +
      '<div class="risk-progress-bar" style="width:0%;background:' + c.color + ';box-shadow:0 0 10px ' + c.color + '40" data-target-width="' + score + '%"></div>' +
      '<span class="risk-progress-label" style="color:' + c.color + '">' + score + ' / 100</span>' +
    '</div>';
  }

  // ---- 维度小卡片 ----
  function dimCards(dims, maxes) {
    var labels = { case:'案件', behavior:'行为', family:'家庭', education:'教育', social:'社交' };
    var colors = { case:'#ef4444', behavior:'#f97316', family:'#eab308', education:'#3b82f6', social:'#38bdf8' };
    var html = '';
    Object.keys(dims).forEach(function(k) {
      var pct = Math.round(dims[k] / maxes[k] * 100);
      html += '<div class="dim-card">' +
        '<div class="dim-label">' + labels[k] + '</div>' +
        '<div class="dim-value" style="color:' + colors[k] + '">' + dims[k] + '<span class="dim-max">/' + maxes[k] + '</span></div>' +
        '<div class="dim-bar-track"><div class="dim-bar-fill" style="width:' + pct + '%;background:' + colors[k] + '"></div></div>' +
      '</div>';
    });
    return html;
  }

  // ---- 教育状态标签 ----
  function eduTag(status) {
    var map = { '辍学':'#ef4444', '流失':'#f97316', '旷课':'#eab308', '在校':'#22c55e', '未知':'#5b6b80' };
    var c = map[status] || '#5b6b80';
    return '<span class="edu-tag" style="background:' + c + '20;color:' + c + ';border:1px solid ' + c + '40">' + status + '</span>';
  }

  // ---- 渲染 ----
  function render(container) {
    var p = PERSON;
    var rc = RISK_CONFIG[p.riskLevel];

    container.innerHTML =
      // 顶部画像卡
      '<div class="card profile-header-card">' +
        '<div class="profile-top">' +
          '<div class="profile-left">' +
            avatarHTML(p.name, 72) +
            '<div class="profile-info">' +
              '<div class="profile-name-row">' +
                '<span class="profile-name">' + p.name + '</span>' +
                riskBadge(p.riskLevel) +
              '</div>' +
              '<div class="profile-meta">' + p.gender + ' · ' + p.age + '岁</div>' +
              '<div class="profile-meta">' + icon('fingerprint',14) + ' ' + p.idCard + ' · ' + p.huji + '</div>' +
              riskProgressBar(p.riskScore) +
            '</div>' +
          '</div>' +
          '<div class="profile-dims">' + dimCards(p.dimensions, p.dimMax) + '</div>' +
          '<button class="btn-primary profile-graph-btn" onclick="PageManager.switchTo(\'graph\')">' +
            icon('network', 16) + ' 展开关系图谱' +
          '</button>' +
        '</div>' +
      '</div>' +

      // 主内容区
      '<div class="profile-body">' +
        // 左栏
        '<div class="profile-main">' +
          // 涉案记录
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('folder',16) + ' 涉案记录</span></div>' +
            '<div class="timeline">' + CASES.map(function(c) {
              return '<div class="timeline-item">' +
                '<div class="timeline-dot"></div>' +
                '<div class="timeline-content">' +
                  '<div class="timeline-time">' + c.time + '</div>' +
                  '<div class="timeline-title">' + c.name + ' <span class="timeline-tag">' + c.reason + '</span></div>' +
                  '<div class="timeline-sub">' + icon('building',13) + ' ' + c.unit + '</div>' +
                '</div></div>';
            }).join('') + '</div>' +
          '</div>' +

          // 行为记录
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('activity',16) + ' 行为记录</span></div>' +
            '<div class="timeline">' + BEHAVIORS.map(function(b) {
              return '<div class="timeline-item">' +
                '<div class="timeline-dot" style="background:#f97316"></div>' +
                '<div class="timeline-content">' +
                  '<div class="timeline-time">' + b.time + '</div>' +
                  '<div class="timeline-title">' + b.desc + '</div>' +
                  '<div class="timeline-sub">' + icon('mapPin',13) + ' ' + b.place + '</div>' +
                '</div></div>';
            }).join('') + '</div>' +
          '</div>' +

          // 轨迹分析
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('mapPin',16) + ' 轨迹分析</span></div>' +
            '<div class="trajectory-grid">' +
              '<div class="traj-places">' +
                '<div class="traj-sub-title">高频出现地点 Top5</div>' +
                TOP_PLACES.map(function(p, i) {
                  return '<div class="traj-place-row">' +
                    '<span class="traj-rank">' + (i+1) + '</span>' +
                    '<span class="traj-place-name">' + p.place + '</span>' +
                    '<span class="traj-place-count">' + p.count + '次</span>' +
                  '</div>';
                }).join('') +
              '</div>' +
              '<div class="traj-hours">' +
                '<div class="traj-sub-title">活动时段分布</div>' +
                '<div id="chart-hours" style="width:100%;height:140px"></div>' +
              '</div>' +
            '</div>' +
            '<div class="traj-latest">' +
              icon('clock',14) + ' 最近出现：2026-05-16 22:30 · 新城区东大街商圈卡口' +
            '</div>' +
          '</div>' +
        '</div>' +

        // 右栏
        '<div class="profile-side">' +
          // 家庭信息
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('users',16) + ' 家庭信息</span></div>' +
            '<div class="info-rows">' +
              '<div class="info-row"><span class="info-label">监护人</span><span>' + FAMILY.guardian + '</span></div>' +
              '<div class="info-row"><span class="info-label">联系电话</span><span>' + icon('phone',13) + ' ' + FAMILY.phone + '</span></div>' +
              '<div class="info-row"><span class="info-label">家庭状况</span><span>' + FAMILY.situation + '</span></div>' +
              '<div class="info-row"><span class="info-label">困难类型</span><span>' + FAMILY.difficulty + '</span></div>' +
              '<div class="info-row"><span class="info-label">儿童类别</span><span>' + FAMILY.childType + '</span></div>' +
            '</div>' +
          '</div>' +

          // 教育状态
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('book',16) + ' 教育状态</span></div>' +
            '<div class="edu-section">' +
              eduTag(EDUCATION.status) +
              '<div class="info-rows" style="margin-top:12px">' +
                '<div class="info-row"><span class="info-label">学校</span><span>' + EDUCATION.school + '</span></div>' +
                '<div class="info-row"><span class="info-label">就学情况</span><span>' + EDUCATION.detail + '</span></div>' +
              '</div>' +
            '</div>' +
          '</div>' +

          // 关系网络
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('link',16) + ' 共犯人员</span></div>' +
            '<div class="assoc-list">' + ASSOCIATES.map(function(a) {
              return '<div class="assoc-item">' +
                '<a href="javascript:void(0)" class="assoc-name" onclick="PageManager.switchTo(\'profile\')">' + a.name + '</a>' +
                '<span class="assoc-times">共犯 ' + a.times + ' 次</span>' +
                riskBadge(a.risk) +
              '</div>';
            }).join('') + '</div>' +
          '</div>' +

          // 旅馆入住
          '<div class="card">' +
            '<div class="card-head"><span class="section-title">' + icon('hotel',16) + ' 旅馆入住</span></div>' +
            '<div class="hotel-list">' + HOTELS.map(function(h) {
              return '<div class="hotel-item">' +
                '<div class="hotel-name">' + h.hotel + '</div>' +
                '<div class="hotel-meta">' + icon('calendar',13) + ' ' + h.time + '</div>' +
                '<div class="hotel-meta">' + icon('user',13) + ' 同住人：' + h.companion + '</div>' +
              '</div>';
            }).join('') + '</div>' +
          '</div>' +

          // 管控建议
          '<div class="card suggestion-card">' +
            '<div class="card-head"><span class="section-title">' + icon('clipboard',16) + ' 管控建议</span></div>' +
            '<ul class="suggestion-list">' + SUGGESTIONS.map(function(s) {
              return '<li class="suggestion-item">' + s + '</li>';
            }).join('') + '</ul>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  // ---- 初始化 ----
  function init() {
    // 风险分进度条动画
    setTimeout(function() {
      document.querySelectorAll('.risk-progress-bar').forEach(function(bar) {
        bar.style.width = bar.dataset.targetWidth;
      });
    }, 100);

    // 活动时段柱状图
    var hoursEl = document.getElementById('chart-hours');
    if (hoursEl) {
      var hoursChart = echarts.init(hoursEl);
      charts.push(hoursChart);
      var hours = [];
      for (var i = 0; i < 24; i++) hours.push(i + ':00');
      hoursChart.setOption(Object.assign({}, echartBaseOption(), {
        grid: { left: 28, right: 4, top: 8, bottom: 20 },
        xAxis: Object.assign({ type: 'category', data: hours }, echartAxisDefaults(), {
          axisLabel: { color: '#5b6b80', fontSize: 9, interval: 5 },
        }),
        yAxis: Object.assign({ type: 'value' }, echartAxisDefaults(), { show: false }),
        series: [{
          type: 'bar', data: HOUR_DATA, barWidth: 8,
          itemStyle: {
            color: function(params) {
              return params.value > 10 ? '#f97316' : params.value > 5 ? '#38bdf8' : '#1e3a5f';
            },
            borderRadius: [2, 2, 0, 0],
          },
          animationDuration: 800,
        }],
      }));
    }

    // 图表 resize
    var resizeHandler = debounce(function() {
      charts.forEach(function(c) { if (!c.isDisposed()) c.resize(); });
    }, 200);
    window.addEventListener('resize', resizeHandler);
  }

  function destroy() {
    charts.forEach(function(c) { if (!c.isDisposed()) c.dispose(); });
    charts = [];
  }

  return { render: render, init: init, destroy: destroy };
})();

PageManager.register('profile', ProfilePage);
