const TOKYO_CLOCK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

function localClock(date) {
  return TOKYO_CLOCK.format(date);
}

function addMinutes(date, minutes) {
  return new Date(date.getTime() + Number(minutes) * 60000);
}

function taxiFields(leaveDate, taxiEstimate) {
  if (
    taxiEstimate?.routeFound !== true ||
    !Number.isFinite(Number(taxiEstimate.durationSeconds))
  ) {
    return {
      arrivalTime: null,
      localArrivalTime: null,
      travelMinutes: null
    };
  }

  const travelMinutes = Math.ceil(Number(taxiEstimate.durationSeconds) / 60);
  const arrival = addMinutes(leaveDate, travelMinutes);

  return {
    arrivalTime: arrival.toISOString(),
    localArrivalTime: localClock(arrival),
    travelMinutes
  };
}

export function composeWalkHomeDecision({
  departureTime,
  offsetMinutes = [0, 15, 30, 60],
  destinationCode,
  destinationName,
  hubId,
  hubName,
  walkResult,
  taxiEstimate
}) {
  const baseDate = new Date(departureTime);

  if (Number.isNaN(baseDate.getTime())) {
    throw new Error("departureTime must be a valid ISO 8601 datetime");
  }

  const walkAvailable =
    walkResult?.routeFound === true &&
    Number.isFinite(Number(walkResult.durationSeconds));

  const walkMinutes = walkAvailable
    ? Math.ceil(Number(walkResult.durationSeconds) / 60)
    : null;

  const taxiAvailable = taxiEstimate?.routeFound === true;
  const taxiEstimatedTotalYen =
    taxiAvailable && Number.isFinite(Number(taxiEstimate.estimatedTotalYen))
      ? Number(taxiEstimate.estimatedTotalYen)
      : null;

  const scenarios = offsetMinutes.map((rawOffset) => {
    const offset = Number(rawOffset);
    const leaveDate = addMinutes(baseDate, offset);

    if (walkAvailable) {
      const arrival = addMinutes(leaveDate, walkMinutes);

      return {
        offsetMinutes: offset,
        leaveTime: leaveDate.toISOString(),
        localLeaveTime: localClock(leaveDate),
        canReachDestination: true,
        recommendedMode: "walk",
        status: "walk_available",
        destinationArrivalMode: "walk",
        recommendedOriginId: hubId,
        recommendedOriginName: hubName,
        walkMinutes,
        walkDistanceMeters: walkResult.distanceMeters ?? null,
        estimatedDestinationStationArrivalTime: arrival.toISOString(),
        localDestinationStationArrivalTime: localClock(arrival),
        taxiTravelMinutes: null,
        taxiEstimatedTotalYen
      };
    }

    if (taxiAvailable) {
      const taxi = taxiFields(leaveDate, taxiEstimate);

      return {
        offsetMinutes: offset,
        leaveTime: leaveDate.toISOString(),
        localLeaveTime: localClock(leaveDate),
        canReachDestination: true,
        recommendedMode: "taxi",
        status: "taxi_fallback",
        destinationArrivalMode: "taxi",
        recommendedOriginId: null,
        recommendedOriginName: null,
        walkMinutes: null,
        walkDistanceMeters: null,
        estimatedDestinationStationArrivalTime: taxi.arrivalTime,
        localDestinationStationArrivalTime: taxi.localArrivalTime,
        taxiTravelMinutes: taxi.travelMinutes,
        taxiEstimatedTotalYen
      };
    }

    return {
      offsetMinutes: offset,
      leaveTime: leaveDate.toISOString(),
      localLeaveTime: localClock(leaveDate),
      canReachDestination: false,
      recommendedMode: "unknown",
      status: "unavailable",
      destinationArrivalMode: "unknown",
      recommendedOriginId: null,
      recommendedOriginName: null,
      walkMinutes: null,
      walkDistanceMeters: null,
      estimatedDestinationStationArrivalTime: null,
      localDestinationStationArrivalTime: null,
      taxiTravelMinutes: null,
      taxiEstimatedTotalYen: null
    };
  });

  return {
    destinationScope: "station_only",
    destinationCode,
    destinationName,
    journeyType: "walk_to_home_station",
    walk: {
      routeFound: walkAvailable,
      destinationHubId: hubId,
      destinationHubName: hubName,
      distanceMeters: walkResult?.distanceMeters ?? null,
      durationSeconds: walkResult?.durationSeconds ?? null,
      walkMinutes
    },
    train: null,
    taxi: taxiEstimate,
    scenarios
  };
}
