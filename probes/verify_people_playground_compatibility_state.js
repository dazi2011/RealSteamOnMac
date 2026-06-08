(async () => {
  const appid = 1118200;
  const expectedTool = "realsteamonmac-experimental";
  const storageKey = "__REALSTEAMONMAC_COMPAT_SELECTIONS_V1__";
  const details =
    appDetailsStore?.m_mapAppData?.get?.(appid)?.details ??
    (await appDetailsStore?.GetAppDetails?.(appid)) ??
    null;

  return {
    appid,
    expectedTool,
    configuredTool:
      globalThis.__REALSTEAMONMAC_CONFIG__?.compatTools?.[String(appid)] ??
      null,
    storedTool: JSON.parse(localStorage.getItem(storageKey) ?? "{}")[
      String(appid)
    ] ?? null,
    availableTools: JSON.parse(
      JSON.stringify(
        await SteamClient.Apps.GetAvailableCompatTools(appid),
      ),
    ),
    details: details
      ? {
          toolName: details.strCompatToolName,
          displayName: details.strCompatToolDisplayName,
          priority: details.nCompatToolPriority,
          displayStatus: details.eDisplayStatus,
        }
      : null,
    patchStatus: globalThis.__REALSTEAMONMAC_UI_STATUS__ ?? null,
  };
})()
