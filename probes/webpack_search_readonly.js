(() => {
  const terms = [
    "eDisplayStatus",
    "nCompatToolPriority",
    "strCompatToolName",
    "bCompatEnabledForOtherTitles",
    "bCompatEnabled",
    "InvalidPlatform",
    "eAppError",
    "OpenInstallWizard",
    "PerformAppAction",
  ];
  const chunks = globalThis.webpackChunksteamui;
  if (!Array.isArray(chunks)) {
    return { error: "webpackChunksteamui is unavailable" };
  }

  let webpackRequire = null;
  const marker = `realsteamonmac-${Date.now()}-${Math.random()}`;
  chunks.push([
    [marker],
    {},
    (runtimeRequire) => {
      webpackRequire = runtimeRequire;
    },
  ]);

  if (!webpackRequire?.m) {
    return { error: "Steam webpack runtime was not captured" };
  }

  const matches = [];
  for (const [moduleID, factory] of Object.entries(webpackRequire.m)) {
    const source = Function.prototype.toString.call(factory);
    const matchedTerms = terms.filter((term) => source.includes(term));
    if (matchedTerms.length === 0) continue;

    const snippets = {};
    for (const term of matchedTerms) {
      const offset = source.indexOf(term);
      snippets[term] = source.slice(
        Math.max(0, offset - 2500),
        Math.min(source.length, offset + 5000),
      );
    }
    matches.push({
      moduleID,
      sourceLength: source.length,
      matchedTerms,
      snippets,
    });
  }

  return {
    moduleCount: Object.keys(webpackRequire.m).length,
    matchCount: matches.length,
    matches,
  };
})()
