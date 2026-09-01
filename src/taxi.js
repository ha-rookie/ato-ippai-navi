const TOKYO_HOUR = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  hourCycle: "h23"
});

export const NAGOYA_TAXI_FARE = {
  source: {
    publisher: "名古屋タクシー協会",
    effectiveDate: "2025-10-14",
    url: "https://www.meitakyo.com/price/"
  },
  ordinaryCar: {
    initialDistanceMeters: 910,
    initialFareYen: 500,
    additionalDistanceMeters: 232,
    additionalFareYen: 100,
    lowSpeedSecondsPerUnit: 85,
    lowSpeedFareYen: 100,
    nightStartHour: 22,
    nightEndHour: 5,
    nightSurchargeRate: 0.2,
    longDistanceDiscountThresholdYen: 5000,
    longDistanceDiscountRate: 0.1,
    standardDispatchFeeYen: 200
  }
};

function tokyoHour(date) {
  return Number(TOKYO_HOUR.format(date));
}

export function isNagoyaTaxiNight(departureTime) {
  const date = new Date(departureTime);
  if (Number.isNaN(date.getTime())) {
    throw new Error("departureTime must be a valid ISO 8601 datetime");
  }

  const hour = tokyoHour(date);
  return hour >= 22 || hour < 5;
}

function distanceFare(distanceMeters, night) {
  const fare = NAGOYA_TAXI_FARE.ordinaryCar;

  // 名古屋地区の深夜早朝2割増は、PoCでは距離を1.2倍した
  // 「メーター距離相当」として近似する。実際のメーター運賃は
  // 時間距離併用・待ち時間・事業者差等により異なる。
  const equivalentDistance = night
    ? distanceMeters * (1 + fare.nightSurchargeRate)
    : distanceMeters;

  if (equivalentDistance <= fare.initialDistanceMeters) {
    return {
      equivalentDistanceMeters: equivalentDistance,
      fareBeforeLongDistanceDiscountYen: fare.initialFareYen
    };
  }

  const increments = Math.ceil(
    (equivalentDistance - fare.initialDistanceMeters) /
      fare.additionalDistanceMeters
  );

  return {
    equivalentDistanceMeters: equivalentDistance,
    fareBeforeLongDistanceDiscountYen:
      fare.initialFareYen + increments * fare.additionalFareYen
  };
}

export function estimateNagoyaTaxiFare({
  distanceMeters,
  departureTime,
  includeDispatchFee = true
}) {
  const distance = Number(distanceMeters);

  if (!Number.isFinite(distance) || distance < 0) {
    throw new Error("distanceMeters must be a non-negative number");
  }

  const night = isNagoyaTaxiNight(departureTime);
  const fare = NAGOYA_TAXI_FARE.ordinaryCar;
  const distanceResult = distanceFare(distance, night);

  const amountOverThreshold = Math.max(
    0,
    distanceResult.fareBeforeLongDistanceDiscountYen -
      fare.longDistanceDiscountThresholdYen
  );

  const longDistanceDiscountYen = Math.round(
    amountOverThreshold * fare.longDistanceDiscountRate
  );

  const distanceOnlyMeterFareYen =
    distanceResult.fareBeforeLongDistanceDiscountYen -
    longDistanceDiscountYen;

  const dispatchFeeYen = includeDispatchFee
    ? fare.standardDispatchFeeYen
    : 0;

  return {
    method: "distance_only_approximation",
    distanceMeters: distance,
    nightSurcharge: night,
    nightSurchargeRate: night ? fare.nightSurchargeRate : 0,
    equivalentDistanceMeters: Math.round(
      distanceResult.equivalentDistanceMeters
    ),
    fareBeforeLongDistanceDiscountYen:
      distanceResult.fareBeforeLongDistanceDiscountYen,
    longDistanceDiscountYen,
    distanceOnlyMeterFareYen,
    dispatchFeeYen,
    estimatedTotalYen: distanceOnlyMeterFareYen + dispatchFeeYen,
    source: NAGOYA_TAXI_FARE.source,
    disclaimer:
      "距離制のみの参考概算です。時速10km以下の時間距離併用運賃、待料金、道路状況、迎車条件、事業者ごとの運賃差は反映していないため、実際の料金は高くなる場合があります。"
  };
}
