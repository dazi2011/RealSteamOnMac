(async () => {
  const appid = 1118200;
  const expectedDependencyIds = [
    "vcrun2022-x86",
    "vcrun2022",
    "vcrun2013-x86",
    "vcrun2013",
    "vcrun2012-x86",
    "vcrun2012",
    "vcrun2010-x86",
    "vcrun2010",
    "vcrun2008-x86",
    "vcrun2008",
    "dotnet48",
    "directx-jun2010",
    "xna40",
    "physx-legacy",
  ];
  const projectToolNames = [
    "realsteamonmac-gptk",
    "realsteamonmac-dxmt",
    "realsteamonmac-dxvk",
    "realsteamonmac-wined3d",
  ];

  const findFiber = (element) => {
    const fiberKey = Object.getOwnPropertyNames(element ?? {}).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    return fiberKey ? element[fiberKey] : null;
  };

  const readDropDownState = (element) => {
    let fiber = findFiber(element);
    for (let depth = 0; fiber && depth < 24; depth += 1) {
      const props = fiber.memoizedProps ?? fiber.pendingProps;
      if (Array.isArray(props?.rgOptions)) {
        return {
          selectedOption: props.selectedOption ?? null,
          options: props.rgOptions.map((option) => ({
            data: option.data,
            label: option.label,
          })),
        };
      }
      fiber = fiber.return;
    }
    return null;
  };

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
  const comboboxes = Array.from(
    propertiesDocument?.querySelectorAll?.("[role=combobox]") ?? [],
  );
  const dependencyDropDown = readDropDownState(comboboxes[1]);
  const dependencyIds =
    dependencyDropDown?.options.map((option) => option.data) ?? [];

  return {
    appid,
    availableTools,
    allProjectToolsAvailable: projectToolNames.every((toolName) =>
      availableTools.some((tool) => tool?.strToolName === toolName),
    ),
    dependencyDropDown,
    expectedDependencyIds,
    allDependenciesAvailable:
      JSON.stringify(dependencyIds) ===
      JSON.stringify(expectedDependencyIds),
    nativeComboboxCount: comboboxes.length,
    allComboboxesUseSteamControls: comboboxes.every((element) =>
      element.classList.contains("DialogDropDown"),
    ),
    legacyControlPanelCount:
      propertiesDocument?.querySelectorAll?.(
        ".realsteamonmac-controls",
      ).length ?? 0,
    legacyModalLayerCount:
      propertiesDocument?.querySelectorAll?.(
        ".realsteamonmac-modal-layer",
      ).length ?? 0,
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
