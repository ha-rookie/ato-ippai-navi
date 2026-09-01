const TOKYO_PARTS = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

const TOKYO_CLOCK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

function toFiniteNonNegative(value, field) {
  const number = Number(value);

  if (!Number.isFinite(number) || number < 0) {
    throw new Error(`${field} must be a non-negative number`);
  }

  return number;
}

function parseWakeTime(value) {
  const match = /^(\d{2}):(\d{2})$/.exec(String(value ?? ""));

  if (!match) {
    throw new Error("wakeTime must be HH:mm");
  }

  const hour = Number(match[1]);
  const minute = Number(match[2]);

  if (hour > 23 || minute > 59) {
    throw new Error("wakeTime must be a valid HH:mm");
  }

  return { hour, minute };
}

function tokyoParts(date) {
  return Object.fromEntries(
    TOKYO_PARTS.formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, Number(part.value)])
  );
}

function tokyoDate(year, month, day, hour, minute) {
  // Japan Standard Time is UTC+09:00 and has no daylight-saving time.
  return new Date(Date.UTC(year, month - 1, day, hour - 9, minute, 0, 0));
}

function nextWakeDate(bedtime, wakeTime) {
  const { hour, minute } = parseWakeTime(wakeTime);
  const local = tokyoParts(bedtime);

  let candidate = tokyoDate(
    local.year,
    local.month,
    local.day,
    hour,
    minute
  );

  if (candidate <= bedtime) {
    candidate = tokyoDate(
      local.year,
      local.month,
      local.day + 1,
      hour,
      minute
    );
  }

  return candidate;
}

function localClock(date) {
  return TOKYO_CLOCK.format(date);
}

function durationLabel(totalMinutes) {
  const minutes = Math.max(0, Math.floor(totalMinutes));
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;

  return `${hours}時間${remainder}分`;
}

export function normalizeSleepSettings(input) {
  if (!input || typeof input !== "object") {
    throw new Error("sleep settings are required");
  }

  return {
    stationToHomeMinutes: toFiniteNonNegative(
      input.stationToHomeMinutes,
      "stationToHomeMinutes"
    ),
    bedtimePrepMinutes: toFiniteNonNegative(
      input.bedtimePrepMinutes,
      "bedtimePrepMinutes"
    ),
    wakeTime: (() => {
      parseWakeTime(input.wakeTime);
      return String(input.wakeTime);
    })()
  };
}

export function calculateSleepEstimate(
  destinationStationArrivalTime,
  settingsInput
) {
  const stationArrival = new Date(destinationStationArrivalTime);

  if (Number.isNaN(stationArrival.getTime())) {
    throw new Error(
      "destinationStationArrivalTime must be a valid ISO 8601 datetime"
    );
  }

  const settings = normalizeSleepSettings(settingsInput);

  const homeArrival = new Date(
    stationArrival.getTime() + settings.stationToHomeMinutes * 60000
  );

  const bedtime = new Date(
    homeArrival.getTime() + settings.bedtimePrepMinutes * 60000
  );

  const wake = nextWakeDate(bedtime, settings.wakeTime);
  const sleepMinutes = Math.max(
    0,
    Math.floor((wake.getTime() - bedtime.getTime()) / 60000)
  );

  return {
    destinationStationArrivalTime: stationArrival.toISOString(),
    localDestinationStationArrivalTime: localClock(stationArrival),
    stationToHomeMinutes: settings.stationToHomeMinutes,
    estimatedHomeArrivalTime: homeArrival.toISOString(),
    localEstimatedHomeArrivalTime: localClock(homeArrival),
    bedtimePrepMinutes: settings.bedtimePrepMinutes,
    estimatedBedtime: bedtime.toISOString(),
    localEstimatedBedtime: localClock(bedtime),
    wakeTime: settings.wakeTime,
    estimatedWakeTime: wake.toISOString(),
    localEstimatedWakeTime: localClock(wake),
    sleepMinutes,
    sleepHours: Math.round((sleepMinutes / 60) * 10) / 10,
    sleepLabel: durationLabel(sleepMinutes)
  };
}

export function enrichTonightDecisionWithSleep(
  tonightDecision,
  settingsInput
) {
  const settings = normalizeSleepSettings(settingsInput);

  return {
    ...tonightDecision,
    sleepPrivacy: {
      calculation: "client_only",
      sendsHomeAddressToServer: false,
      sendsWakeTimeToServer: false
    },
    scenarios: (tonightDecision?.scenarios || []).map((scenario) => {
      const arrival = scenario.estimatedDestinationStationArrivalTime;

      if (!arrival) {
        return {
          ...scenario,
          sleep: null
        };
      }

      return {
        ...scenario,
        sleep: calculateSleepEstimate(arrival, settings)
      };
    })
  };
}
