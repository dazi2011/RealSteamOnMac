(async () => {
  const appid = 1118200;
  const expectedTool = "realsteamonmac-dxmt";
  const storageKey = "__REALSTEAMONMAC_COMPAT_SELECTIONS_V1__";
  const controlStorageKey = "__REALSTEAMONMAC_CONTROL_CONFIGS_V1__";
  const projectToolNames = [
    "realsteamonmac-gptk",
    "realsteamonmac-dxmt",
    "realsteamonmac-dxvk",
    "realsteamonmac-wined3d",
  ];
  const details =
    appDetailsStore?.m_mapAppData?.get?.(appid)?.details ??
    (await appDetailsStore?.GetAppDetails?.(appid)) ??
    null;
  const availableTools = JSON.parse(
    JSON.stringify(
      await SteamClient.Apps.GetAvailableCompatTools(appid),
    ),
  );
  const propertiesDocument = (
    globalThis.g_FriendsUIApp?.m_IdleTracker?.m_rgWindows ?? []
  )
    .map((windowObject) => windowObject?.document)
    .find((documentObject) => documentObject?.title === "People Playground");
  const controlPanel = propertiesDocument?.querySelector?.(
    ".realsteamonmac-controls",
  );

  return {
    appid,
    expectedTool,
    configuredTool:
      globalThis.__REALSTEAMONMAC_CONFIG__?.defaultCompatTool ??
      null,
    storedTool: JSON.parse(localStorage.getItem(storageKey) ?? "{}")[
      String(appid)
    ] ?? null,
    storedControl:
      JSON.parse(localStorage.getItem(controlStorageKey) ?? "{}")[
        String(appid)
      ] ?? null,
    availableTools,
    allProjectToolsAvailable: projectToolNames.every((toolName) =>
      availableTools.some((tool) => tool?.strToolName === toolName),
    ),
    controlPanel: controlPanel
      ? {
          appid: controlPanel.dataset.appid ?? null,
          renderer:
            controlPanel.querySelector(
              ".realsteamonmac-controls__renderer",
            )?.textContent?.trim() ?? null,
          status:
            controlPanel.querySelector(
              ".realsteamonmac-controls__status",
            )?.textContent?.trim() ?? null,
          controls: Array.from(
            controlPanel.querySelectorAll("input[data-control]"),
          ).map((input) => ({
            key: input.dataset.control,
            checked: input.checked,
            disabled: input.disabled,
          })),
        }
      : null,
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
