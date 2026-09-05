export function prepareDestinationSelect(documentRef = document) {
  const select = documentRef.getElementById("destinationCode");
  if (!select) return;

  let placeholder = Array.from(select.options || []).find(
    (option) => option.value === ""
  );

  if (!placeholder) {
    placeholder = documentRef.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "選択してください";
    placeholder.disabled = true;
    select.insertBefore(placeholder, select.firstChild);
  }

  placeholder.selected = true;
  select.value = "";

  const routeBadge = documentRef.getElementById("routeBadge");
  if (routeBadge) {
    routeBadge.textContent = "深夜帰宅判定 → 最寄り駅";
  }

  const checkButton = documentRef.getElementById("checkButton");
  const status = documentRef.getElementById("status");

  checkButton?.addEventListener(
    "click",
    (event) => {
      if (select.value) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      if (status) {
        status.textContent = "帰宅先の最寄り駅を選択してください";
      }
      select.focus?.();
    },
    true
  );
}
