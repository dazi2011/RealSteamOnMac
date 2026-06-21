(async () => {
  const appid = 2358720;
  if (appid !== 2358720) {
    throw new Error("refusing to inspect another AppID");
  }

  const before = await SteamClient.Installs.GetInstallManagerInfo();
  let openResult = null;
  let planned = null;
  let cancelResult = null;
  let cancelled = false;
  try {
    await SteamClient.Console.ExecCommand(
      "@sSteamCmdForcePlatformType windows",
    );
    openResult = await SteamClient.Installs.OpenInstallWizard([appid]);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    planned = await SteamClient.Installs.GetInstallManagerInfo();
    if (planned.currentAppID === appid) {
      cancelResult = await SteamClient.Installs.CancelInstall();
      cancelled = true;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  } finally {
    await SteamClient.Console.ExecCommand(
      "@sSteamCmdForcePlatformType macos",
    );
  }
  const after = await SteamClient.Installs.GetInstallManagerInfo();

  return {
    appid,
    openResult: openResult ?? null,
    before: JSON.parse(JSON.stringify(before)),
    planned: JSON.parse(JSON.stringify(planned)),
    cancelled,
    cancelResult: cancelResult ?? null,
    after: JSON.parse(JSON.stringify(after)),
  };
})()
