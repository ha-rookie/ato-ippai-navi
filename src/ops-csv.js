const DISPLAY_BY_PREFIX = [
  ["JR-CJ", "JR東海", "関西本線"],
  ["JR-CF", "JR東海", "中央本線"],
  ["JR-CA", "JR東海", "東海道本線"],
  ["KT-E", "近畿日本鉄道", "名古屋線"],
  ["ST", "名古屋鉄道", "瀬戸線"],
  ["NH", "名古屋鉄道", "名古屋本線"],
  ["TA", "名古屋鉄道", "常滑線"],
  ["IY", "名古屋鉄道", "犬山線"],
  ["CH", "名古屋鉄道", "築港線"],
  ["KM", "名古屋鉄道", "小牧線"],
  ["AN", "名古屋臨海高速鉄道", "あおなみ線"],
  ["H", "名古屋市交通局", "東山線"],
  ["T", "名古屋市交通局", "鶴舞線"],
  ["M", "名古屋市交通局", "名城線"],
  ["E", "名古屋市交通局", "名港線"],
  ["S", "名古屋市交通局", "桜通線"],
  ["K", "名古屋市交通局", "上飯田線"]
];

export const LAST_TRAIN_OPS_HEADERS = [
  "目的駅コード",
  "駅名",
  "事業者",
  "路線",
  "hub",
  "曜日区分",
  "最終出発",
  "最終到着",
  "経路概要",
  "列車行先",
  "乗換回数",
  "乗換駅",
  "接続列車発車",
  "乗換余裕(分)",
  "status",
  "sourceIds"
];

function displayForDestination(code) {
  const match = DISPLAY_BY_PREFIX.find(([prefix]) => code.startsWith(prefix));
  if (!match) return { operator: "不明", line: "不明" };
  return { operator: match[1], line: match[2] };
}

function safeCell(value) {
  if (value == null) return "";
  const text = String(value);
  return /^[=+\-@]/.test(text) ? `'${text}` : text;
}

function csvCell(value) {
  return `"${safeCell(value).replaceAll('"', '""')}"`;
}

export function flattenLastTrainBoundaries(data) {
  const rows = [];

  for (const [destinationCode, destination] of Object.entries(data.destinations || {})) {
    const { operator, line } = displayForDestination(destinationCode);

    for (const [originId, dayTypes] of Object.entries(destination.routes || {})) {
      const hubName = data.origins?.[originId]?.name || originId;

      for (const [dayType, route] of Object.entries(dayTypes || {})) {
        rows.push([
          destinationCode,
          destination.name || "",
          operator,
          line,
          hubName,
          dayType === "weekday" ? "平日" : dayType === "saturday_holiday" ? "土休日" : dayType,
          route.lastDeparture ?? "",
          route.lastArrival ?? "",
          route.routeSummary ?? "",
          route.trainTerminal ?? "",
          route.transfers ?? "",
          route.transferAt ?? "",
          route.connectionDeparture ?? "",
          route.transferMarginMinutes ?? "",
          route.status ?? "",
          Array.isArray(route.sourceIds) ? route.sourceIds.join(" / ") : ""
        ]);
      }
    }
  }

  return rows;
}

export function lastTrainBoundariesCsv(data) {
  const rows = [LAST_TRAIN_OPS_HEADERS, ...flattenLastTrainBoundaries(data)];
  return `${rows.map((row) => row.map(csvCell).join(",")).join("\r\n")}\r\n`;
}
