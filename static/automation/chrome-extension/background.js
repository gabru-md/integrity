chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "rasbhari-capture-selection",
    title: "Capture selection in Rasbhari",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== "rasbhari-capture-selection") return;
  chrome.storage.local.get(["baseUrl", "apiKey"], (items) => {
    const summary = {
      selectedText: info.selectionText || "",
      baseUrlConfigured: Boolean(items.baseUrl),
      apiKeyConfigured: Boolean(items.apiKey)
    };
    chrome.storage.local.set({ lastContextMenuCapture: summary });
  });
});
