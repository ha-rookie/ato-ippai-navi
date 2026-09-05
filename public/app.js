const normalizedPath = window.location.pathname.replace(/\/+$/, "") || "/";

if (normalizedPath === "/last-train") {
  const { mountLastTrainPage } = await import("/js/last-train-page.js");
  mountLastTrainPage();
} else {
  await import("/js/main-page.js");
  const { mountLastTrainQuickLink } = await import("/js/last-train-link.js");
  mountLastTrainQuickLink();
}
