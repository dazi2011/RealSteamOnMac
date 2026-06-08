(async () => {
  const apps = globalThis.SteamClient?.Apps;
  const compat = globalThis.SteamClient?.Compat;
  const result = {
    location: globalThis.location?.href ?? null,
    platform:
      new URL(globalThis.location.href).searchParams.get("PLATFORM") ?? null,
    hasSteamClient: Boolean(globalThis.SteamClient),
    methods: {
      GetAvailableCompatTools:
        typeof apps?.GetAvailableCompatTools === "function",
      SpecifyCompatTool: typeof apps?.SpecifyCompatTool === "function",
      RunGame: typeof apps?.RunGame === "function",
      BIsCompatLayerEnabled:
        typeof compat?.BIsCompatLayerEnabled === "function",
    },
    appid: 1118200,
  };

  if (result.methods.BIsCompatLayerEnabled) {
    try {
      result.compatLayerEnabled = await compat.BIsCompatLayerEnabled();
    } catch (error) {
      result.compatLayerEnabledError = String(error?.stack ?? error);
    }
  }

  if (!result.methods.GetAvailableCompatTools) {
    result.compatToolsError = "GetAvailableCompatTools is unavailable";
    return result;
  }

  try {
    const tools = await apps.GetAvailableCompatTools(result.appid);
    result.compatTools = JSON.parse(JSON.stringify(tools));
  } catch (error) {
    result.compatToolsError = String(error?.stack ?? error);
  }

  return result;
})()
