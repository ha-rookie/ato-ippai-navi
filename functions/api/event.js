const PRODUCTION_HOSTS = new Set(["ato-ippai.pages.dev"]);

const EVENTS = new Set([
  "top_view",
  "last_train_view",
  "last_train_link_click",
  "tonight_decision_check",
  "last_train_check",
  "install_prompt_shown",
  "install_prompt_clicked",
  "app_installed",
  "standalone_open",
  "offline_fallback",
  "deployment_smoke_test"
]);

const DISPLAY_MODES = new Set(["browser", "standalone"]);
const NETWORK_STATES = new Set(["online", "offline"]);

export function normalizePayload(input) {
  if (!input || typeof input !== "object" || !EVENTS.has(input.event)) {
    return null;
  }

  return {
    event: input.event,
    displayMode: DISPLAY_MODES.has(input.display_mode)
      ? input.display_mode
      : "browser",
    networkState: NETWORK_STATES.has(input.network_state)
      ? input.network_state
      : "online"
  };
}

export function sameOrigin(request) {
  const requestUrl = new URL(request.url);
  if (!PRODUCTION_HOSTS.has(requestUrl.hostname.toLowerCase())) return false;

  const origin = request.headers.get("Origin");
  if (!origin) return false;

  try {
    return new URL(origin).origin === requestUrl.origin;
  } catch {
    return false;
  }
}

export async function onRequestPost(context) {
  const { request, env } = context;

  if (!sameOrigin(request)) {
    return new Response("Not allowed", { status: 403 });
  }

  const contentType = request.headers.get("Content-Type") || "";
  if (!contentType.toLowerCase().startsWith("application/json")) {
    return new Response("Unsupported content type", { status: 415 });
  }

  const declaredLength = Number(request.headers.get("Content-Length") || 0);
  if (declaredLength > 2048) {
    return new Response("Payload too large", { status: 413 });
  }

  let raw;
  try {
    raw = await request.text();
  } catch {
    return new Response("Invalid body", { status: 400 });
  }

  if (raw.length > 2048) {
    return new Response("Payload too large", { status: 413 });
  }

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  const payload = normalizePayload(input);
  if (!payload) {
    return new Response("Invalid event", { status: 400 });
  }

  if (!env.ANALYTICS || typeof env.ANALYTICS.writeDataPoint !== "function") {
    console.error("Analytics Engine binding ANALYTICS is unavailable");
    return new Response("Analytics unavailable", { status: 503 });
  }

  const hostname = new URL(request.url).hostname;
  env.ANALYTICS.writeDataPoint({
    indexes: [payload.event],
    blobs: [
      payload.event,
      payload.displayMode,
      payload.networkState,
      hostname
    ],
    doubles: [1]
  });

  return new Response(null, {
    status: 204,
    headers: { "Cache-Control": "no-store" }
  });
}

export function onRequest(context) {
  if (context.request.method !== "POST") {
    return new Response("Method not allowed", {
      status: 405,
      headers: { Allow: "POST" }
    });
  }
  return onRequestPost(context);
}
