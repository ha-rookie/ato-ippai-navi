function ensureStyles() {
  if (document.querySelector('link[href="/last-train-link.css"]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/last-train-link.css";
  document.head.appendChild(link);
}

export function mountLastTrainQuickLink() {
  const hero = document.querySelector(".hero");
  if (!hero || document.getElementById("lastTrainQuickLink")) return;

  ensureStyles();

  hero.insertAdjacentHTML(
    "afterend",
    `
      <a id="lastTrainQuickLink" class="last-train-quick-link" href="/last-train">
        <span class="last-train-quick-icon" aria-hidden="true">🚃</span>
        <span class="last-train-quick-copy">
          <span class="last-train-quick-title">今日の終電</span>
          <span class="last-train-quick-subtitle">最寄り駅までの「ここを出る期限」だけ確認</span>
        </span>
        <span class="last-train-quick-arrow" aria-hidden="true">→</span>
      </a>
    `
  );
}
