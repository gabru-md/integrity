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

async function renderPopup() {
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

  chrome.storage.local.get(["baseUrl", "apiKey"], (items) => {
    if (items.baseUrl && items.apiKey) {
      setText("connection-state", `Configured for ${items.baseUrl}`);
    } else if (items.baseUrl) {
      setText("connection-state", `Base URL saved: ${items.baseUrl}`);
    } else {
      setText("connection-state", "Not configured yet");
    }
  });
}

renderPopup();
