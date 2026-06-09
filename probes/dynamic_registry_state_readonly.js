(async () => {
  const status = globalThis.__REALSTEAMONMAC_UI_STATUS__ ?? null;
  const appids = Array.isArray(status?.appids) ? status.appids : [];
  const projectToolNames = [
    "realsteamonmac-gptk",
    "realsteamonmac-dxmt",
    "realsteamonmac-dxvk",
    "realsteamonmac-wined3d",
  ];

  const loadDetails = async (appid) => {
    let result =
      appDetailsStore?.GetAppDetails?.(appid) ??
      appDetailsStore?.m_mapAppData?.get?.(appid)?.details ??
      null;
    if (result && typeof result.then === "function") {
      result = await result;
    }
    if (!result) {
      result = await appDetailsStore?.RequestAppDetails?.(appid);
    }
    return result?.details ?? result ?? null;
  };

  const selectedData = (overview) =>
    overview?.GetPerClientData?.("selected") ??
    overview?.selected_per_client_data ??
    overview?.per_client_data?.find?.(
      (entry) => entry.clientid === overview.selected_clientid,
    ) ??
    null;

  const rows = [];
  for (const appid of appids) {
    const overview = appStore?.GetAppOverviewByAppID?.(appid) ?? null;
    const details = await loadDetails(appid);
    const selected = selectedData(overview);
    const tools = JSON.parse(
      JSON.stringify(
        await SteamClient.Apps.GetAvailableCompatTools(appid),
      ),
    );
    rows.push({
      appid,
      name:
        overview?.display_name ??
        overview?.strDisplayName ??
        details?.strDisplayName ??
        null,
      platforms: details?.vecPlatforms
        ? Array.from(details.vecPlatforms)
        : null,
      overviewStatus: selected?.display_status ?? null,
      detailsStatus: details?.eDisplayStatus ?? null,
      hasAnyLocalContent: details?.bHasAnyLocalContent ?? null,
      isAvailableOnCurrentPlatform:
        selected?.is_available_on_current_platform ?? null,
      isInvalidOsType: selected?.is_invalid_os_type ?? null,
      compatToolName: details?.strCompatToolName ?? null,
      compatToolDisplayName: details?.strCompatToolDisplayName ?? null,
      compatToolPriority: details?.nCompatToolPriority ?? null,
      projectToolsAvailable: projectToolNames.every((toolName) =>
        tools.some((tool) => tool?.strToolName === toolName),
      ),
      projectToolNames: tools
        .map((tool) => tool?.strToolName)
        .filter((toolName) => projectToolNames.includes(toolName)),
      managedPredicate:
        globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__?.(appid) ?? false,
    });
  }

  const excludedAppid = 4000;
  const excludedOverview =
    appStore?.GetAppOverviewByAppID?.(excludedAppid) ?? null;
  const excludedDetails = await loadDetails(excludedAppid);
  const excludedSelected = selectedData(excludedOverview);

  return {
    status,
    summary: {
      managedCount: rows.length,
      predicateTrueCount: rows.filter((row) => row.managedPredicate).length,
      backendReadyCount: rows.filter(
        (row) => row.detailsStatus === 9 || row.detailsStatus === 11,
      ).length,
      overviewReadyCount: rows.filter(
        (row) => row.overviewStatus === 9 || row.overviewStatus === 11,
      ).length,
      nativeStatusSyncedCount: rows.filter(
        (row) =>
          Number.isSafeInteger(row.detailsStatus) &&
          row.detailsStatus !== 14 &&
          row.overviewStatus === row.detailsStatus,
      ).length,
      invalidPlatformDetailsCount: rows.filter(
        (row) => row.detailsStatus === 14,
      ).length,
      invalidPlatformOverviewCount: rows.filter(
        (row) => row.overviewStatus === 14,
      ).length,
      projectToolAvailableCount: rows.filter(
        (row) => row.projectToolsAvailable,
      ).length,
      windowsOnlyCount: rows.filter(
        (row) =>
          Array.isArray(row.platforms) &&
          row.platforms.includes("windows") &&
          !row.platforms.includes("osx"),
      ).length,
      installedReadyCount: rows.filter(
        (row) =>
          row.hasAnyLocalContent === true &&
          row.detailsStatus === 11 &&
          row.overviewStatus === 11,
      ).length,
      uninstalledReadyCount: rows.filter(
        (row) =>
          row.hasAnyLocalContent === false &&
          row.detailsStatus === 9 &&
          row.overviewStatus === 9,
      ).length,
    },
    excludedControl: {
      appid: excludedAppid,
      name:
        excludedOverview?.display_name ??
        excludedOverview?.strDisplayName ??
        excludedDetails?.strDisplayName ??
        null,
      platforms: excludedDetails?.vecPlatforms
        ? Array.from(excludedDetails.vecPlatforms)
        : null,
      overviewStatus: excludedSelected?.display_status ?? null,
      detailsStatus: excludedDetails?.eDisplayStatus ?? null,
      managedPredicate:
        globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__?.(
          excludedAppid,
        ) ?? false,
    },
    rows,
  };
})()
