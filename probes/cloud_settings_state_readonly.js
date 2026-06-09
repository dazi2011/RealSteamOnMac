(() => {
  const cloudSetting = "cloud_enabled";
  const screenshotSetting = "show_screenshot_manager";
  const chunks = globalThis.webpackChunksteamui;
  if (!Array.isArray(chunks)) {
    return { error: "webpackChunksteamui is unavailable" };
  }

  let webpackRequire = null;
  chunks.push([
    [`realsteamonmac-cloud-settings-${Date.now()}-${Math.random()}`],
    {},
    (runtimeRequire) => {
      webpackRequire = runtimeRequire;
    },
  ]);

  const schemaModule = webpackRequire(29788);
  const schemaFields = schemaModule.Ne?.M?.()?.fields ?? {};
  const settingsModule = webpackRequire(33867);
  const settingsStore = settingsModule.rV;
  const clientSettings = settingsStore?.m_ClientSettings ?? null;
  const cloudStorage = globalThis.SteamClient?.CloudStorage;

  const describeSetting = (name) => {
    const field = schemaFields[name];
    return {
      schema: field
        ? {
            number: field.n,
            defaultValue: field.d ?? null,
            repeated: field.r ?? false,
          }
        : null,
      presentInClientSettings: Object.prototype.hasOwnProperty.call(
        clientSettings ?? {},
        name,
      ),
      clientValue: clientSettings?.[name] ?? null,
    };
  };

  return {
    settingsModuleExports: Object.keys(settingsModule).sort(),
    settingsStoreKeys: settingsStore ? Object.keys(settingsStore).sort() : [],
    cloud: describeSetting(cloudSetting),
    screenshotManager: describeSetting(screenshotSetting),
    CloudStorage: cloudStorage
      ? {
          available: true,
          methods: Object.getOwnPropertyNames(cloudStorage)
            .filter((name) => typeof cloudStorage[name] === "function")
            .sort(),
        }
      : {
          available: false,
          methods: [],
        },
    matchingGlobalKeys: Object.getOwnPropertyNames(globalThis)
      .filter((name) => /cloudstorage/i.test(name))
      .sort(),
  };
})()
