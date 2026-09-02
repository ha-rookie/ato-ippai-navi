import { normalizeSleepSettings } from "./sleep.js";

export const SLEEP_SETTINGS_STORAGE_KEY =
  "atoIppaiNavi.sleepSettings.v1";

function resolveStorage(storage) {
  if (storage) return storage;

  if (typeof window !== "undefined" && window.localStorage) {
    return window.localStorage;
  }

  throw new Error("localStorage is not available");
}

export function saveSleepSettings(settingsInput, storage) {
  const settings = normalizeSleepSettings(settingsInput);
  const target = resolveStorage(storage);

  target.setItem(
    SLEEP_SETTINGS_STORAGE_KEY,
    JSON.stringify(settings)
  );

  return settings;
}

export function loadSleepSettings(storage) {
  const target = resolveStorage(storage);
  const raw = target.getItem(SLEEP_SETTINGS_STORAGE_KEY);

  if (!raw) return null;

  try {
    return normalizeSleepSettings(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function clearSleepSettings(storage) {
  resolveStorage(storage).removeItem(SLEEP_SETTINGS_STORAGE_KEY);
}


export const DESTINATION_STATION_STORAGE_KEY =
  "atoIppaiNavi.destinationStation.v1";

export function normalizeDestinationStation(value) {
  const code = String(value ?? "").trim().toUpperCase();
  const match = /^([HTMESK])(\d{1,2})$/.exec(code);

  if (!match) {
    throw new Error("destination station must be H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, or K01");
  }

  const line = match[1];
  const number = Number(match[2]);
  const max = { H: 22, T: 20, M: 28, E: 7, S: 21, K: 1 }[line];

  if (number < 1 || number > max) {
    throw new Error("destination station must be H01-H22, T01-T20, M01-M28, E01-E07, S01-S21, or K01");
  }

  return `${line}${String(number).padStart(2, "0")}`;
}

export function saveDestinationStation(value, storage) {
  const code = normalizeDestinationStation(value);
  const target = resolveStorage(storage);
  target.setItem(DESTINATION_STATION_STORAGE_KEY, code);
  return code;
}

export function loadDestinationStation(storage) {
  const target = resolveStorage(storage);
  const raw = target.getItem(DESTINATION_STATION_STORAGE_KEY);

  if (!raw) return null;

  try {
    return normalizeDestinationStation(raw);
  } catch {
    return null;
  }
}

export function clearDestinationStation(storage) {
  resolveStorage(storage).removeItem(DESTINATION_STATION_STORAGE_KEY);
}
