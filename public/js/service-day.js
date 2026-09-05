import { JAPAN_HOLIDAYS } from "./holidays-jp.js";

const TOKYO_PARTS = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

function tokyoParts(date) {
  const value = date instanceof Date ? date : new Date(date);

  if (Number.isNaN(value.getTime())) {
    throw new Error("invalid date");
  }

  const parts = Object.fromEntries(
    TOKYO_PARTS.formatToParts(value)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value])
  );

  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour),
    minute: Number(parts.minute)
  };
}

function dateKey({ year, month, day }) {
  return [
    String(year).padStart(4, "0"),
    String(month).padStart(2, "0"),
    String(day).padStart(2, "0")
  ].join("-");
}

function previousCalendarDate(parts) {
  const previous = new Date(Date.UTC(parts.year, parts.month - 1, parts.day) - 86400000);
  return {
    year: previous.getUTCFullYear(),
    month: previous.getUTCMonth() + 1,
    day: previous.getUTCDate()
  };
}

export function serviceDate(input = new Date()) {
  const parts = tokyoParts(input);
  const calendarDate = {
    year: parts.year,
    month: parts.month,
    day: parts.day
  };

  const resolved = parts.hour < 4
    ? previousCalendarDate(calendarDate)
    : calendarDate;

  return {
    ...resolved,
    key: dateKey(resolved)
  };
}

export function isJapaneseHoliday(dateLike) {
  const resolved = typeof dateLike === "string"
    ? dateLike
    : dateLike?.key || dateKey(dateLike);
  const year = Number(resolved.slice(0, 4));
  const holidays = JAPAN_HOLIDAYS[year];

  if (!holidays) {
    return null;
  }

  return holidays.has(resolved);
}

export function autoDayType(input = new Date()) {
  const day = serviceDate(input);
  const holiday = isJapaneseHoliday(day);

  if (holiday == null) {
    throw new Error(`holiday calendar unavailable for service year ${day.year}`);
  }

  const weekday = new Date(Date.UTC(day.year, day.month - 1, day.day)).getUTCDay();

  return weekday === 0 || weekday === 6 || holiday
    ? "saturday_holiday"
    : "weekday";
}
