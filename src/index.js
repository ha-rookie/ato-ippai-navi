import { estimateNagoyaTaxiFare } from "./taxi.js";
import { composeTonightDecision } from "./tonight.js";
import { composeWalkHomeDecision } from "./walk-home.js";
import { eligibleOriginIds, evaluateLastTrainBoundary } from "./last-train.js";
import LAST_TRAINS_NAGOYA from "./data/last-trains-nagoya.json" with { type: "json" };

const ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes";

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

async function walk(env, input) {
  const payload = await googleRoutes(
    env,
    {
      origin: waypoint(input.origin),
      destination: waypoint(input.destination),
      travelMode: "WALK",
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

async function lastTrainBoundaryFromCurrentLocation(env, input) {
  if (!input.origin) throw new Error("origin is required");
  if (!input.departureTime) throw new Error("departureTime is required");

  const destinationCode = input.destinationCode || "H22";
  const stationBufferMinutes = Number(input.stationBufferMinutes ?? 3);
  const minimumBoardingLeadMinutes = Number(
    input.minimumBoardingLeadMinutes ?? 1
  );

  const eligibleIds = new Set(
    eligibleOriginIds(LAST_TRAINS_NAGOYA, destinationCode)
  );

  const hubEntries = Object.entries(LAST_TRAINS_NAGOYA.origins)
    .filter(([originId]) => eligibleIds.has(originId));

  const walkResults = await Promise.all(
    hubEntries.map(async ([originId, hub]) => {
      try {
        const result = await walk(env, {
          origin: input.origin,
          destination: hub.walkDestination
        });

        return [originId, hub, result];
      } catch (error) {
        return [
          originId,
          hub,
          {
            routeFound: false,
            error: String(error?.message || error)
          }
        ];
      }
    })
  );

  const walkOptions = {};
  const hubAccess = {};

  for (const [originId, hub, result] of walkResults) {
    const walkMinutes =
      result.routeFound && result.durationSeconds != null
        ? Math.ceil(result.durationSeconds / 60)
        : null;

    walkOptions[originId] = {
      originId,
      originName: hub.name,
      destination: hub.walkDestination,
      routeFound: result.routeFound === true,
      distanceMeters: result.distanceMeters ?? null,
      durationSeconds: result.durationSeconds ?? null,
      walkMinutes,
      error: result.error ?? null
    };

    if (walkMinutes != null) {
      hubAccess[originId] = { walkMinutes };
    }
  }

  if (Object.keys(hubAccess).length === 0) {
    return {
      routeFound: false,
      reason: "walk_routes_not_found",
      walkOptions
    };
  }

  const decision = evaluateLastTrainBoundary(
    LAST_TRAINS_NAGOYA,
    {
      departureTime: input.departureTime,
      dayType: input.dayType,
      destinationCode,
      offsetMinutes: input.offsetMinutes,
      stationBufferMinutes,
      minimumBoardingLeadMinutes,
      hubAccess
    }
  );

  return {
    routeFound: true,
    dataSource: "internal_last_train_json",
    walkOptions,
    ...decision
  };
}

async function tonightDecision(env, input) {
  if (!input.origin) throw new Error("origin is required");
  if (!input.departureTime) throw new Error("departureTime is required");

  const destinationCode = input.destinationCode || "H22";
  const destination = LAST_TRAINS_NAGOYA.destinations[destinationCode];

  if (!destination?.enabled) {
    throw new Error(`destination is not enabled: ${destinationCode}`);
  }

  const taxiDestination =
    input.taxiDestination ||
    `${destination.name}駅 愛知県名古屋市`;

  const homeHubEntry = Object.entries(LAST_TRAINS_NAGOYA.origins)
    .find(([, hub]) =>
      hub.enabled &&
      hub.stationCodes?.includes(destinationCode)
    );

  if (homeHubEntry) {
    const [hubId, hub] = homeHubEntry;

    const walkResult = await walk(env, {
      origin: input.origin,
      destination: hub.walkDestination
    }).catch((error) => ({
      routeFound: false,
      error: String(error?.message || error)
    }));

    const taxiResult = await safeTaxiEstimate(env, {
      origin: input.origin,
      destination: taxiDestination,
      departureTime: input.departureTime,
      includeDispatchFee: input.includeDispatchFee !== false
    });

    return {
      taxiDestination,
      ...composeWalkHomeDecision({
        departureTime: input.departureTime,
        offsetMinutes: input.offsetMinutes,
        destinationCode,
        destinationName: destination.name,
        hubId,
        hubName: hub.name,
        walkResult,
        taxiEstimate: taxiResult
      })
    };
  }

  const trainDecision = await lastTrainBoundaryFromCurrentLocation(
    env,
    {
      ...input,
      destinationCode
    }
  );

  const taxiResult = await safeTaxiEstimate(env, {
    origin: input.origin,
    destination: taxiDestination,
    departureTime: input.departureTime,
    includeDispatchFee: input.includeDispatchFee !== false
  });

  return {
    destinationCode,
    destinationName: destination.name,
    taxiDestination,
    ...composeTonightDecision(trainDecision, taxiResult)
  };
}

async function safeTaxiEstimate(env, input) {
  try {
    return await taxiEstimate(env, input);
  } catch (error) {
    return {
      routeFound: false,
      error: String(error?.message || error)
    };
  }
}

async function taxiEstimate(env, input) {
  if (!input.origin) throw new Error("origin is required");
  if (!input.destination) throw new Error("destination is required");

  const departureTime = input.departureTime || new Date().toISOString();
  const driveResult = await drive(env, {
    origin: input.origin,
    destination: input.destination,
    departureTime
  });

  if (!driveResult.routeFound) {
    return { routeFound: false };
  }

  return {
    routeFound: true,
    durationSeconds: driveResult.durationSeconds,
    ...estimateNagoyaTaxiFare({
      distanceMeters: driveResult.distanceMeters,
      departureTime,
      includeDispatchFee: input.includeDispatchFee !== false
    })
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
        buildSha: env.BUILD_SHA || null,
        googleApiKeyConfigured: Boolean(env.GOOGLE_MAPS_API_KEY)
      });
    }

    if (request.method !== "POST") {
      return json({ error: "Not found" }, 404);
    }

    try {
      const input = await request.json();

      if (url.pathname === "/api/drive") {
        return json(await drive(env, input));
      }

      if (url.pathname === "/api/walk") {
        return json(await walk(env, input));
      }

      if (url.pathname === "/api/last-train-boundary") {
        return json(await lastTrainBoundaryFromCurrentLocation(env, input));
      }

      if (url.pathname === "/api/taxi-estimate") {
        return json(await taxiEstimate(env, input));
      }

      if (url.pathname === "/api/tonight-decision") {
        return json(await tonightDecision(env, input));
      }

      return json({ error: "Not found" }, 404);
    } catch (error) {
      return json({ error: String(error?.message || error) }, 400);
    }
  }
};
