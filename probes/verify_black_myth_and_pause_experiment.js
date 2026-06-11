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
  let beforeAction = null;
  let verifyResult = null;
  let verifyError = null;
  let plannedAction = null;
  let pauseResult = null;
  let pauseError = null;
  try {
    beforeAction = await SteamClient.Apps.GetGameActionForApp(appid);
    verifyResult = await SteamClient.Apps.VerifyApp(appid);
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      plannedAction =
        await SteamClient.Apps.GetGameActionForApp(appid);
      if (plannedAction) {
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
    beforeAction: JSON.parse(JSON.stringify(beforeAction ?? null)),
    verifyResult: JSON.parse(JSON.stringify(verifyResult ?? null)),
    verifyError,
    plannedAction: JSON.parse(JSON.stringify(plannedAction ?? null)),
    pauseResult: JSON.parse(JSON.stringify(pauseResult ?? null)),
    pauseError,
    afterAction: JSON.parse(
      JSON.stringify(
        (await SteamClient.Apps.GetGameActionForApp(appid)) ?? null,
      ),
    ),
  };
})()
