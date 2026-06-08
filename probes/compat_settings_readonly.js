(() => {
  const chunks = globalThis.webpackChunksteamui;
  if (!Array.isArray(chunks)) {
    return { error: "webpackChunksteamui is unavailable" };
  }

  let webpackRequire = null;
  chunks.push([
    [`realsteamonmac-compat-settings-${Date.now()}-${Math.random()}`],
    {},
    (runtimeRequire) => {
      webpackRequire = runtimeRequire;
    },
  ]);

  const module = webpackRequire(33867);
  const store = module.rV;
  return {
    moduleExports: Object.keys(module).sort(),
    storeKeys: store ? Object.keys(store).sort() : [],
    settings: store?.settings
      ? JSON.parse(JSON.stringify(store.settings))
      : null,
  };
})()
