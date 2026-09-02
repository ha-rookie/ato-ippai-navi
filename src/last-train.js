const TOKYO_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

function tokyoHourMinute(date) {
  const parts = Object.fromEntries(
    TOKYO_TIME.formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value])
  );

  return {
    hour: Number(parts.hour),
    minute: Number(parts.minute)
  };
}

function localClock(date) {
  const { hour, minute } = tokyoHourMinute(date);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function serviceMinutesAt(date) {
  const { hour, minute } = tokyoHourMinute(date);
  return (hour < 4 ? hour + 24 : hour) * 60 + minute;
}

export function clockToServiceMinutes(clock) {
  const match = /^(\d{2}):(\d{2})$/.exec(String(clock ?? ""));

  if (!match) {
    throw new Error(`invalid clock: ${clock}`);
  }

  const hour = Number(match[1]);
  const minute = Number(match[2]);

  if (hour > 23 || minute > 59) {
    throw new Error(`invalid clock: ${clock}`);
  }

  return (hour < 4 ? hour + 24 : hour) * 60 + minute;
}

function routeEntry(dataset, destinationCode, originId, dayType) {
  const destination = dataset?.destinations?.[destinationCode];

  if (!destination?.enabled) {
    throw new Error(`destination is not enabled: ${destinationCode}`);
  }

  const origin = dataset?.origins?.[originId];

  if (!origin?.enabled) {
    throw new Error(`origin is not enabled: ${originId}`);
  }

  const route = destination.routes?.[originId]?.[dayType];

  if (!route || route.status !== "verified") {
    return null;
  }

  return { origin, destination, route };
}

function estimateServiceDate(referenceDate, targetServiceMinutes) {
  const referenceServiceMinutes = serviceMinutesAt(referenceDate);
  const minuteAligned = new Date(referenceDate);
  minuteAligned.setUTCSeconds(0, 0);

  return new Date(
    minuteAligned.getTime() +
      (targetServiceMinutes - referenceServiceMinutes) * 60000
  );
}

function evaluateHub({
  dataset,
  destinationCode,
  originId,
  dayType,
  leaveDate,
  walkMinutes,
  stationBufferMinutes,
  minimumBoardingLeadMinutes
}) {
  const context = routeEntry(dataset, destinationCode, originId, dayType);

  if (!context) {
    return {
      originId,
      available: false,
      reason: "verified_route_not_found"
    };
  }

  const stationReadyDate = new Date(
    leaveDate.getTime() +
      (walkMinutes + stationBufferMinutes) * 60000
  );

  const readyServiceMinutes = serviceMinutesAt(stationReadyDate);
  const lastDepartureServiceMinutes =
    clockToServiceMinutes(context.route.lastDeparture);
  const lastArrivalServiceMinutes =
    clockToServiceMinutes(context.route.lastArrival);

  const requiredServiceMinutes =
    readyServiceMinutes + minimumBoardingLeadMinutes;

  const canReachDestination =
    requiredServiceMinutes <= lastDepartureServiceMinutes;

  const lastDepartureDate = estimateServiceDate(
    stationReadyDate,
    lastDepartureServiceMinutes
  );

  const lastArrivalDate = new Date(
    lastDepartureDate.getTime() +
      (lastArrivalServiceMinutes - lastDepartureServiceMinutes) * 60000
  );

  return {
    originId,
    originName: context.origin.name,
    available: true,
    walkMinutes,
    stationBufferMinutes,
    minimumBoardingLeadMinutes,
    stationReadyTime: stationReadyDate.toISOString(),
    localStationReadyTime: localClock(stationReadyDate),
    canReachDestination,
    lastDeparture: context.route.lastDeparture,
    estimatedLastDepartureTime: lastDepartureDate.toISOString(),
    localLastDepartureTime: localClock(lastDepartureDate),
    lastArrival: context.route.lastArrival,
    estimatedLastTrainArrivalTime: lastArrivalDate.toISOString(),
    localLastTrainArrivalTime: localClock(lastArrivalDate),
    routeSummary: context.route.routeSummary,
    transfers: context.route.transfers,
    minutesUntilLastDeparture:
      lastDepartureServiceMinutes - readyServiceMinutes,
    usableMarginMinutes:
      lastDepartureServiceMinutes - requiredServiceMinutes,
    sourceIds: context.route.sourceIds
  };
}

export function evaluateLastTrainBoundary(dataset, input) {
  if (!input?.departureTime) {
    throw new Error("departureTime is required");
  }

  const baseDate = new Date(input.departureTime);

  if (Number.isNaN(baseDate.getTime())) {
    throw new Error("departureTime must be a valid ISO 8601 datetime");
  }

  if (!["weekday", "saturday_holiday"].includes(input.dayType)) {
    throw new Error("dayType must be weekday or saturday_holiday");
  }

  const destinationCode = input.destinationCode;
  const destination = dataset?.destinations?.[destinationCode];

  if (!destination?.enabled) {
    throw new Error(`destination is not enabled: ${destinationCode}`);
  }

  const offsets = input.offsetMinutes ?? [0, 15, 30, 60];
  const stationBufferMinutes = Number(input.stationBufferMinutes ?? 3);
  const minimumBoardingLeadMinutes = Number(
    input.minimumBoardingLeadMinutes ?? 1
  );
  const hubAccess = input.hubAccess || {};

  const scenarios = offsets.map((rawOffset) => {
    const offsetMinutes = Number(rawOffset);
    const leaveDate = new Date(
      baseDate.getTime() + offsetMinutes * 60000
    );

    const options = Object.entries(hubAccess)
      .filter(([, access]) => access?.walkMinutes != null)
      .map(([originId, access]) =>
        evaluateHub({
          dataset,
          destinationCode,
          originId,
          dayType: input.dayType,
          leaveDate,
          walkMinutes: Number(access.walkMinutes),
          stationBufferMinutes,
          minimumBoardingLeadMinutes
        })
      );

    const reachable = options
      .filter((option) => option.available && option.canReachDestination)
      .sort((a, b) => {
        if (b.usableMarginMinutes !== a.usableMarginMinutes) {
          return b.usableMarginMinutes - a.usableMarginMinutes;
        }

        return a.walkMinutes - b.walkMinutes;
      });

    const recommended = reachable[0] ?? null;

    return {
      offsetMinutes,
      leaveTime: leaveDate.toISOString(),
      localLeaveTime: localClock(leaveDate),
      canReachDestination: recommended != null,
      recommendedOriginId: recommended?.originId ?? null,
      recommendedOriginName: recommended?.originName ?? null,
      stationReadyTime: recommended?.stationReadyTime ?? null,
      localStationReadyTime: recommended?.localStationReadyTime ?? null,
      lastDeparture: recommended?.lastDeparture ?? null,
      estimatedLastDepartureTime:
        recommended?.estimatedLastDepartureTime ?? null,
      minutesUntilLastDeparture:
        recommended?.minutesUntilLastDeparture ?? null,
      usableMarginMinutes:
        recommended?.usableMarginMinutes ?? null,
      lastArrival: recommended?.lastArrival ?? null,
      estimatedLastTrainArrivalTime:
        recommended?.estimatedLastTrainArrivalTime ?? null,
      localLastTrainArrivalTime:
        recommended?.localLastTrainArrivalTime ?? null,
      estimatedDestinationStationArrivalTime: null,
      localDestinationStationArrivalTime: null,
      arrivalEstimateQuality: "last_train_boundary_only",
      routeSummary: recommended?.routeSummary ?? null,
      transfers: recommended?.transfers ?? null,
      options
    };
  });

  return {
    schemaVersion: dataset.schemaVersion,
    serviceArea: dataset.serviceArea,
    metadata: dataset.metadata,
    destination: {
      code: destinationCode,
      name: destination.name,
      city: destination.city
    },
    dayType: input.dayType,
    baseDepartureTime: baseDate.toISOString(),
    scenarios
  };
}
