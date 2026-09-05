const API_ORIGIN = "https://ato-ippai-api-poc.edward-se-pg.workers.dev";

function shouldProxy(pathname) {
  return (
    pathname === "/health" ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/ops/")
  );
}

export async function onRequest(context) {
  const incomingUrl = new URL(context.request.url);

  if (!shouldProxy(incomingUrl.pathname)) {
    return context.next();
  }

  const upstreamUrl = new URL(
    `${incomingUrl.pathname}${incomingUrl.search}`,
    API_ORIGIN
  );

  const upstreamRequest = new Request(upstreamUrl.toString(), context.request);
  const upstreamResponse = await fetch(upstreamRequest);

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: upstreamResponse.headers
  });
}
