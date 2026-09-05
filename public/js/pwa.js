import { track } from "./analytics.js";

const OFFLINE_PENDING_KEY = "ato-ippai-offline-fallback-pending";
let deferredInstallPrompt = null;

export function isStandaloneMode() {
  if (typeof window === "undefined") return false;
  return Boolean(
    window.matchMedia?.("(display-mode: standalone)")?.matches ||
      window.navigator?.standalone === true
  );
}

export function isIosDevice() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  const classicIos = /iPad|iPhone|iPod/.test(ua);
  const ipadDesktopMode =
    navigator.platform === "MacIntel" && Number(navigator.maxTouchPoints) > 1;
  return classicIos || ipadDesktopMode;
}

function ensureHeadLink(rel, href, attributes = {}) {
  let link = document.head.querySelector(`link[rel="${rel}"][href="${href}"]`);
  if (link) return link;
  link = document.createElement("link");
  link.rel = rel;
  link.href = href;
  for (const [key, value] of Object.entries(attributes)) {
    link.setAttribute(key, value);
  }
  document.head.appendChild(link);
  return link;
}

function ensureHeadMetadata() {
  ensureHeadLink("manifest", "/manifest.webmanifest");
  ensureHeadLink("icon", "/favicon.svg", { type: "image/svg+xml" });
  ensureHeadLink("apple-touch-icon", "/apple-touch-icon.png", {
    sizes: "180x180"
  });

  if (!document.head.querySelector('meta[name="mobile-web-app-capable"]')) {
    const meta = document.createElement("meta");
    meta.name = "mobile-web-app-capable";
    meta.content = "yes";
    document.head.appendChild(meta);
  }
}

function ensurePwaStyles() {
  if (document.getElementById("pwaRuntimeStyles")) return;
  const style = document.createElement("style");
  style.id = "pwaRuntimeStyles";
  style.textContent = `
    .pwa-network-notice {
      margin: 0 0 12px;
      padding: 10px 12px;
      border-radius: 12px;
      font-size: 0.88rem;
      line-height: 1.5;
      background: rgba(255, 191, 71, 0.12);
      border: 1px solid rgba(255, 191, 71, 0.32);
    }
    .pwa-install-panel {
      margin: 12px 0 0;
      font-size: 0.84rem;
      line-height: 1.5;
    }
    .pwa-install-button {
      min-height: 44px;
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 10px;
      padding: 9px 14px;
      background: rgba(255, 255, 255, 0.08);
      color: inherit;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .pwa-install-button:disabled { opacity: 0.55; cursor: default; }
    .pwa-install-help { margin: 0; opacity: 0.82; }
    .pwa-hidden { display: none !important; }
  `;
  document.head.appendChild(style);
}

function getShell() {
  return document.querySelector("main.shell");
}

function ensureNetworkNotice() {
  let notice = document.getElementById("pwaNetworkNotice");
  if (notice) return notice;
  const shell = getShell();
  if (!shell) return null;

  notice = document.createElement("div");
  notice.id = "pwaNetworkNotice";
  notice.className = "pwa-network-notice pwa-hidden";
  notice.setAttribute("role", "status");
  notice.textContent =
    "オフラインです。現在地からの終電判定・タクシー概算には通信が必要です。";
  shell.prepend(notice);
  return notice;
}

function markOfflineFallbackPending() {
  try {
    sessionStorage.setItem(OFFLINE_PENDING_KEY, "1");
  } catch {
    // Storage failure must not affect the app.
  }
}

function flushOfflineFallbackIfNeeded() {
  try {
    if (sessionStorage.getItem(OFFLINE_PENDING_KEY) === "1") {
      sessionStorage.removeItem(OFFLINE_PENDING_KEY);
      track("offline_fallback");
    }
  } catch {
    // Analytics is best effort only.
  }
}

function applyNetworkState() {
  const notice = ensureNetworkNotice();
  if (!notice) return;

  const offline = navigator.onLine === false;
  notice.classList.toggle("pwa-hidden", !offline);
  if (offline) {
    markOfflineFallbackPending();
  } else {
    flushOfflineFallbackIfNeeded();
  }
}

function setOfflineActionMessage(target) {
  const message = "現在地からの判定には通信が必要です";
  if (target?.closest?.("#lastTrainCheckButton")) {
    const status = document.getElementById("lastTrainStatus");
    if (status) status.textContent = message;
    return;
  }
  if (target?.closest?.("#checkButton")) {
    const status = document.getElementById("status");
    if (status) status.textContent = message;
  }
}

function guardOfflineActions(event) {
  if (navigator.onLine !== false) return;
  const blocked =
    event.target?.closest?.("#checkButton") ||
    event.target?.closest?.("#lastTrainCheckButton");
  if (!blocked) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  markOfflineFallbackPending();
  setOfflineActionMessage(event.target);
}

function ensureInstallPanel() {
  let panel = document.getElementById("pwaInstallPanel");
  if (panel) return panel;

  const hero = document.querySelector("header.hero");
  if (!hero) return null;

  panel = document.createElement("div");
  panel.id = "pwaInstallPanel";
  panel.className = "pwa-install-panel pwa-hidden";
  panel.setAttribute("aria-label", "ホーム画面への追加");
  panel.innerHTML = `
    <button id="pwaInstallButton" class="pwa-install-button" type="button" hidden>ホーム画面に追加</button>
    <p id="pwaHelp" class="pwa-install-help" hidden></p>
  `;
  hero.appendChild(panel);
  return panel;
}

function hideInstallUi() {
  const panel = document.getElementById("pwaInstallPanel");
  const button = document.getElementById("pwaInstallButton");
  const help = document.getElementById("pwaHelp");
  if (button) {
    button.hidden = true;
    button.disabled = false;
  }
  if (help) help.hidden = true;
  panel?.classList.add("pwa-hidden");
}

function showIosInstallHint() {
  if (!isIosDevice() || isStandaloneMode()) return;
  const panel = ensureInstallPanel();
  const button = document.getElementById("pwaInstallButton");
  const help = document.getElementById("pwaHelp");
  if (!panel || !help) return;

  if (button) button.hidden = true;
  help.textContent =
    "iPhone / iPadでは、Safariの共有メニューから「ホーム画面に追加」を選べます。";
  help.hidden = false;
  panel.classList.remove("pwa-hidden");
}

function setupInstallUi() {
  const panel = ensureInstallPanel();
  const button = document.getElementById("pwaInstallButton");
  const help = document.getElementById("pwaHelp");
  if (!panel || !button || !help) return;

  if (isStandaloneMode()) {
    hideInstallUi();
    track("standalone_open");
    return;
  }

  showIosInstallHint();

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    button.hidden = false;
    help.hidden = true;
    panel.classList.remove("pwa-hidden");
    track("install_prompt_shown");
  });

  button.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;

    button.disabled = true;
    track("install_prompt_clicked");
    try {
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
    } finally {
      deferredInstallPrompt = null;
      hideInstallUi();
    }
  });

  window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    hideInstallUi();
    track("app_installed");
  });
}

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  try {
    await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
      updateViaCache: "none"
    });
  } catch (error) {
    console.warn("Service Worker registration failed", error);
  }
}

export function setupPwa() {
  if (typeof window === "undefined" || typeof document === "undefined") return;

  ensureHeadMetadata();
  ensurePwaStyles();
  applyNetworkState();
  setupInstallUi();
  registerServiceWorker();
  document.addEventListener("click", guardOfflineActions, true);

  window.addEventListener("offline", applyNetworkState);
  window.addEventListener("online", applyNetworkState);
}
