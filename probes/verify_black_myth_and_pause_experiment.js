(async () => {
  const appid = 2358720;
  if (appid !== 2358720) {
    throw new Error("refusing to verify another AppID");
  }

  const overview =
    globalThis.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
  const selected =
    overview?.GetPerClientData?.("selected") ??
    overview?.selected_per_client_data ??
    null;
  const clientid =
    overview?.selected_clientid ?? selected?.clientid ?? "0";
  let beforeActions = [];
  let verifyResult = null;
  let verifyError = null;
  let activeActions = [];
  let pauseResult = null;
  let pauseError = null;
  try {
    beforeActions = await SteamClient.Apps.GetActiveGameActions();
    verifyResult = await SteamClient.Apps.VerifyApp(appid);
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      activeActions = await SteamClient.Apps.GetActiveGameActions();
      if (activeActions.length !== 0) {
        break;
      }
    }
  } catch (error) {
    verifyError = String(error);
  } finally {
    try {
      pauseResult = await SteamClient.Downloads.PauseAppUpdate(
        appid,
        clientid,
      );
    } catch (error) {
      pauseError = String(error);
    }
  }
  await new Promise((resolve) => setTimeout(resolve, 500));

  return {
    appid,
    clientid: String(clientid),
    beforeActions: JSON.parse(JSON.stringify(beforeActions)),
    verifyResult: JSON.parse(JSON.stringify(verifyResult ?? null)),
    verifyError,
    activeActions: JSON.parse(JSON.stringify(activeActions)),
    pauseResult: JSON.parse(JSON.stringify(pauseResult ?? null)),
    pauseError,
    afterActions: JSON.parse(
      JSON.stringify(await SteamClient.Apps.GetActiveGameActions()),
    ),
  };
})()
