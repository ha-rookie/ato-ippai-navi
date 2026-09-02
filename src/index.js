import {
  evaluateSakaeToFujigaoka,
  evaluateSakaeToFujigaokaWithAccess
} from "./decision.js";
import { estimateNagoyaTaxiFare } from "./taxi.js";
import { composeTonightDecision } from "./tonight.js";
import { evaluateLastTrainBoundary } from "./last-train.js";
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
  if (!input.origin) throw new Error("origin is required");
  if (!input.destination) throw new Error("destination is required");

  const requestReferenceTime =
    input.departureTime || new Date().toISOString();

  const body = {
    origin: waypoint(input.origin),
    destination: waypoint(input.destination),
    travelMode: "TRANSIT",
    languageCode: input.languageCode || "ja",
    units: "METRIC"
  };

  if (!input.omitRegionCode) {
    body.regionCode = input.regionCode || "JP";
  }

  // Google公式仕様ではdepartureTimeを省略すると実行時刻(now)が使われる。
  // PoCでは明示時刻と省略時刻の両方を切り分けられるようにする。
  if (input.departureTime) {
    body.departureTime = input.departureTime;
  }

  if (input.computeAlternativeRoutes === true) {
    body.computeAlternativeRoutes = true;
  }

  const transitPreferences = {};

  if (Array.isArray(input.allowedTravelModes)) {
    transitPreferences.allowedTravelModes = input.allowedTravelModes;
  }

  if (input.routingPreference) {
    transitPreferences.routingPreference = input.routingPreference;
  }

  if (Object.keys(transitPreferences).length > 0) {
    body.transitPreferences = transitPreferences;
  }

  const payload = await googleRoutes(
    env,
    body,
    [
      "routes.distanceMeters",
      "routes.duration",
      "routes.travelAdvisory.transitFare",
      "routes.legs.steps.travelMode",
      "routes.legs.steps.transitDetails.stopDetails",
      "routes.legs.steps.transitDetails.transitLine.name",
      "routes.legs.steps.transitDetails.transitLine.nameShort",
      "routes.legs.steps.transitDetails.transitLine.vehicle.type",
      "routes.legs.steps.transitDetails.transitLine.agencies.name",
      "routes.legs.steps.transitDetails.headsign"
    ].join(",")
  );

  const routes = payload.routes || [];

  if (routes.length === 0) {
    return {
      requestedDepartureTime: requestReferenceTime,
      departureTimeMode: input.departureTime ? "explicit" : "google_now",
      requestOptions: {
        computeAlternativeRoutes: input.computeAlternativeRoutes === true,
        allowedTravelModes: input.allowedTravelModes || null,
        routingPreference: input.routingPreference || null,
        regionCode: input.omitRegionCode
          ? null
          : input.regionCode || "JP"
      },
      routeFound: false,
      lateNightReturnPossible: false,
      rawRouteCount: 0,
      routes: []
    };
  }

  const normalizedRoutes = routes.map((route) =>
    normalizeTransit(
      route,
      requestReferenceTime,
      Number(env.MAX_LATE_TRANSIT_WAIT_MINUTES || "90")
    )
  );

  return {
    routeFound: true,
    departureTimeMode: input.departureTime ? "explicit" : "google_now",
    requestOptions: {
      computeAlternativeRoutes: input.computeAlternativeRoutes === true,
      allowedTravelModes: input.allowedTravelModes || null,
      routingPreference: input.routingPreference || null,
      regionCode: input.omitRegionCode
        ? null
        : input.regionCode || "JP"
    },
    rawRouteCount: routes.length,
    ...normalizedRoutes[0],
    routes: normalizedRoutes
  };
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

function addMinutes(iso, minutes) {
  return new Date(
    new Date(iso).getTime() + Number(minutes) * 60000
  ).toISOString();
}

async function lastTrainBoundaryFromCurrentLocation(env, input) {
  if (!input.origin) throw new Error("origin is required");
  if (!input.departureTime) throw new Error("departureTime is required");

  const destinationCode = input.destinationCode || "H22";
  const stationBufferMinutes = Number(input.stationBufferMinutes ?? 3);
  const minimumBoardingLeadMinutes = Number(
    input.minimumBoardingLeadMinutes ?? 1
  );

  const hubEntries = Object.entries(LAST_TRAINS_NAGOYA.origins)
    .filter(([, hub]) => hub.enabled);

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

async function decisionFromCurrentLocation(env, input) {
  if (!input.origin) throw new Error("origin is required");
  if (!input.departureTime) throw new Error("departureTime is required");

  const stationDestination =
    input.stationDestination || "栄駅 愛知県名古屋市";

  const walkResult = await walk(env, {
    origin: input.origin,
    destination: stationDestination
  });

  if (!walkResult.routeFound || walkResult.durationSeconds == null) {
    return {
      routeFound: false,
      reason: "walk_route_not_found",
      stationDestination
    };
  }

  const walkMinutes = Math.ceil(walkResult.durationSeconds / 60);
  const stationBufferMinutes = Number(input.stationBufferMinutes ?? 3);
  const minimumBoardingLeadMinutes = Number(
    input.minimumBoardingLeadMinutes ?? 1
  );

  const decision = evaluateSakaeToFujigaokaWithAccess({
    departureTime: input.departureTime,
    dayType: input.dayType,
    offsetMinutes: input.offsetMinutes,
    walkMinutes,
    stationBufferMinutes,
    minimumBoardingLeadMinutes
  });

  return {
    routeFound: true,
    walk: {
      destination: stationDestination,
      distanceMeters: walkResult.distanceMeters,
      durationSeconds: walkResult.durationSeconds,
      walkMinutes,
      note:
        "徒歩経路はGoogle Routes APIの推定です。駅構内移動はstationBufferMinutesで別途加算します。"
    },
    ...decision
  };
}

async function tonightDecision(env, input) {
  if (!input.origin) throw new Error("origin is required");
  if (!input.departureTime) throw new Error("departureTime is required");

  const trainDecision = await lastTrainBoundaryFromCurrentLocation(
    env,
    {
      ...input,
      destinationCode: input.destinationCode || "H22"
    }
  );

  const taxiDestination =
    input.taxiDestination || "藤が丘駅 愛知県名古屋市";

  const taxiResult = await taxiEstimate(env, {
    origin: input.origin,
    destination: taxiDestination,
    departureTime: input.departureTime,
    includeDispatchFee: input.includeDispatchFee !== false
  });

  return {
    taxiDestination,
    ...composeTonightDecision(trainDecision, taxiResult)
  };
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
        buildSha: env.BUILD_SHA || null,
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

      if (url.pathname === "/api/walk") {
        return json(await walk(env, input));
      }

      if (url.pathname === "/api/evaluate") {
        return json(await evaluate(env, input));
      }

      if (url.pathname === "/api/decision-poc") {
        return json(evaluateSakaeToFujigaoka(input));
      }

      if (url.pathname === "/api/last-train-boundary") {
        return json(await lastTrainBoundaryFromCurrentLocation(env, input));
      }

      if (url.pathname === "/api/decision-from-current-location") {
        return json(await decisionFromCurrentLocation(env, input));
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
