(async () => {
  const appid = 1118200;
  const overview = globalThis.appStore?.GetAppOverviewByAppID?.(appid);
  const detailsResult = globalThis.appDetailsStore?.GetAppDetails?.(appid);
  const details =
    detailsResult && typeof detailsResult.then === "function"
      ? await detailsResult
      : detailsResult;
  const selected =
    overview?.GetPerClientData?.("selected") ??
    overview?.selected_per_client_data ??
    overview?.per_client_data?.find(
      (entry) => entry.clientid === overview.selected_clientid,
    );
  if (!overview || !details || !selected) {
    throw new Error("People Playground shared store state is unavailable");
  }
  if (details.eDisplayStatus !== 9) {
    throw new Error(
      `backend is not ready for reconciliation: ${details.eDisplayStatus}`,
    );
  }

  const normalizedBefore =
    globalThis.__REALSTEAMONMAC_UI_STATUS__?.normalized ?? null;
  selected.display_status = 14;
  selected.is_available_on_current_platform = false;
  selected.is_invalid_os_type = true;
  await new Promise((resolve) => setTimeout(resolve, 1500));

  return {
    appid,
    detailsStatus: details.eDisplayStatus,
    selectedStatus: selected.display_status,
    isAvailableOnCurrentPlatform:
      selected.is_available_on_current_platform,
    isInvalidOsType: selected.is_invalid_os_type,
    normalizedBefore,
    normalizedAfter:
      globalThis.__REALSTEAMONMAC_UI_STATUS__?.normalized ?? null,
    patchError:
      globalThis.__REALSTEAMONMAC_UI_STATUS__?.lastError ?? null,
  };
})()
