export function composeTonightDecision(trainDecision, taxiEstimate) {
  const taxiAvailable = taxiEstimate?.routeFound === true;
  const taxiEstimatedTotalYen =
    taxiAvailable && Number.isFinite(Number(taxiEstimate.estimatedTotalYen))
      ? Number(taxiEstimate.estimatedTotalYen)
      : null;

  const scenarios = (trainDecision?.scenarios || []).map((scenario) => {
    let recommendedMode = "unknown";
    let status = "unavailable";

    if (scenario.canReachDestination) {
      recommendedMode = "train";
      status = "train_available";
    } else if (taxiAvailable) {
      recommendedMode = "taxi";
      status = "taxi_fallback";
    }

    return {
      ...scenario,
      recommendedMode,
      status,
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
