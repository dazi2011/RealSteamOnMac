(async () => {
  const appid = 1118200;
  if (appid !== 1118200) {
    throw new Error("refusing to cancel an install for another AppID");
  }

  const before = await SteamClient.Installs.GetInstallManagerInfo();
  if (before.currentAppID !== appid) {
    return {
      appid,
      cancelled: false,
      reason: "People Playground is not the active install",
      before: JSON.parse(JSON.stringify(before)),
    };
  }

  const cancelResult = await SteamClient.Installs.CancelInstall();
  await new Promise((resolve) => setTimeout(resolve, 500));
  const after = await SteamClient.Installs.GetInstallManagerInfo();

  return {
    appid,
    cancelled: true,
    cancelResult: cancelResult ?? null,
    before: JSON.parse(JSON.stringify(before)),
    after: JSON.parse(JSON.stringify(after)),
  };
})()
