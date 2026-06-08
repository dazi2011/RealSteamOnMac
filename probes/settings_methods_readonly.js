(async () => {
  const settings = globalThis.SteamClient?.Settings;
  if (!settings) {
    return { error: "SteamClient.Settings is unavailable" };
  }
  const result = {
    methods: Object.getOwnPropertyNames(settings)
      .filter((name) => typeof settings[name] === "function")
      .sort(),
  };
  try {
    result.accountSettings = JSON.parse(
      JSON.stringify(await settings.GetAccountSettings()),
    );
  } catch (error) {
    result.accountSettingsError = String(error?.stack ?? error);
  }
  return result;
})()
