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

export function evaluateSakaeToFujigaoka(input) {
  const baseDate = assertDecisionInput(input);
  const offsets = input.offsetMinutes ?? [0, 15, 30, 60];
  const schedule = SAKAE_HIGASHIYAMA_LATE.schedules[input.dayType];

  const destinationName = SAKAE_HIGASHIYAMA_LATE.destination.name;
  const destinationTrains = schedule.filter(
    (train) => train.destination === destinationName
  );
  const lastTrain = destinationTrains.at(-1);

  const scenarios = offsets.map((rawOffset) => {
    const offsetMinutes = Number(rawOffset);
    const queryDate = new Date(baseDate.getTime() + offsetMinutes * 60000);
    const currentServiceMinutes = serviceMinutesAt(queryDate);

    const nextTrain =
      destinationTrains.find(
        (train) => train.serviceMinutes >= currentServiceMinutes
      ) ?? null;

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
    route: {
      line: SAKAE_HIGASHIYAMA_LATE.source.line,
      origin: SAKAE_HIGASHIYAMA_LATE.origin,
      destination: SAKAE_HIGASHIYAMA_LATE.destination
    },
    dayType: input.dayType,
    source: SAKAE_HIGASHIYAMA_LATE.source,
    baseDepartureTime: baseDate.toISOString(),
    scenarios
  };
}
