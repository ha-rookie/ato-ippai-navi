const TOKYO_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

function localClock(date) {
  const parts = Object.fromEntries(
    TOKYO_TIME.formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value])
  );

  return `${parts.hour}:${parts.minute}`;
}

function taxiArrivalForScenario(scenario, taxiEstimate) {
  if (
    !scenario?.leaveTime ||
    !Number.isFinite(Number(taxiEstimate?.durationSeconds))
  ) {
    return {
      taxiTravelMinutes: null,
      arrivalDate: null
    };
  }

  const taxiTravelMinutes = Math.ceil(
    Number(taxiEstimate.durationSeconds) / 60
  );

  return {
    taxiTravelMinutes,
    arrivalDate: new Date(
      new Date(scenario.leaveTime).getTime() + taxiTravelMinutes * 60000
    )
  };
}

export function composeTonightDecision(trainDecision, taxiEstimate) {
  const taxiAvailable = taxiEstimate?.routeFound === true;
  const taxiEstimatedTotalYen =
    taxiAvailable && Number.isFinite(Number(taxiEstimate.estimatedTotalYen))
      ? Number(taxiEstimate.estimatedTotalYen)
      : null;

  const scenarios = (trainDecision?.scenarios || []).map((scenario) => {
    let recommendedMode = "unknown";
    let status = "unavailable";
    let estimatedDestinationStationArrivalTime = null;
    let localDestinationStationArrivalTime = null;
    let taxiTravelMinutes = null;

    if (scenario.canReachDestination) {
      recommendedMode = "train";
      status = "train_available";
      estimatedDestinationStationArrivalTime =
        scenario.estimatedDestinationStationArrivalTime ?? null;
      localDestinationStationArrivalTime =
        scenario.localDestinationStationArrivalTime ?? null;
    } else if (taxiAvailable) {
      recommendedMode = "taxi";
      status = "taxi_fallback";

      const taxiArrival = taxiArrivalForScenario(scenario, taxiEstimate);
      taxiTravelMinutes = taxiArrival.taxiTravelMinutes;

      if (taxiArrival.arrivalDate) {
        estimatedDestinationStationArrivalTime =
          taxiArrival.arrivalDate.toISOString();
        localDestinationStationArrivalTime = localClock(
          taxiArrival.arrivalDate
        );
      }
    }

    return {
      ...scenario,
      recommendedMode,
      status,
      destinationArrivalMode: recommendedMode,
      estimatedDestinationStationArrivalTime,
      localDestinationStationArrivalTime,
      taxiTravelMinutes,
      taxiEstimatedTotalYen
    };
  });

  return {
    destinationScope: "station_only",
    train: trainDecision,
    taxi: taxiEstimate,
    scenarios
  };
}
