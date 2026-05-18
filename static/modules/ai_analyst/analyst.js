(function () {
  let chatHistory = [];
  let ragMode = false;
  let streaming = false;

  const chatArea = document.getElementById('chatArea');
  const inputBox = document.getElementById('inputBox');
  const sendBtn = document.getElementById('sendBtn');
  const modeLabel = document.getElementById('modeLabel');

  function addMessage(role, content, extra) {
    const isFirst = chatArea.querySelector('.text-center.py-20');
    if (isFirst) chatArea.innerHTML = '';

    const div = document.createElement('div');
    div.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-ai');

    if (role === 'ai') {
      div.innerHTML = renderMarkdown(content);
    } else {
      div.textContent = content;
    }

    if (extra) {
      const meta = document.createElement('div');
      meta.className = 'msg-meta';
      meta.textContent = extra;
      div.appendChild(meta);
    }

    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
    return div;
  }

  function addTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'msg msg-ai';
    div.id = 'typingMsg';
    div.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
    return div;
  }

  function removeTypingIndicator() {
    const el = document.getElementById('typingMsg');
    if (el) el.remove();
  }

  function renderMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^\* (.+)$/gm, '<li>$1</li>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
      .replace(/\n/g, '<br>');
    html = html.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    html = html.replace(/<\/ul><br><ul>/g, '');
    return html;
  }

  function setStreaming(val) {
    streaming = val;
    sendBtn.disabled = val;
    sendBtn.textContent = val ? '生成中...' : '发送';
    inputBox.disabled = val;
  }

  async function streamSSE(url, body, onChunk, onMeta) {
    setStreaming(true);
    addTypingIndicator();

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      removeTypingIndicator();
      const msgDiv = addMessage('ai', '');
      let fullText = '';

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;
          const payload = trimmed.slice(5).trim();
          if (payload === '[DONE]') continue;

          try {
            const data = JSON.parse(payload);
            if (data.meta && onMeta) {
              onMeta(data.meta);
              continue;
            }
            if (data.content) {
              fullText += data.content;
              msgDiv.innerHTML = renderMarkdown(fullText);
              chatArea.scrollTop = chatArea.scrollHeight;
            }
            if (data.error) {
              fullText += '\n\n[错误] ' + data.error;
              msgDiv.innerHTML = renderMarkdown(fullText);
            }
          } catch (e) { /* skip parse errors */ }
        }
      }

      if (onChunk) onChunk(fullText);
      chatHistory.push({ role: 'assistant', content: fullText });
    } catch (e) {
      removeTypingIndicator();
      addMessage('ai', '连接失败: ' + e.message);
    }

    setStreaming(false);
  }

  window.sendMessage = function () {
    const text = inputBox.value.trim();
    if (!text || streaming) return;

    addMessage('user', text);
    chatHistory.push({ role: 'user', content: text });
    inputBox.value = '';
    inputBox.style.height = 'auto';

    streamSSE('/api/ai/chat', {
      message: text,
      history: chatHistory.slice(-20),
      mode: ragMode ? 'rag' : 'general',
    });
  };

  window.handleKey = function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  inputBox.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });

  window.startPersonAnalysis = function () {
    const zjhm = prompt('请输入要分析的人员证件号码:');
    if (!zjhm || !zjhm.trim()) return;

    addMessage('user', '请对人员 ' + zjhm.trim() + ' 进行侵财犯罪风险研判分析');
    chatHistory.push({ role: 'user', content: '分析人员: ' + zjhm.trim() });

    streamSSE('/api/ai/analyze/person', { zjhm: zjhm.trim() });
  };

  window.startSerialAnalysis = function () {
    addMessage('user', '请自动分析近期侵财案件，发现串并案线索');
    chatHistory.push({ role: 'user', content: '串并案分析' });

    streamSSE('/api/ai/analyze/serial', { auto: true, months: 6 }, null, function (meta) {
      addMessage('ai', '已检索到 ' + meta.case_count + ' 起侵财案件，发现 ' + meta.pair_count + ' 组相似案件对，正在深度分析...',
        '向量检索 + Rerank');
    });
  };

  window.toggleRagMode = function () {
    ragMode = !ragMode;
    const btn = document.getElementById('btnRag');
    btn.classList.toggle('active', ragMode);
    modeLabel.textContent = ragMode ? '知识库模式' : '通用模式';
    modeLabel.className = 'mode-tag ' + (ragMode ? 'mode-rag' : 'mode-general');

    if (ragMode) {
      addMessage('ai', '已切换到 **知识库模式**。我将基于侵财犯罪法律知识库回答您的问题，回答会包含法律依据引用。');
    } else {
      addMessage('ai', '已切换到 **通用模式**。');
    }
  };

  window.quickAsk = function (question) {
    if (streaming) return;
    if (!ragMode) {
      ragMode = true;
      document.getElementById('btnRag').classList.add('active');
      modeLabel.textContent = '知识库模式';
      modeLabel.className = 'mode-tag mode-rag';
    }
    inputBox.value = question;
    sendMessage();
  };

  window.clearChat = function () {
    chatHistory = [];
    chatArea.innerHTML = `
      <div class="text-center text-slate-500 py-20">
        <div class="text-3xl mb-4">&#129302;</div>
        <div class="text-lg mb-2">未成年人侵财犯罪AI研判助手</div>
        <div class="text-sm">选择左侧功能或直接输入问题开始对话</div>
      </div>`;
  };
})();
