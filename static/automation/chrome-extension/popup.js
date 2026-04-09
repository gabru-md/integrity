const ACTION_HISTORY_KEY = "rasbhariActionHistory";
const HISTORY_LIMIT = 12;

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0] || null;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function getStoredConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["baseUrl", "apiKey"], (items) => resolve(items));
  });
}

function updateConnectionState(baseUrl, state, tone = "muted") {
  const stateEl = document.getElementById("connection-state");
  if (!stateEl) return;
  stateEl.textContent = state;
  stateEl.className = `line ${tone}`;
  if (baseUrl) {
    stateEl.textContent += ` · ${baseUrl}`;
  }
}

async function fetchJsonWithAuth(baseUrl, apiKey, suffix) {
  const url = `${baseUrl.replace(/\/$/, "")}${suffix}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      "Authorization": `ApiKey ${apiKey}`,
    },
  });
  if (!response.ok) {
    throw new Error((await response.json().catch(() => ({}))).error || `Status ${response.status}`);
  }
  return response.json();
}

async function loadSyncData(baseUrl, apiKey) {
  return fetchJsonWithAuth(baseUrl, apiKey, "/automation/api/extension/sync");
}

function mapActionById(actions) {
  const lookup = {};
  (actions || []).forEach((item) => {
    lookup[item.id] = item;
  });
  return lookup;
}

function renderRules(rules, actionsLookup) {
  const container = document.getElementById("rules-container");
  const placeholder = document.getElementById("rules-empty");
  if (!container || !placeholder) return;
  container.innerHTML = "";
  if (!rules.length) {
    placeholder.textContent = "No enabled rules yet.";
    placeholder.style.display = "block";
    return;
  }
  placeholder.style.display = "none";

  rules.forEach((rule) => {
    const action = actionsLookup[rule.browser_action_id];
    const card = document.createElement("div");
    card.className = "rule-card";
    card.innerHTML = `
      <div class="rule-title">${rule.name || (action && action.name) || "Unnamed rule"}</div>
      <div class="rule-meta">${rule.trigger_mode.toUpperCase()} · ${rule.condition_type} · priority ${rule.priority}</div>
      <div class="rule-meta">Action: ${action ? action.name : "Missing action"}</div>
      <div class="rule-actions"></div>
    `;
    const actionsEl = card.querySelector(".rule-actions");
    if (actionsEl) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "button primary";
      btn.textContent = rule.trigger_mode === "confirm" ? "Confirm trigger" : "Trigger now";
      btn.addEventListener("click", async () => {
        if (rule.trigger_mode === "confirm") {
          const ok = confirm(`Trigger ${action ? action.name : "a browser action"} now?`);
          if (!ok) return;
        }
        await executeRule(rule);
      });
      actionsEl.appendChild(btn);
    }
    container.appendChild(card);
  });
}

async function getHistory() {
  return new Promise((resolve) => {
    chrome.storage.local.get([ACTION_HISTORY_KEY], (items) => {
      resolve(items[ACTION_HISTORY_KEY] || []);
    });
  });
}

async function saveHistory(history) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ [ACTION_HISTORY_KEY]: history }, () => resolve());
  });
}

async function addHistoryEntry(entry) {
  const history = await getHistory();
  history.unshift(entry);
  if (history.length > HISTORY_LIMIT) {
    history.splice(HISTORY_LIMIT);
  }
  await saveHistory(history);
  renderHistory(history);
}

function renderHistory(history) {
  const list = document.getElementById("history-list");
  if (!list) return;
  list.innerHTML = "";
  if (!history.length) {
    const empty = document.createElement("div");
    empty.className = "line muted";
    empty.textContent = "No history yet.";
    list.appendChild(empty);
    return;
  }
  history.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "history-entry";
    row.innerHTML = `
      <div class="entry-title">${entry.label}</div>
      <div class="entry-detail">${entry.detail}</div>
    `;
    list.appendChild(row);
  });
}

async function executeRule(rule) {
  const tab = await getActiveTab();
  const context = {
    url: tab?.url || "",
    title: tab?.title || "",
    domain: tab?.url ? new URL(tab.url).hostname.replace(/^www\\./, "") : "",
  };
  const { baseUrl, apiKey } = await getStoredConfig();
  if (!baseUrl || !apiKey) {
    updateConnectionState("", "Save base URL and API key first.", "muted");
    return;
  }
  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/automation/api/extension/execute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `ApiKey ${apiKey}`,
      },
      body: JSON.stringify({
        browser_action_id: rule.browser_action_id,
        browser_context: context,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Execution failed");
    }
    addHistoryEntry({
      label: rule.name || `Action ${rule.browser_action_id}`,
      detail: `${rule.trigger_mode} · ${payload.result.execution_type} · ${new Date().toLocaleTimeString()}`,
    });
  } catch (err) {
    addHistoryEntry({
      label: rule.name || `Action ${rule.browser_action_id}`,
      detail: `Failed: ${err.message}`,
    });
  }
}

async function initPopup() {
  const tab = await getActiveTab();
  if (tab) {
    setText("page-title", tab.title || "Untitled page");
    try {
      const url = new URL(tab.url);
      setText("page-domain", `${url.hostname}${url.pathname}`);
    } catch (_) {
      setText("page-domain", tab.url || "Unknown page");
    }
  } else {
    setText("page-title", "No active tab");
    setText("page-domain", "Open a page first");
  }

  const config = await getStoredConfig();
  if (!config.baseUrl || !config.apiKey) {
    updateConnectionState("", "Not configured yet", "muted");
    renderRules([], {});
    renderHistory(await getHistory());
    return;
  }

  try {
    updateConnectionState(config.baseUrl, "Checking connection…", "muted");
    await fetchJsonWithAuth(config.baseUrl, config.apiKey, "/automation/api/extension/status");
    updateConnectionState(config.baseUrl, "Connection successful", "success");
    const syncPackage = await loadSyncData(config.baseUrl, config.apiKey);
    const actionsLookup = mapActionById(syncPackage.actions || []);
    renderRules(syncPackage.rules || [], actionsLookup);
  } catch (error) {
    updateConnectionState(config.baseUrl, `Sync error: ${error.message}`, "muted");
    renderRules([], {});
  }

  renderHistory(await getHistory());
}

initPopup();
