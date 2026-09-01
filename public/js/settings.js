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
