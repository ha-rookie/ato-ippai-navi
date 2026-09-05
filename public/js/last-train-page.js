import {
  loadDestinationStation,
  saveDestinationStation
} from "./settings.js";
import { autoDayType } from "./service-day.js";

const TOKYO_CLOCK = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23"
});

const state = {
  origin: null,
  checking: false
};

function ensureStyles() {
  if (document.querySelector('link[href="/last-train.css"]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/last-train.css";
  document.head.appendChild(link);
}

function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("このブラウザは位置情報に対応していません"));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
      },
      (error) => {
        const messages = {
          1: "位置情報の利用が許可されていません",
          2: "現在地を取得できませんでした",
          3: "現在地の取得がタイムアウトしました"
        };
        reject(new Error(messages[error.code] || "現在地を取得できませんでした"));
      },
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 60000
      }
    );
  });
}

function clock(date) {
  return TOKYO_CLOCK.format(date);
}

function countdownLabel(minutes) {
  const value = Math.max(0, Math.floor(Number(minutes) || 0));
  const hours = Math.floor(value / 60);
  const rest = value % 60;

  if (hours > 0) {
    return `あと${hours}時間${String(rest).padStart(2, "0")}分`;
  }

  return `あと${rest}分`;
}

function deadlineForScenario(scenario) {
  if (
    !scenario?.leaveTime ||
    !Number.isFinite(Number(scenario?.usableMarginMinutes))
  ) {
    return null;
  }

  return new Date(
    new Date(scenario.leaveTime).getTime() +
      Number(scenario.usableMarginMinutes) * 60000
  );
}

function currentDayType(dayTypeSelect, dayTypeStatus) {
  try {
    const value = autoDayType(new Date());
    dayTypeSelect.value = value;
    dayTypeSelect.classList.add("last-train-hidden");
    dayTypeStatus.textContent = value === "weekday"
      ? "平日ダイヤ（自動判定）"
      : "土休日ダイヤ（自動判定）";
    return value;
  } catch {
    dayTypeSelect.classList.remove("last-train-hidden");
    dayTypeStatus.textContent = "曜日区分を選択してください";
    return dayTypeSelect.value;
  }
}

async function fetchBoundary({ origin, destinationCode, dayType }) {
  const response = await fetch("/api/last-train-boundary", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      origin,
      departureTime: new Date().toISOString(),
      dayType,
      destinationCode,
      offsetMinutes: [0],
      stationBufferMinutes: 3,
      minimumBoardingLeadMinutes: 1
    })
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.error || "終電を確認できませんでした");
  }
  return data;
}

function bestUnavailableOption(scenario) {
  return [...(scenario?.options || [])]
    .filter((option) => option?.available)
    .sort((a, b) =>
      Number(b.usableMarginMinutes ?? -99999) -
      Number(a.usableMarginMinutes ?? -99999)
    )[0] || null;
}

function routeRowsHtml(scenario, destinationName) {
  const rows = [];
  rows.push(`
    <div class="last-train-route-row">
      <span>${scenario.recommendedOriginName}</span>
      <strong>${scenario.lastDeparture} 発</strong>
    </div>
  `);

  if (scenario.transferAt && scenario.connectionDeparture) {
    rows.push(`
      <div class="last-train-route-row">
        <span>${scenario.transferAt} 乗換</span>
        <strong>${scenario.connectionDeparture} 発</strong>
      </div>
    `);
  }

  if (scenario.localLastTrainArrivalTime) {
    rows.push(`
      <div class="last-train-route-row">
        <span>${destinationName}</span>
        <strong>${scenario.localLastTrainArrivalTime} 着</strong>
      </div>
    `);
  }

  return rows.join("");
}

