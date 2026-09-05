const normalizedPath = window.location.pathname.replace(/\/+$/, "") || "/";

if (normalizedPath === "/last-train") {
  const { mountLastTrainPage } = await import("/js/last-train-page.js");
  const { clarifyLastTrainInformation } = await import("/js/information-architecture.js");
  mountLastTrainPage();
  clarifyLastTrainInformation();
} else {
  await import("/js/main-page.js");
  const { mountLastTrainQuickLink } = await import("/js/last-train-link.js");
  const { clarifyMainPageInformation } = await import("/js/information-architecture.js");
  mountLastTrainQuickLink();
  clarifyMainPageInformation();
}
