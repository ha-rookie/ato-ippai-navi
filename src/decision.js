import { SAKAE_HIGASHIYAMA_LATE } from "./data/sakae-higashiyama-late.js";

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

function serviceMinutesAt(date) {
  const { hour, minute } = tokyoHourMinute(date);
  const serviceHour = hour < 4 ? hour + 24 : hour;
  return serviceHour * 60 + minute;
}

function localClock(date) {
  const { hour, minute } = tokyoHourMinute(date);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function assertDecisionInput(input) {
  if (!input?.departureTime) {
    throw new Error("departureTime is required");
  }

  const date = new Date(input.departureTime);
  if (Number.isNaN(date.getTime())) {
    throw new Error("departureTime must be a valid ISO 8601 datetime");
  }

  if (!["weekday", "saturday_holiday"].includes(input.dayType)) {
    throw new Error("dayType must be weekday or saturday_holiday");
  }

  if (
    input.offsetMinutes != null &&
    (!Array.isArray(input.offsetMinutes) ||
      input.offsetMinutes.some(
        (value) => !Number.isFinite(Number(value)) || Number(value) < 0
      ))
  ) {
    throw new Error("offsetMinutes must be an array of non-negative numbers");
  }

  return date;
}

function scheduleContext(dayType) {
  const schedule = SAKAE_HIGASHIYAMA_LATE.schedules[dayType];
  const destinationName = SAKAE_HIGASHIYAMA_LATE.destination.name;
  const destinationTrains = schedule.filter(
    (train) => train.destination === destinationName
  );

  return {
    destinationTrains,
    lastTrain: destinationTrains.at(-1)
  };
}

function nextTrainAt(destinationTrains, date) {
  const currentServiceMinutes = serviceMinutesAt(date);
  const nextTrain =
    destinationTrains.find(
      (train) => train.serviceMinutes >= currentServiceMinutes
    ) ?? null;

  return {
    currentServiceMinutes,
    nextTrain
  };
}

function routeMetadata() {
  return {
    line: SAKAE_HIGASHIYAMA_LATE.source.line,
    origin: SAKAE_HIGASHIYAMA_LATE.origin,
    destination: SAKAE_HIGASHIYAMA_LATE.destination
  };
}

export function evaluateSakaeToFujigaoka(input) {
  const baseDate = assertDecisionInput(input);
  const offsets = input.offsetMinutes ?? [0, 15, 30, 60];
  const { destinationTrains, lastTrain } = scheduleContext(input.dayType);

  const scenarios = offsets.map((rawOffset) => {
    const offsetMinutes = Number(rawOffset);
    const queryDate = new Date(baseDate.getTime() + offsetMinutes * 60000);
    const { currentServiceMinutes, nextTrain } = nextTrainAt(
      destinationTrains,
      queryDate
    );

    return {
      offsetMinutes,
      queryTime: queryDate.toISOString(),
      localTime: localClock(queryDate),
      canReachDestination: nextTrain != null,
      nextTrain: nextTrain?.time ?? null,
      lastTrain: lastTrain.time,
      minutesUntilLastTrain: lastTrain.serviceMinutes - currentServiceMinutes
    };
  });

  return {
    route: routeMetadata(),
    dayType: input.dayType,
    source: SAKAE_HIGASHIYAMA_LATE.source,
    baseDepartureTime: baseDate.toISOString(),
    scenarios
  };
}

export function evaluateSakaeToFujigaokaWithAccess(input) {
  const baseDate = assertDecisionInput(input);
  const offsets = input.offsetMinutes ?? [0, 15, 30, 60];

  const walkMinutes = Number(input.walkMinutes);
  const stationBufferMinutes = Number(input.stationBufferMinutes ?? 3);

  if (!Number.isFinite(walkMinutes) || walkMinutes < 0) {
    throw new Error("walkMinutes must be a non-negative number");
  }

  if (!Number.isFinite(stationBufferMinutes) || stationBufferMinutes < 0) {
    throw new Error("stationBufferMinutes must be a non-negative number");
  }

  const { destinationTrains, lastTrain } = scheduleContext(input.dayType);
  const accessMinutes = walkMinutes + stationBufferMinutes;

  const scenarios = offsets.map((rawOffset) => {
    const offsetMinutes = Number(rawOffset);
    const leaveDate = new Date(baseDate.getTime() + offsetMinutes * 60000);
    const stationReadyDate = new Date(
      leaveDate.getTime() + accessMinutes * 60000
    );

    const { currentServiceMinutes, nextTrain } = nextTrainAt(
      destinationTrains,
      stationReadyDate
    );

    return {
      offsetMinutes,
      leaveTime: leaveDate.toISOString(),
      localLeaveTime: localClock(leaveDate),
      walkMinutes,
      stationBufferMinutes,
      stationReadyTime: stationReadyDate.toISOString(),
      localStationReadyTime: localClock(stationReadyDate),
      canReachDestination: nextTrain != null,
      nextTrain: nextTrain?.time ?? null,
      minutesUntilNextTrain:
        nextTrain == null
          ? null
          : nextTrain.serviceMinutes - currentServiceMinutes,
      lastTrain: lastTrain.time,
      minutesUntilLastTrain: lastTrain.serviceMinutes - currentServiceMinutes
    };
  });

  return {
    route: routeMetadata(),
    dayType: input.dayType,
    source: SAKAE_HIGASHIYAMA_LATE.source,
    baseDepartureTime: baseDate.toISOString(),
    access: {
      walkMinutes,
      stationBufferMinutes,
      totalAccessMinutes: accessMinutes
    },
    scenarios
  };
}
