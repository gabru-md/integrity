const form = document.getElementById("settings-form");
const baseUrlInput = document.getElementById("base-url");
const apiKeyInput = document.getElementById("api-key");
const statusElement = document.getElementById("status");
const clearButton = document.getElementById("clear-settings");

function setStatus(message, tone = "muted") {
  statusElement.textContent = message;
  statusElement.className = `status ${tone}`;
}

chrome.storage.local.get(["baseUrl", "apiKey"], (items) => {
  baseUrlInput.value = items.baseUrl || "";
  apiKeyInput.value = items.apiKey || "";
  if (items.baseUrl || items.apiKey) {
    setStatus("Saved settings loaded from local extension storage.", "success");
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const payload = {
    baseUrl: baseUrlInput.value.trim(),
    apiKey: apiKeyInput.value.trim()
  };
  chrome.storage.local.set(payload, () => {
    setStatus("Settings saved locally. Sync APIs will use these values when they land.", "success");
  });
});

clearButton.addEventListener("click", () => {
  chrome.storage.local.remove(["baseUrl", "apiKey"], () => {
    baseUrlInput.value = "";
    apiKeyInput.value = "";
    setStatus("Settings cleared.", "muted");
  });
});
