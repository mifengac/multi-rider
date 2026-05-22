// ============================================================
// ai-analyst.js - AI 研判助手
// ============================================================

var AIAnalystPage = (function() {
  var messages = [];
  var isGenerating = false;
  var knowledgeMode = false;
  var abortFlag = false;

  // ---- 演示对话 ----
  var DEMO_RESPONSES = {
    '盗窃量刑标准': '## 未成年人盗窃量刑标准\n\n根据《刑法》及相关司法解释，未成年人盗窃的量刑需注意以下要点：\n\n**一、数额标准**\n- 盗窃公私财物价值 **1000元至3000元** 以上为"数额较大"\n- **3万元至10万元** 以上为"数额巨大"\n- **30万元至50万元** 以上为"数额特别巨大"\n\n**二、未成年人从宽原则**\n- 已满14周岁不满16周岁：仅对八种严重犯罪负刑事责任，一般盗窃不追究\n- 已满16周岁不满18周岁：应当从轻或减轻处罚\n- 初次犯罪且数额较小：可依法作出不起诉决定\n\n**三、附条件不起诉**\n- 可能判处一年有期徒刑以下刑罚\n- 有悔罪表现\n- 设定6个月至1年考验期',
    '侵财预防措施': '## 未成年人侵财犯罪预防措施\n\n### 一、源头预防\n- 建立 **辍学预警机制**，对辍学、流失学生进行实时监控\n- 强化家庭教育指导，对监护缺失家庭提供帮扶\n- 开展法治进校园活动，提高未成年人法律意识\n\n### 二、重点管控\n- 对已标记的高风险未成年人实施 **分级管控**\n- 建立与社区、学校的联动巡查机制\n- 利用技防手段，对高风险区域加强监控覆盖\n\n### 三、综合治理\n- 联合教育、民政、妇联等部门形成工作合力\n- 建立未成年人犯罪记录封存制度\n- 推动建立专门的未成年人观护帮教基地',
    '附条件不起诉': '## 附条件不起诉制度要点\n\n根据《刑事诉讼法》第二百八十二条：\n\n**适用条件：**\n- 未成年犯罪嫌疑人\n- 涉嫌刑法分则第四、五、六章规定的犯罪（含侵财犯罪）\n- 可能判处 **一年有期徒刑以下刑罚**\n- 有悔罪表现\n\n**考验期：**\n- 六个月以上一年以下\n- 考验期内需遵守相关规定，接受监督\n\n**考验期要求：**\n- 遵守法律法规，服从监督\n- 按规定报告活动情况\n- 离开居住地需批准\n- 按要求接受矫治和教育',
    'default': '根据系统分析，该人员近期行为存在以下风险特征：\n\n**一、轨迹异常**\n- 近7日内多次在商业区深夜出现\n- 活动时段集中在 22:00-02:00，与侵财案件高发时段吻合\n\n**二、社交风险**\n- 与已知高风险人员存在频繁接触\n- 共同出现在案件高发区域3次以上\n\n**三、综合评估**\n- 风险评分较上月上升 **12分**\n- 建议等级调整为"高风险"\n- 需加强日常监控和走访\n\n**建议措施：**\n- 增加对该人员的巡查频次\n- 通知其监护人加强管教\n- 关注与共犯人员的联络动态',
  };

  var SERIAL_RESPONSE = '## 串并案分析结果\n\n通过对近6个月案件数据进行智能分析，发现以下系列案件线索：\n\n### 系列一：新城区夜间盗窃系列案（4起）\n- **共同特征**：作案时间 22:00-02:00，目标为临街商铺\n- **关联嫌疑人**：张某辉、李某阳\n- **作案手法**：撬锁入室，盗窃现金及电子产品\n- **建议**：合并侦查，重点关注两人行动轨迹\n\n### 系列二：校园周边敲诈勒索系列（3起）\n- **共同特征**：作案地点集中在中学周边200米范围内\n- **关联嫌疑人**：赵某杰、陈某龙\n- **受害群体**：12-15岁在校学生\n- **建议**：加强校园周边巡逻，开展专项整治';

  // ---- 渲染 ----
  function render(container) {
    container.innerHTML =
      '<div class="ai-layout">' +
        // 左侧栏
        '<div class="ai-sidebar">' +
          '<div class="ai-sidebar-section">' +
            '<div class="ai-sidebar-label">快捷功能</div>' +
            '<button class="ai-func-btn" id="btn-person-judge">' +
              '<div class="ai-func-icon">' + icon('target', 24) + '</div>' +
              '<div class="ai-func-text"><div class="ai-func-title">人员研判</div><div class="ai-func-desc">输入证件号，AI 分析侵财风险</div></div>' +
            '</button>' +
            '<button class="ai-func-btn" id="btn-serial">' +
              '<div class="ai-func-icon" style="color:#a855f7">' + icon('layers', 24) + '</div>' +
              '<div class="ai-func-text"><div class="ai-func-title">串并案分析</div><div class="ai-func-desc">AI 自动发现侵财系列案线索</div></div>' +
            '</button>' +
            '<button class="ai-func-btn" id="btn-knowledge">' +
              '<div class="ai-func-icon" style="color:#f59e0b">' + icon('book', 24) + '</div>' +
              '<div class="ai-func-text"><div class="ai-func-title">知识问答</div><div class="ai-func-desc">基于侵财法律知识库 RAG</div></div>' +
              '<div class="ai-func-toggle" id="knowledge-toggle"></div>' +
            '</button>' +
          '</div>' +
          '<div class="ai-sidebar-section">' +
            '<div class="ai-sidebar-label">快捷提问</div>' +
            '<button class="ai-quick-btn" data-q="盗窃量刑标准">盗窃量刑标准</button>' +
            '<button class="ai-quick-btn" data-q="侵财预防措施">侵财预防措施</button>' +
            '<button class="ai-quick-btn" data-q="附条件不起诉">附条件不起诉</button>' +
          '</div>' +
          '<div class="ai-sidebar-bottom">' +
            '<button class="ai-clear-btn" id="btn-clear">' + icon('trash', 16) + ' 清空对话</button>' +
          '</div>' +
        '</div>' +

        // 右侧对话区
        '<div class="ai-chat-area">' +
          // 顶部标题
          '<div class="ai-chat-header">' +
            '<span class="ai-chat-title">' + icon('sparkles', 18) + ' AI 研判助手</span>' +
            '<span class="ai-mode-tag" id="ai-mode-tag">通用模式</span>' +
          '</div>' +
          // 消息区
          '<div class="ai-messages" id="ai-messages">' +
            '<div class="ai-empty-state" id="ai-empty">' +
              '<div class="ai-empty-icon">' + icon('sparkles', 56) + '</div>' +
              '<div class="ai-empty-title">未成年人侵财犯罪 AI 研判助手</div>' +
              '<div class="ai-empty-sub">请选择左侧功能或直接输入问题开始对话</div>' +
            '</div>' +
          '</div>' +
          // 输入区
          '<div class="ai-input-area">' +
            '<div class="ai-input-wrap">' +
              '<textarea class="ai-input" id="ai-input" rows="1" placeholder="输入您的问题…（Enter 发送，Shift+Enter 换行）"></textarea>' +
              '<button class="ai-send-btn" id="ai-send-btn">' + icon('send', 18) + '</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +

      // 人员研判弹窗
      '<div class="modal-overlay" id="modal-person" style="display:none">' +
        '<div class="modal-card">' +
          '<div class="modal-header">' +
            '<span>' + icon('target', 18) + ' 人员研判</span>' +
            '<button class="modal-close" id="modal-person-close">' + icon('x', 18) + '</button>' +
          '</div>' +
          '<div class="modal-body">' +
            '<label class="modal-label">请输入证件号码</label>' +
            '<input class="modal-input" id="modal-person-input" placeholder="请输入身份证号码…" />' +
          '</div>' +
          '<div class="modal-footer">' +
            '<button class="btn-outline" id="modal-person-cancel">取消</button>' +
            '<button class="btn-primary" id="modal-person-submit">' + icon('zap', 14) + ' 开始研判</button>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  // ---- 消息管理 ----
  function addMessage(role, content, meta) {
    messages.push({ role: role, content: content, meta: meta || null });
    renderMessages();
  }

  function renderMessages() {
    var container = document.getElementById('ai-messages');
    var empty = document.getElementById('ai-empty');
    if (messages.length === 0) {
      if (empty) empty.style.display = 'flex';
      return;
    }
    if (empty) empty.style.display = 'none';

    var html = '';
    messages.forEach(function(m) {
      if (m.role === 'user') {
        html += '<div class="ai-msg ai-msg-user"><div class="ai-bubble ai-bubble-user">' + escapeHtml(m.content) + '</div></div>';
      } else if (m.role === 'meta') {
        html += '<div class="ai-msg ai-msg-meta"><div class="ai-meta-bar">' + icon('info', 14) + ' ' + m.content + '</div></div>';
      } else {
        html += '<div class="ai-msg ai-msg-ai"><div class="ai-avatar">' + icon('sparkles', 18) + '</div><div class="ai-bubble ai-bubble-ai">' + renderMarkdown(m.content) + '</div></div>';
      }
    });
    // Remove empty state, set messages
    container.innerHTML = html;
    container.scrollTop = container.scrollHeight;
  }

  function escapeHtml(text) {
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ---- 流式输出模拟 ----
  function streamResponse(text, meta) {
    isGenerating = true;
    updateSendBtn();

    if (meta) addMessage('meta', meta);

    // 添加占位 AI 消息
    messages.push({ role: 'ai', content: '' });
    var idx = messages.length - 1;

    // 显示思考动画
    var container = document.getElementById('ai-messages');
    var thinkHtml = '<div class="ai-msg ai-msg-ai" id="ai-thinking"><div class="ai-avatar">' + icon('sparkles', 18) + '</div><div class="ai-bubble ai-bubble-ai"><span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span> 思考中</div></div>';
    container.innerHTML += thinkHtml;
    container.scrollTop = container.scrollHeight;

    var charIdx = 0;
    var speed = 15;
    abortFlag = false;

    setTimeout(function() {
      // 移除思考动画
      var thinking = document.getElementById('ai-thinking');
      if (thinking) thinking.remove();

      function typeNext() {
        if (abortFlag || charIdx >= text.length) {
          messages[idx].content = text;
          renderMessages();
          isGenerating = false;
          updateSendBtn();
          return;
        }
        charIdx += 1 + Math.floor(Math.random() * 2);
        if (charIdx > text.length) charIdx = text.length;
        messages[idx].content = text.substring(0, charIdx);
        renderMessages();
        setTimeout(typeNext, speed + Math.random() * 20);
      }
      typeNext();
    }, 1200);
  }

  function updateSendBtn() {
    var btn = document.getElementById('ai-send-btn');
    if (!btn) return;
    if (isGenerating) {
      btn.disabled = true;
      btn.innerHTML = '<span class="generating-text">生成中…</span>';
    } else {
      btn.disabled = false;
      btn.innerHTML = icon('send', 18);
    }
  }

  // ---- 发送消息 ----
  function sendMessage(text) {
    if (!text || isGenerating) return;
    addMessage('user', text);
    var resp = DEMO_RESPONSES[text] || DEMO_RESPONSES['default'];
    streamResponse(resp);
  }

  // ---- 初始化 ----
  function init() {
    messages = [];
    isGenerating = false;
    renderMessages();

    // 输入区自动增高
    var input = document.getElementById('ai-input');
    input.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Enter 发送
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        var text = this.value.trim();
        if (text) { sendMessage(text); this.value = ''; this.style.height = 'auto'; }
      }
    });

    // 发送按钮
    document.getElementById('ai-send-btn').addEventListener('click', function() {
      var text = input.value.trim();
      if (text) { sendMessage(text); input.value = ''; input.style.height = 'auto'; }
    });

    // 快捷提问
    document.querySelectorAll('.ai-quick-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { sendMessage(this.dataset.q); });
    });

    // 人员研判弹窗
    document.getElementById('btn-person-judge').addEventListener('click', function() {
      document.getElementById('modal-person').style.display = 'flex';
      document.getElementById('modal-person-input').value = '';
      document.getElementById('modal-person-input').focus();
    });
    document.getElementById('modal-person-close').addEventListener('click', function() {
      document.getElementById('modal-person').style.display = 'none';
    });
    document.getElementById('modal-person-cancel').addEventListener('click', function() {
      document.getElementById('modal-person').style.display = 'none';
    });
    document.getElementById('modal-person-submit').addEventListener('click', function() {
      var val = document.getElementById('modal-person-input').value.trim();
      document.getElementById('modal-person').style.display = 'none';
      if (val) {
        addMessage('user', '请对证件号 ' + val + ' 进行人员研判分析');
        streamResponse(DEMO_RESPONSES['default']);
      }
    });

    // 串并案
    document.getElementById('btn-serial').addEventListener('click', function() {
      addMessage('user', '请进行串并案分析，发现近期侵财系列案线索');
      streamResponse(SERIAL_RESPONSE, '已检索 287 起案件，发现 2 组相似对');
    });

    // 知识模式切换
    document.getElementById('btn-knowledge').addEventListener('click', function() {
      knowledgeMode = !knowledgeMode;
      var tag = document.getElementById('ai-mode-tag');
      var toggle = document.getElementById('knowledge-toggle');
      if (knowledgeMode) {
        tag.textContent = '知识库模式';
        tag.className = 'ai-mode-tag mode-knowledge';
        toggle.classList.add('active');
      } else {
        tag.textContent = '通用模式';
        tag.className = 'ai-mode-tag';
        toggle.classList.remove('active');
      }
    });

    // 清空对话
    document.getElementById('btn-clear').addEventListener('click', function() {
      messages = [];
      abortFlag = true;
      isGenerating = false;
      updateSendBtn();
      renderMessages();
    });
  }

  function destroy() {
    abortFlag = true;
    isGenerating = false;
  }

  return { render: render, init: init, destroy: destroy };
})();

PageManager.register('analyst', AIAnalystPage);
