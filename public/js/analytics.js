const PRODUCTION_HOSTS = new Set(["ato-ippai.pages.dev"]);

const EVENTS = new Set([
  "top_view",
  "last_train_view",
  "last_train_link_click",
  "tonight_decision_check",
  "last_train_check"
]);

function currentDisplayMode() {
  if (typeof window === "undefined") return "browser";
  const standalone =
    window.matchMedia?.("(display-mode: standalone)")?.matches ||
    window.navigator?.standalone === true;
  return standalone ? "standalone" : "browser";
}

function currentNetworkState() {
  if (typeof navigator === "undefined") return "online";
  return navigator.onLine === false ? "offline" : "online";
}

export function shouldSendForHost(hostname) {
  return PRODUCTION_HOSTS.has(String(hostname || "").toLowerCase());
}

export function isInternalTestMode(search) {
  let query = search;
  if (typeof query !== "string") {
    if (typeof location === "undefined") return false;
    query = location.search || "";
  }

  try {
    return new URLSearchParams(query).getAll("internal_test").includes("1");
  } catch {
    return false;
  }
}

export function withInternalTest(pathname, search) {
  if (!isInternalTestMode(search)) return pathname;
  const separator = pathname.includes("?") ? "&" : "?";
  return `${pathname}${separator}internal_test=1`;
}

export function normalizeEvent(eventName) {
  if (!EVENTS.has(eventName)) return null;
  return {
    event: eventName,
    display_mode: currentDisplayMode(),
    network_state: currentNetworkState()
  };
}

function shouldSend() {
  if (typeof location === "undefined") return false;
  return (
    shouldSendForHost(location.hostname) &&
    !isInternalTestMode(location.search)
  );
}

function postEvent(payload) {
  if (!payload || !shouldSend()) return false;
  const body = JSON.stringify(payload);

  try {
    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon("/api/event", blob)) return true;
    }
  } catch {
    // Analytics failure must never affect the app.
  }

  if (typeof fetch === "function") {
    fetch("/api/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
      credentials: "same-origin"
    }).catch(() => {});
    return true;
  }

  return false;
}

export function track(eventName) {
  return postEvent(normalizeEvent(eventName));
}

function preserveInternalTestOnAnchor(anchor) {
  if (!anchor || !isInternalTestMode()) return;

  const rawHref = anchor.getAttribute("href");
  if (!rawHref || !rawHref.startsWith("/")) return;

  try {
    const url = new URL(rawHref, location.origin);
    if (url.origin !== location.origin) return;
    url.searchParams.set("internal_test", "1");
    anchor.setAttribute("href", `${url.pathname}${url.search}${url.hash}`);
  } catch {
    // Navigation should continue unchanged if URL parsing fails.
  }
}

function onDocumentClick(event) {
  const anchor = event.target?.closest?.("a");
  preserveInternalTestOnAnchor(anchor);

  if (event.target?.closest?.("#lastTrainQuickLink")) {
    track("last_train_link_click");
    return;
  }

  if (event.target?.closest?.("#checkButton")) {
    track("tonight_decision_check");
    return;
  }

  if (event.target?.closest?.("#lastTrainCheckButton")) {
    track("last_train_check");
  }
}

export function setupAnalytics() {
  if (typeof document !== "undefined") {
    document.addEventListener("click", onDocumentClick, true);
  }

  if (typeof location === "undefined") return;
  const normalizedPath = location.pathname.replace(/\/+$/, "") || "/";
  track(normalizedPath === "/last-train" ? "last_train_view" : "top_view");
}
