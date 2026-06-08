(() => {
  const chunks = globalThis.webpackChunksteamui;
  if (!Array.isArray(chunks)) {
    return { error: "webpackChunksteamui is unavailable" };
  }

  let webpackRequire = null;
  chunks.push([
    [`realsteamonmac-install-enums-${Date.now()}-${Math.random()}`],
    {},
    (runtimeRequire) => {
      webpackRequire = runtimeRequire;
    },
  ]);

  const exports = webpackRequire(44846);
  const localization = webpackRequire(46108);
  const numericMatches = {};
  for (const [exportName, value] of Object.entries(exports)) {
    if (!value || typeof value !== "object") continue;
    const entries = Object.entries(value).filter(
      ([, item]) => item === 15 || item === 29,
    );
    if (entries.length > 0) {
      numericMatches[exportName] = Object.fromEntries(entries);
    }
  }

  return {
    installManagerStates: exports.H24 ?? null,
    topLevelNumericMatches: Object.fromEntries(
      Object.entries(exports).filter(([, value]) => value === 15 || value === 29),
    ),
    numericMatches,
    appError29Text:
      typeof localization.we === "function"
        ? localization.we("#Steam_AppUpdateError_29")
        : null,
  };
})()
