import {
  enrichTonightDecisionWithSleep
} from "/js/sleep.js";
import {
  clearSleepSettings,
  loadDestinationStation,
  loadSleepSettings,
  saveDestinationStation,
  saveSleepSettings
} from "/js/settings.js";

const $ = (id) => document.getElementById(id);

const els = {
  clock: $("clock"),
  routeBadge: $("routeBadge"),
  destinationCode: $("destinationCode"),
  dayType: $("dayType"),
  checkButton: $("checkButton"),
  status: $("status"),
  resultsSection: $("resultsSection"),
  results: $("results"),
  taxiNote: $("taxiNote"),
  stationToHomeLabel: $("stationToHomeLabel"),
  stationToHomeMinutes: $("stationToHomeMinutes"),
  bedtimePrepMinutes: $("bedtimePrepMinutes"),
  wakeTime: $("wakeTime"),
  saveSettingsButton: $("saveSettingsButton"),
  clearSettingsButton: $("clearSettingsButton"),
  settingsStatus: $("settingsStatus")
};

const offsetLabels = new Map([
  [0, "今出る"],
  [15, "あと15分"],
  [30, "あと30分"],
  [60, "あと60分"]
]);

function yen(value) {
  if (!Number.isFinite(Number(value))) return "—";
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0
  }).format(Number(value));
}

function autoDayType() {
  const day = new Date().getDay();
  return day === 0 || day === 6
    ? "saturday_holiday"
    : "weekday";
}

function updateClock() {
  els.clock.textContent = new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23"
  }).format(new Date());
}

function selectedDestinationName() {
  return (
    els.destinationCode.selectedOptions?.[0]?.dataset?.name ||
    "最寄り駅"
  );
}

function updateDestinationUi() {
  const name = selectedDestinationName();
  els.routeBadge.textContent = `PoC：栄・伏見 → ${name}`;
  els.stationToHomeLabel.textContent = `${name}駅 → 自宅`;
}

function populateDestinationStation() {
  try {
    const stored = loadDestinationStation();
    if (stored) {
      els.destinationCode.value = stored;
    }
  } catch {
    // localStorageが使えない場合は既定値H22のまま続行する。
  }

  updateDestinationUi();
}


function currentSleepSettingsOrNull() {
  try {
    return loadSleepSettings();
  } catch {
    return null;
  }
}

function populateSettings() {
  const settings = currentSleepSettingsOrNull();
  if (!settings) return;

  els.stationToHomeMinutes.value = settings.stationToHomeMinutes;
  els.bedtimePrepMinutes.value = settings.bedtimePrepMinutes;
  els.wakeTime.value = settings.wakeTime;
  els.settingsStatus.textContent = "この端末に保存済み";
}

function formSettings() {
  const stationToHomeMinutes = els.stationToHomeMinutes.value;
  const bedtimePrepMinutes = els.bedtimePrepMinutes.value;
  const wakeTime = els.wakeTime.value;

  if (
    stationToHomeMinutes === "" ||
    bedtimePrepMinutes === "" ||
    wakeTime === ""
  ) {
    return null;
  }

  return {
    stationToHomeMinutes,
    bedtimePrepMinutes,
    wakeTime
  };
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

async function fetchDecision(origin) {
  const response = await fetch("/api/tonight-decision", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      origin,
      departureTime: new Date().toISOString(),
      dayType: els.dayType.value,
      destinationCode: els.destinationCode.value,
      offsetMinutes: [0, 15, 30, 60],
      stationBufferMinutes: 3,
      minimumBoardingLeadMinutes: 1,
      includeDispatchFee: true
    })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "判定APIでエラーが発生しました");
  }

  return data;
}

function sleepHtml(scenario) {
  if (
    scenario.recommendedMode === "train" &&
    !scenario.estimatedDestinationStationArrivalTime
  ) {
    return '<div class="sleep-line">睡眠時間：終電時刻のみのため未算出</div>';
  }

  if (!scenario.sleep) {
    return '<div class="sleep-line">睡眠時間：設定すると表示</div>';
  }

  return `
    <div class="sleep-line">
      就寝見込み ${scenario.sleep.localEstimatedBedtime}
      ／ <span class="sleep-value">${scenario.sleep.sleepLabel}</span> 睡眠
    </div>
  `;
}

