(async () => {
  const appid = 1118200;
  const overview = globalThis.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
  const detailsResult =
    globalThis.appDetailsStore?.GetAppDetails?.(appid) ?? null;
  const details =
    detailsResult && typeof detailsResult.then === "function"
      ? await detailsResult
      : detailsResult;
  const selected =
    overview?.GetPerClientData?.("selected") ??
    overview?.selected_per_client_data ??
    overview?.per_client_data?.find(
      (entry) => entry.clientid === overview.selected_clientid,
    ) ??
    null;

  return {
    appid,
    overviewFound: Boolean(overview),
    overviewKeys: overview ? Object.keys(overview).sort() : [],
    selected,
    detailsFound: Boolean(details),
    details:
      details && typeof details === "object"
        ? Object.fromEntries(
            Object.entries(details).filter(([key, value]) =>
              /DisplayStatus|LocalContent|CompatTool|AppID|DiskSpace/.test(key) &&
              ["string", "number", "boolean"].includes(typeof value),
            ),
          )
        : details,
    mapAppDataEntry:
      globalThis.appDetailsStore?.m_mapAppData?.get?.(appid) ?? null,
  };
})()
