(async () => {
  const appid = 2358720;
  if (appid !== 2358720) {
    throw new Error("refusing to uninstall another AppID");
  }

  const overview =
    globalThis.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
  const localClient = overview?.per_client_data?.find(
    (client) => String(client?.clientid) === "0",
  );
  if (!overview || String(overview.size_on_disk) !== "0") {
    throw new Error("refusing to uninstall a non-zero-size app");
  }
  if (!localClient?.installed) {
    throw new Error("refusing to uninstall an app not marked installed");
  }

  const installManager =
    await SteamClient.Installs.GetInstallManagerInfo();
  if (installManager?.currentAppID) {
    throw new Error("refusing while another install is active");
  }

  const activeAction =
    await SteamClient.Apps.GetGameActionForApp(appid);
  if (activeAction) {
    throw new Error("refusing while a game action is active");
  }

  const before = {
    sizeOnDisk: String(overview.size_on_disk),
    displayStatus: localClient.display_status,
    installed: localClient.installed,
  };
  const uninstallResult =
    await SteamClient.Installs.OpenUninstallWizard([appid], true);

  await new Promise((resolve) => setTimeout(resolve, 1500));
  const afterOverview =
    globalThis.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
  const afterLocalClient = afterOverview?.per_client_data?.find(
    (client) => String(client?.clientid) === "0",
  );

  return {
    appid,
    before,
    uninstallResult: uninstallResult ?? null,
    after: afterOverview
      ? {
          sizeOnDisk: String(afterOverview.size_on_disk),
          displayStatus: afterLocalClient?.display_status ?? null,
          installed: afterLocalClient?.installed ?? null,
        }
      : null,
  };
})()
