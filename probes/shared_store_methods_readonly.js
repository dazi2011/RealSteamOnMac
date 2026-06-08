(() => {
  const source = (value) =>
    typeof value === "function"
      ? Function.prototype.toString.call(value).slice(0, 6000)
      : null;
  return {
    updateAppOverview: source(globalThis.appStore?.UpdateAppOverview),
    getAppOverviewByAppID: source(
      globalThis.appStore?.GetAppOverviewByAppID,
    ),
    appDetailsChanged: source(
      globalThis.appDetailsStore?.AppDetailsChanged,
    ),
    registerForAppData: source(
      globalThis.appDetailsStore?.RegisterForAppData,
    ),
  };
})()
