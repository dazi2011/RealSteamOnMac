(() => {
  const appid = 1118200;
  const panel = document.querySelector(".realsteamonmac-controls");
  if (Number(panel?.dataset.appid) !== appid) {
    throw new Error(
      `People Playground panel AppID mismatch: ${panel?.dataset.appid}`,
    );
  }
  const status = panel.querySelector(".realsteamonmac-action-status");
  if (!status) {
    throw new Error("People Playground action status is unavailable");
  }
  status.scrollIntoView({ block: "center", inline: "nearest" });
  return {
    appid,
    state: status.dataset.state ?? null,
    text: status.textContent?.replace(/\s+/g, " ").trim() ?? "",
  };
})()