function renderScenario(scenario, destinationName) {
  const label =
    offsetLabels.get(Number(scenario.offsetMinutes)) ||
    `+${scenario.offsetMinutes}分`;

  const isTrain = scenario.recommendedMode === "train";
  const isTaxi = scenario.recommendedMode === "taxi";
  const warning =
    isTrain &&
    Number.isFinite(Number(scenario.usableMarginMinutes)) &&
    Number(scenario.usableMarginMinutes) <= 10;

  let main = "判定できません";
  let sub = "";
  let modeLabel = "未判定";
  let modeClass = "";

  if (isTrain) {
    modeLabel = warning ? "終電注意" : "電車";
    modeClass = "train";
    main = `${scenario.recommendedOriginName}から終電 ${scenario.lastDeparture} に間に合う`;
    sub = `
      ${scenario.recommendedOriginName}駅 ${scenario.localStationReadyTime}ごろ
      ／ 最終 ${scenario.lastDeparture}
    `;

    if (scenario.localLastTrainArrivalTime) {
      sub += `<br>最終列車は${destinationName} ${scenario.localLastTrainArrivalTime}着`;
    }

    if (Number.isFinite(Number(scenario.usableMarginMinutes))) {
      sub += `<br>終電までの余裕 約${Math.max(0, scenario.usableMarginMinutes)}分`;
    }
  } else if (isTaxi) {
    modeLabel = "タクシー";
    modeClass = "taxi";
    main = `終電後・約${yen(scenario.taxiEstimatedTotalYen)}`;
    sub = `${destinationName} ${scenario.localDestinationStationArrivalTime || "—"}ごろ着見込み`;
  }

  return `
    <article class="result-card ${warning ? "warning" : ""} ${isTaxi ? "taxi" : ""}">
      <div class="card-top">
        <div class="offset-label">${label}</div>
        <span class="mode ${modeClass}">${modeLabel}</span>
      </div>
      <div class="main-result">${main}</div>
      <div class="sub-result">${sub}</div>
      ${sleepHtml(scenario)}
    </article>
  `;
}

function render(data) {
  const settings = currentSleepSettingsOrNull();
  const displayData = settings
    ? enrichTonightDecisionWithSleep(data, settings)
    : data;

  const destinationName =
    data.train?.destination?.name || selectedDestinationName();

  els.results.innerHTML = displayData.scenarios
    .map((scenario) => renderScenario(scenario, destinationName))
    .join("");

  els.taxiNote.textContent = data.taxi?.estimatedTotalYen
    ? `終電後のタクシー参考概算：${destinationName}駅まで約${yen(data.taxi.estimatedTotalYen)}。距離制のみの参考値です。`
    : "";

  els.resultsSection.classList.remove("hidden");
}

async function runDecision() {
  els.checkButton.disabled = true;
  els.status.textContent = "現在地を確認しています…";

  try {
    const origin = await getLocation();
    els.status.textContent = "栄・伏見への徒歩と終電・タクシーを計算しています…";

    const data = await fetchDecision(origin);
    render(data);
    els.status.textContent = "判定しました";
  } catch (error) {
    els.status.textContent = error?.message || "判定できませんでした";
  } finally {
    els.checkButton.disabled = false;
  }
}

els.checkButton.addEventListener("click", runDecision);

els.destinationCode.addEventListener("change", () => {
  updateDestinationUi();

  try {
    saveDestinationStation(els.destinationCode.value);
  } catch {
    // 保存できなくても、その場の判定は選択値で続行する。
  }
});

els.saveSettingsButton.addEventListener("click", () => {
  const settings = formSettings();

  if (!settings) {
    els.settingsStatus.textContent = "3項目を入力してください";
    return;
  }

  try {
    saveSleepSettings(settings);
    els.settingsStatus.textContent = "この端末に保存しました";
  } catch (error) {
    els.settingsStatus.textContent = error?.message || "保存できませんでした";
  }
});

els.clearSettingsButton.addEventListener("click", () => {
  clearSleepSettings();
  els.stationToHomeMinutes.value = "";
  els.bedtimePrepMinutes.value = "";
  els.wakeTime.value = "";
  els.settingsStatus.textContent = "端末の設定を削除しました";
});

els.dayType.value = autoDayType();
populateDestinationStation();
populateSettings();
updateClock();
setInterval(updateClock, 30000);
