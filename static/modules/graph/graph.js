const GRAPH_BOOTSTRAP = window.GRAPH_PAGE_BOOTSTRAP || { urls: {} };

const graphState = {
  cy: null,
  lastTaskId: "",
  lastRunId: "",
};

function graphUrl(template, value) {
  return String(template || "").replace("__P__", encodeURIComponent(value)).replace("__G__", encodeURIComponent(value));
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function setStatusCard(prefix, ok, text) {
  const title = document.getElementById(`${prefix}Status`);
  const body = document.getElementById(`${prefix}StatusText`);
  if (!title || !body) {
    return;
  }
  title.textContent = ok ? "已连接" : "异常";
  title.className = `mt-3 text-2xl font-bold ${ok ? "text-emerald-300" : "text-rose-300"}`;
  body.textContent = text || "";
}

function renderTaskText(value) {
  const panel = document.getElementById("taskStatusPanel");
  if (panel) {
    panel.textContent = value;
  }
}

function renderPersonDetail(payload) {
  const panel = document.getElementById("personDetailPanel");
  if (panel) {
    panel.textContent = JSON.stringify(payload, null, 2);
  }
}

function renderTrajectory(items) {
  const panel = document.getElementById("trajectoryPanel");
  if (!panel) {
    return;
  }
  if (!items.length) {
    panel.innerHTML = "暂无轨迹数据";
    return;
  }
  panel.innerHTML = items.slice(0, 20).map((item) => `
    <div class="rounded-2xl border border-white/10 bg-stone-950/70 p-3">
      <div class="text-cyan-300">${item.shot_time || "未知时间"}</div>
      <div class="mt-1 text-stone-200">设备: ${item.device_id || "--"}</div>
      <div class="mt-1 text-stone-400">库名: ${item.libname || "--"}</div>
    </div>
  `).join("");
}

function ensureCytoscape() {
  if (graphState.cy || !window.cytoscape) {
    return;
  }
  graphState.cy = window.cytoscape({
    container: document.getElementById("graphCanvas"),
    style: [
      {
        selector: "node",
        style: {
          label: "data(name)",
          "background-color": "#22d3ee",
          color: "#f5f5f4",
          "font-size": 12,
          "text-wrap": "wrap",
          "text-max-width": 100,
          width: 42,
          height: 42,
        },
      },
      {
        selector: 'node[label="Case"]',
        style: {
          label: "data(aymc)",
          shape: "round-rectangle",
          width: 64,
          height: 36,
          "background-color": "#f97316",
        },
      },
      {
        selector: 'node[is_wcnr = true]',
        style: {
          "border-width": 3,
          "border-color": "#f472b6",
        },
      },
      {
        selector: "edge",
        style: {
          width: 2,
          "line-color": "#52525b",
          "target-arrow-color": "#52525b",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(type)",
          color: "#a8a29e",
          "font-size": 10,
        },
      },
      {
        selector: 'edge[type="CO_SUSPECT"]',
        style: {
          width: "mapData(weight, 1, 10, 2, 8)",
          "line-color": "#a855f7",
          "target-arrow-shape": "none",
        },
      },
      {
        selector: 'edge[type="SAME_CASE"]',
        style: {
          "line-color": "#14b8a6",
          "target-arrow-shape": "triangle",
        },
      },
    ],
    layout: { name: "cose", animate: false, padding: 30 },
  });
  graphState.cy.on("tap", "node[label = 'Person']", async (event) => {
    const node = event.target.data();
    renderPersonDetail(node);
    if (node.sfzh) {
      await loadTrajectory(node.sfzh);
    }
  });
}

function renderGraph(payload) {
  ensureCytoscape();
  if (!graphState.cy) {
    return;
  }
  const elements = [];
  (payload.nodes || []).forEach((node) => {
    elements.push({ data: { ...node, name: node.name || node.sfzh || node.ajbh || node.id } });
  });
  (payload.edges || []).forEach((edge, index) => {
    elements.push({ data: { id: `${edge.type || "edge"}-${index}`, ...edge } });
  });
  graphState.cy.elements().remove();
  graphState.cy.add(elements);
  graphState.cy.layout({ name: "cose", animate: false, padding: 40 }).run();
}

async function refreshStatus() {
  const payload = await fetchJson(GRAPH_BOOTSTRAP.urls.status);
  setStatusCard("neo4j", Boolean(payload.neo4j && payload.neo4j.ok), payload.neo4j && (payload.neo4j.error || payload.neo4j.uri || ""));
  setStatusCard("kingbase", Boolean(payload.kingbase && payload.kingbase.ok), payload.kingbase && (payload.kingbase.error || payload.kingbase.dbname || ""));
  const syncSummary = document.getElementById("syncSummary");
  const syncSummaryText = document.getElementById("syncSummaryText");
  if (syncSummary && syncSummaryText) {
    const latest = payload.latest_sync || {};
    syncSummary.textContent = latest.status || (latest.table_ready ? "未运行" : "表未就绪");
    syncSummaryText.textContent = latest.sync_start_time || latest.error_msg || "等待首次同步";
  }
}

async function loadGangs() {
  const payload = await fetchJson(GRAPH_BOOTSTRAP.urls.gangs);
  graphState.lastRunId = payload.run_id || "";
  const host = document.getElementById("gangList");
  if (!host) {
    return;
  }
  if (!payload.items || !payload.items.length) {
    host.innerHTML = '<div class="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-stone-400">暂无团伙结果，先执行同步和团伙识别。</div>';
    return;
  }
  host.innerHTML = payload.items.map((item) => `
    <button type="button" data-gang-id="${item.gang_id}" class="graph-gang-item w-full rounded-[22px] border border-white/10 bg-stone-950/70 p-4 text-left transition hover:border-cyan-300/50 hover:bg-stone-900">
      <div class="flex items-center justify-between gap-3">
        <div>
          <div class="text-sm font-semibold text-stone-100">${item.gang_id}</div>
          <div class="mt-1 text-xs text-stone-400">成员 ${item.member_count} 人 / 未成年人 ${item.wcnr_count || 0} 人</div>
        </div>
        <div class="rounded-full bg-cyan-400/15 px-3 py-1 text-xs text-cyan-300">区域 ${item.area_code || "--"}</div>
      </div>
    </button>
  `).join("");

  host.querySelectorAll(".graph-gang-item").forEach((button) => {
    button.addEventListener("click", async () => {
      const gangId = button.getAttribute("data-gang-id");
      const detail = await fetchJson(`${graphUrl(GRAPH_BOOTSTRAP.urls.gangDetail, gangId)}?run_id=${encodeURIComponent(graphState.lastRunId)}`);
      renderPersonDetail(detail);
    });
  });
}

async function loadTaskStatus() {
  if (!graphState.lastTaskId) {
    return;
  }
  const payload = await fetchJson(`${GRAPH_BOOTSTRAP.urls.syncStatus}?task_id=${encodeURIComponent(graphState.lastTaskId)}`);
  renderTaskText(JSON.stringify(payload, null, 2));
}

async function submitSyncTask() {
  const limit = document.getElementById("syncLimitInput")?.value || "";
  const theftOnly = Boolean(document.getElementById("theftOnlyInput")?.checked);
  const payload = await fetchJson(GRAPH_BOOTSTRAP.urls.sync, {
    method: "POST",
    body: JSON.stringify({ limit: limit ? Number(limit) : null, theft_only: theftOnly }),
  });
  graphState.lastTaskId = payload.task_id;
  document.getElementById("taskFeedback").textContent = `已提交同步任务 ${payload.task_id}`;
  await loadTaskStatus();
}

async function submitDetectTask() {
  const payload = await fetchJson(GRAPH_BOOTSTRAP.urls.detect, {
    method: "POST",
    body: JSON.stringify({ min_size: 2 }),
  });
  graphState.lastTaskId = payload.task_id;
  document.getElementById("taskFeedback").textContent = `已提交识别任务 ${payload.task_id}`;
  await loadTaskStatus();
}

async function loadPersonGraph(sfzh) {
  const payload = await fetchJson(graphUrl(GRAPH_BOOTSTRAP.urls.person, sfzh));
  renderGraph(payload);
  renderPersonDetail(payload.center || payload);
  await loadTrajectory(sfzh);
}

async function loadTrajectory(sfzh) {
  const payload = await fetchJson(graphUrl(GRAPH_BOOTSTRAP.urls.trajectory, sfzh));
  renderTrajectory(payload.items || []);
}

function bindEvents() {
  document.getElementById("refreshStatusBtn")?.addEventListener("click", async () => {
    await refreshStatus();
    await loadGangs();
    await loadTaskStatus();
  });
  document.getElementById("reloadGangBtn")?.addEventListener("click", loadGangs);
  document.getElementById("syncBtn")?.addEventListener("click", submitSyncTask);
  document.getElementById("detectBtn")?.addEventListener("click", submitDetectTask);
  document.getElementById("personSearchForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const sfzh = document.getElementById("personSfzhInput")?.value?.trim();
    if (!sfzh) {
      return;
    }
    await loadPersonGraph(sfzh);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  ensureCytoscape();
  bindEvents();
  try {
    await refreshStatus();
    await loadGangs();
  } catch (error) {
    renderTaskText(String(error.message || error));
  }
});