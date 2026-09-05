import { track } from "./analytics.js";

const OFFLINE_PENDING_KEY = "ato-ippai-offline-fallback-pending";
let deferredInstallPrompt = null;
let installButton = null;

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

function ensurePwaStyles() {
  if (document.getElementById("pwaRuntimeStyles")) return;
  const style = document.createElement("style");
  style.id = "pwaRuntimeStyles";
  style.textContent = `
    .pwa-network-notice,
    .pwa-install-panel {
      margin: 0 0 12px;
      padding: 10px 12px;
      border-radius: 12px;
      font-size: 0.88rem;
      line-height: 1.5;
    }
    .pwa-network-notice {
      background: rgba(255, 191, 71, 0.12);
      border: 1px solid rgba(255, 191, 71, 0.32);
    }
    .pwa-install-panel {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .pwa-install-button {
      margin-top: 8px;
      border: 0;
      border-radius: 10px;
      padding: 9px 12px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
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

function ensureInstallPanel() {
  let panel = document.getElementById("pwaInstallPanel");
  if (panel) return panel;
  const shell = getShell();
  if (!shell) return null;

  panel = document.createElement("section");
  panel.id = "pwaInstallPanel";
  panel.className = "pwa-install-panel pwa-hidden";
  panel.setAttribute("aria-label", "ホーム画面への追加");
  shell.appendChild(panel);
  return panel;
}

function showChromiumInstallUi() {
  if (isStandaloneMode()) return;
  const panel = ensureInstallPanel();
  if (!panel) return;

  panel.innerHTML = `
    <strong>ホーム画面から1タップで開けます</strong><br>
    <span>あと一杯ナビをアプリのように追加できます。</span><br>
    <button id="pwaInstallButton" class="pwa-install-button" type="button">ホーム画面に追加</button>
  `;
  panel.classList.remove("pwa-hidden");
  installButton = document.getElementById("pwaInstallButton");

  installButton?.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    track("install_prompt_clicked");
    const prompt = deferredInstallPrompt;
    deferredInstallPrompt = null;
    await prompt.prompt();
    try {
      await prompt.userChoice;
    } catch {
      // Browser controls the final install result.
    }
    panel.classList.add("pwa-hidden");
  });
}

function showIosInstallHint() {
  if (!isIosDevice() || isStandaloneMode()) return;
  const panel = ensureInstallPanel();
  if (!panel) return;

  panel.innerHTML = `
    <strong>ホーム画面に追加できます</strong><br>
    <span>Safariの共有メニューから「ホーム画面に追加」を選んでください。</span>
  `;
  panel.classList.remove("pwa-hidden");
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

  ensurePwaStyles();
  applyNetworkState();
  registerServiceWorker();

  if (isStandaloneMode()) {
    track("standalone_open");
  } else {
    showIosInstallHint();
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    track("install_prompt_shown");
    showChromiumInstallUi();
  });

  window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    document.getElementById("pwaInstallPanel")?.classList.add("pwa-hidden");
    track("app_installed");
  });

  window.addEventListener("offline", applyNetworkState);
  window.addEventListener("online", applyNetworkState);
}