function detailsHtml(scenario) {
  const option = (scenario.options || []).find(
    (candidate) => candidate.originId === scenario.recommendedOriginId
  );
  const lines = [];

  if (Number.isFinite(Number(option?.walkMinutes))) {
    lines.push(`現在地 → ${scenario.recommendedOriginName}駅　徒歩 約${option.walkMinutes}分`);
  }
  lines.push("駅構内3分＋乗車前1分の安全マージンを含む");

  if (scenario.transferAt && Number.isFinite(Number(scenario.transferMarginMinutes))) {
    lines.push(`${scenario.transferAt}での乗換余裕 ${scenario.transferMarginMinutes}分`);
  }

  return lines.map((line) => `<div>${line}</div>`).join("");
}

function renderAvailable(result, data, scenario, destinationName) {
  const deadline = deadlineForScenario(scenario);
  const margin = Math.max(0, Number(scenario.usableMarginMinutes || 0));
  const warning = margin <= 10;

  result.className = `last-train-primary${warning ? " warning" : ""}`;
  result.innerHTML = `
    <p class="last-train-kicker">${warning ? "LAST TRAIN / LEAVE NOW" : "LAST TRAIN"}</p>
    <p class="last-train-deadline">
      ここを <strong>${deadline ? clock(deadline) : "--:--"}</strong> までに<br>
      出れば間に合います
    </p>
    <div class="last-train-countdown">${countdownLabel(margin)}</div>

    <div class="last-train-route">
      ${routeRowsHtml(scenario, destinationName)}
    </div>

    ${scenario.routeSummary ? `<div class="last-train-route-summary">${scenario.routeSummary}</div>` : ""}

    <details class="last-train-details" id="lastTrainRouteDetails">
      <summary>経路詳細</summary>
      <div class="last-train-details-body">
        ${detailsHtml(scenario)}
      </div>
    </details>

    <div class="last-train-actions">
      <button class="last-train-action-button" id="lastTrainRefreshButton" type="button">現在地を更新</button>
      <a class="last-train-action-link" href="/">あと一杯判定へ</a>
    </div>
  `;

  return data;
}

function renderEnded(result, scenario) {
  const last = bestUnavailableOption(scenario);
  result.className = "last-train-primary ended";
  result.innerHTML = `
    <p class="last-train-kicker">LAST TRAIN ENDED</p>
    <p class="last-train-deadline">今日の終電は終了しました</p>
    ${last ? `<div class="last-train-route-summary">${last.originName}の最終 ${last.lastDeparture}</div>` : ""}
    <div class="last-train-actions">
      <button class="last-train-action-button" id="lastTrainRefreshButton" type="button">現在地を更新</button>
      <a class="last-train-action-link" href="/">タクシーも含めて帰り方を見る</a>
    </div>
  `;
}

