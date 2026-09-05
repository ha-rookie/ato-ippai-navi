function collapseSupportedRoutes() {
  const destinationCode = document.getElementById("destinationCode");
  const destinationField = destinationCode?.closest("label.field");
  const supportHint = destinationField?.nextElementSibling;

  if (!supportHint?.classList.contains("hint")) return;
  if (document.getElementById("supportedRoutesDetails")) return;

  const original = supportHint.textContent.trim();
  const routeScope = original
    .replace(/^最寄り駅はこの端末だけに保存します。/, "")
    .replace(/自宅住所は登録しません。$/, "")
    .trim();

  supportHint.textContent =
    "最寄り駅はこの端末だけに保存します。自宅住所は登録しません。";

  const details = document.createElement("details");
  details.id = "supportedRoutesDetails";
  details.className = "support-scope-details";

  const summary = document.createElement("summary");
  summary.textContent = "対応エリア・路線を確認";

  const body = document.createElement("p");
  body.className = "hint";
  body.textContent = routeScope || original;

  details.append(summary, body);
  supportHint.after(details);
}

function clarifyDayTypeHint() {
  const dayType = document.getElementById("dayType");
  const dayTypeField = dayType?.closest("label.field");
  const hint = dayTypeField?.nextElementSibling;

  if (!hint?.classList.contains("hint")) return;
  hint.textContent =
    "曜日・祝日は自動判定します。必要な場合は手動で変更できます。";
}

export function clarifyMainPageInformation() {
  const lead = document.querySelector("header.hero .lead");
  if (lead) {
    lead.innerHTML =
      "このアプリで分かること：<br>あと何分飲める？ ／ 今日の終電 ／ 帰ったら何時間寝られる？";
  }

  const decisionTitle = document.getElementById("decision-title");
  if (decisionTitle) {
    decisionTitle.textContent = "あと何分飲める？を判定";
  }

  collapseSupportedRoutes();
  clarifyDayTypeHint();
}

export function clarifyLastTrainInformation() {
  const lead = document.querySelector("header.last-train-hero .lead");
  if (lead) {
    lead.textContent =
      "今いる場所から、何時までに出れば最寄り駅まで終電で帰れるかを確認します。";
  }

  const result = document.getElementById("lastTrainResult");
  const initialDeadline = result?.querySelector(".last-train-deadline");
  if (initialDeadline?.textContent.trim() === "現在地から終電を確認します") {
    initialDeadline.textContent = "ここを出る期限を現在地から計算します";
  }

  const checkButton = document.getElementById("lastTrainCheckButton");
  if (checkButton) {
    checkButton.textContent = "ここを出る期限を確認";
  }
}
