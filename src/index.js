import { evaluateSakaeToFujigaoka } from "./decision.js";\n\nconst ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes";

const json = (data, status = 200) =>
  new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type",
      "access-control-allow-methods": "POST,OPTIONS"
    }
  });

function waypoint(value) {
  if (typeof value === "string") return { address: value };

  if (value?.latitude != null && value?.longitude != null) {
    return {
      location: {
        latLng: {
          latitude: Number(value.latitude),
          longitude: Number(value.longitude)
        }
      }
    };
  }

  throw new Error("waypoint must be an address string or {latitude, longitude}");
}

function parseSeconds(duration) {
  if (!duration) return null;
  return Number(String(duration).replace(/s$/, ""));
}

function allSteps(route) {
  return route?.legs?.flatMap((leg) => leg.steps || []) || [];
}

function firstTransitStep(route) {
  return allSteps(route).find(
    (step) =>
      step.travelMode === "TRANSIT" &&
      step.transitDetails?.stopDetails?.departureTime
  );
}

function lastTransitStep(route) {
  return [...allSteps(route)]
    .reverse()
    .find(
      (step) =>
        step.travelMode === "TRANSIT" &&
        step.transitDetails?.stopDetails?.arrivalTime
    );
}

function normalizeTransit(route, requestedDepartureTime, maxWaitMinutes) {
  const first = firstTransitStep(route);
  const last = lastTransitStep(route);

  const firstTransitDeparture =
    first?.transitDetails?.stopDetails?.departureTime ?? null;
  const lastTransitArrival =
    last?.transitDetails?.stopDetails?.arrivalTime ?? null;

  let waitMinutes = null;
  if (firstTransitDeparture) {
    waitMinutes =
      (new Date(firstTransitDeparture).getTime() -
        new Date(requestedDepartureTime).getTime()) /
      60000;
  }

  return {
    requestedDepartureTime,
    distanceMeters: route?.distanceMeters ?? null,
    durationSeconds: parseSeconds(route?.duration),
    firstTransitDeparture,
    lastTransitArrival,
    waitMinutes:
      waitMinutes == null ? null : Math.round(waitMinutes * 10) / 10,
    lateNightReturnPossible:
      waitMinutes != null &&
      waitMinutes >= 0 &&
      waitMinutes <= maxWaitMinutes,
    fare: route?.travelAdvisory?.transitFare ?? null,
    steps: allSteps(route).map((step) => ({
      travelMode: step.travelMode,
      departureStop:
        step.transitDetails?.stopDetails?.departureStop?.name ?? null,
      departureTime:
        step.transitDetails?.stopDetails?.departureTime ?? null,
      arrivalStop:
        step.transitDetails?.stopDetails?.arrivalStop?.name ?? null,
      arrivalTime:
        step.transitDetails?.stopDetails?.arrivalTime ?? null,
      line: step.transitDetails?.transitLine?.name ?? null,
      headsign: step.transitDetails?.headsign ?? null
    }))
  };
}

async function googleRoutes(env, body, fieldMask) {
  const response = await fetch(ROUTES_URL, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "X-Goog-Api-Key": env.GOOGLE_MAPS_API_KEY,
      "X-Goog-FieldMask": fieldMask
    },
    body: JSON.stringify(body)
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(
      `Google Routes API ${response.status}: ${JSON.stringify(payload)}`
    );
  }

  return payload;
}

async function transit(env, input) {
  if (!input.departureTime) throw new Error("departureTime is required");

  const payload = await googleRoutes(
    env,
    {
      origin: waypoint(input.origin),
      destination: waypoint(input.destination),
      travelMode: "TRANSIT",
      departureTime: input.departureTime,
      languageCode: "ja",
      regionCode: "JP",
      units: "METRIC"
    },
    [
      "routes.distanceMeters",
      "routes.duration",
      "routes.travelAdvisory.transitFare",
      "routes.legs.steps.travelMode",
      "routes.legs.steps.transitDetails.stopDetails",
      "routes.legs.steps.transitDetails.transitLine.name",
      "routes.legs.steps.transitDetails.headsign"
    ].join(",")
  );

  const route = payload.routes?.[0];

  if (!route) {
    return {
      requestedDepartureTime: input.departureTime,
      routeFound: false,
      lateNightReturnPossible: false,
      rawRouteCount: payload.routes?.length ?? 0
    };
  }

  return {
    routeFound: true,
    ...normalizeTransit(
      route,
      input.departureTime,
      Number(env.MAX_LATE_TRANSIT_WAIT_MINUTES || "90")
    )
  };
}

async function drive(env, input) {
  const payload = await googleRoutes(
    env,
    {
      origin: waypoint(input.origin),
      destination: waypoint(input.destination),
      travelMode: "DRIVE",
      routingPreference: "TRAFFIC_AWARE",
      departureTime: input.departureTime || new Date().toISOString(),
      languageCode: "ja",
      regionCode: "JP",
      units: "METRIC"
    },
    "routes.distanceMeters,routes.duration"
  );

  const route = payload.routes?.[0];

  return route
    ? {
        routeFound: true,
        distanceMeters: route.distanceMeters ?? null,
        durationSeconds: parseSeconds(route.duration)
      }
    : { routeFound: false };
}

function addMinutes(iso, minutes) {
  return new Date(
    new Date(iso).getTime() + Number(minutes) * 60000
  ).toISOString();
}

async function evaluate(env, input) {
  const base = input.departureTime || new Date().toISOString();
  const offsets = input.offsetMinutes || [0, 15, 30, 60];

  const transitResults = [];

  for (const offset of offsets) {
    const result = await transit(env, {
      origin: input.origin,
      destination: input.transitDestination,
      departureTime: addMinutes(base, offset)
    });

    transitResults.push({
      offsetMinutes: Number(offset),
      ...result
    });
  }

  const driveResult = input.driveDestination
    ? await drive(env, {
        origin: input.origin,
        destination: input.driveDestination,
        departureTime: base
      })
    : null;

  return {
    baseDepartureTime: base,
    transitDestination: input.transitDestination,
    driveDestination: input.driveDestination || null,
    transit: transitResults,
    drive: driveResult
  };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return json({ ok: true });

    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({
        ok: true,
        service: "ato-ippai-api-poc",
        googleApiKeyConfigured: Boolean(env.GOOGLE_MAPS_API_KEY)
      });
    }

    if (request.method !== "POST") {
      return json({ error: "Not found" }, 404);
    }

    try {
      const input = await request.json();

      if (url.pathname === "/api/transit") {
        return json(await transit(env, input));
      }

      if (url.pathname === "/api/drive") {
        return json(await drive(env, input));
      }

      if (url.pathname === "/api/evaluate") {
        return json(await evaluate(env, input));
      }

      if (url.pathname === "/api/decision-poc") {
        return json(evaluateSakaeToFujigaoka(input));
      }

      return json({ error: "Not found" }, 404);
    } catch (error) {
      return json({ error: String(error?.message || error) }, 400);
    }
  }
};