export function mountLastTrainPage() {
  ensureStyles();
  document.title = "今日の終電｜あと一杯ナビ";

  const shell = document.querySelector("main.shell");
  const sourceSelect = document.getElementById("destinationCode");
  const stationOptions = sourceSelect?.innerHTML || "";

  if (!shell) {
    throw new Error("main shell not found");
  }

  let storedDestination = null;
  try {
    storedDestination = loadDestinationStation();
  } catch {
    storedDestination = null;
  }

  shell.classList.add("last-train-shell");
  shell.innerHTML = `
    <header class="hero last-train-hero">
      <div class="last-train-nav">
        <a class="last-train-back" href="/">← あと一杯ナビ</a>
        <span id="lastTrainClock" class="clock">--:--</span>
      </div>
      <div class="eyebrow">NAGOYA LAST TRAIN</div>
      <h1>今日の終電</h1>
      <p class="lead">入力を繰り返さず、今いる場所から帰れる最後の時間だけ確認。</p>
    </header>

    <section class="panel">
      <details id="lastTrainDestinationSettings" ${storedDestination ? "" : "open"}>
        <summary>帰宅先：<strong id="lastTrainDestinationName">最寄り駅</strong>（変更）</summary>
        <label class="field last-train-destination">
          <span>帰宅先の最寄り駅</span>
          <select id="lastTrainDestinationCode">${stationOptions}</select>
        </label>
        <label class="field">
          <span>ダイヤ区分</span>
          <select id="lastTrainDayType">
            <option value="weekday">平日</option>
            <option value="saturday_holiday">土休日</option>
          </select>
        </label>
        <p id="lastTrainDayTypeStatus" class="hint"></p>
      </details>

      <div id="lastTrainResult" class="last-train-primary">
        <p class="last-train-kicker">LAST TRAIN</p>
        <p class="last-train-deadline">現在地から終電を確認します</p>
      </div>

      <div class="last-train-actions">
        <button id="lastTrainCheckButton" class="primary" type="button">現在地から終電を確認</button>
      </div>
      <p id="lastTrainStatus" class="last-train-status" aria-live="polite"></p>
      <p class="last-train-note">終電時刻は公式時刻表をもとに検証した内部データを使用しています。現在地から乗車駅までの徒歩時間を含めて判定します。</p>
    </section>
  `;

  const destinationCode = document.getElementById("lastTrainDestinationCode");
  const destinationName = document.getElementById("lastTrainDestinationName");
  const destinationSettings = document.getElementById("lastTrainDestinationSettings");
  const dayType = document.getElementById("lastTrainDayType");
  const dayTypeStatus = document.getElementById("lastTrainDayTypeStatus");
  const result = document.getElementById("lastTrainResult");
  const checkButton = document.getElementById("lastTrainCheckButton");
  const status = document.getElementById("lastTrainStatus");
  const clockEl = document.getElementById("lastTrainClock");

  if (storedDestination) {
    destinationCode.value = storedDestination;
  }

  function updateDestinationName() {
    destinationName.textContent =
      destinationCode.selectedOptions?.[0]?.dataset?.name || "最寄り駅";
  }

  function updateClock() {
    clockEl.textContent = clock(new Date());
  }

  async function runCheck({ refreshLocation = false } = {}) {
    if (state.checking) return;
    state.checking = true;
    checkButton.disabled = true;
    status.textContent = "現在地を確認しています…";

    try {
      if (!state.origin || refreshLocation) {
        state.origin = await getLocation();
      }

      const resolvedDayType = currentDayType(dayType, dayTypeStatus);
      status.textContent = "利用できる駅への徒歩と終電を確認しています…";

      const data = await fetchBoundary({
        origin: state.origin,
        destinationCode: destinationCode.value,
        dayType: resolvedDayType
      });

      const scenario = data.scenarios?.[0];
      if (!data.routeFound || !scenario) {
        throw new Error("利用できる乗車駅への経路を確認できませんでした");
      }

      const name = data.destination?.name || destinationName.textContent;
      if (scenario.canReachDestination) {
        renderAvailable(result, data, scenario, name);
      } else {
        renderEnded(result, scenario);
      }

      document.getElementById("lastTrainRefreshButton")
        ?.addEventListener("click", () => runCheck({ refreshLocation: true }));

      status.textContent = `${clock(new Date())} 時点で確認`;
    } catch (error) {
      result.className = "last-train-primary";
      result.innerHTML = `
        <p class="last-train-kicker">LOCATION REQUIRED</p>
        <p class="last-train-deadline">正確な終電期限を表示できません</p>
        <div class="last-train-route-summary">${error?.message || "現在地を取得できませんでした"}</div>
      `;
      status.textContent = "位置情報を確認して、もう一度お試しください";
    } finally {
      state.checking = false;
      checkButton.disabled = false;
    }
  }

  destinationCode.addEventListener("change", () => {
    updateDestinationName();
    try {
      saveDestinationStation(destinationCode.value);
      storedDestination = destinationCode.value;
      destinationSettings.open = false;
    } catch {
      // 保存できなくても選択値で確認を続ける。
    }
    runCheck();
  });

  dayType.addEventListener("change", () => runCheck());
  checkButton.addEventListener("click", () => runCheck({ refreshLocation: true }));

  updateDestinationName();
  currentDayType(dayType, dayTypeStatus);
  updateClock();
  setInterval(updateClock, 30000);

  if (storedDestination) {
    runCheck();
  } else {
    status.textContent = "帰宅先の最寄り駅を一度選ぶと、次回から自動で確認できます";
  }
}
