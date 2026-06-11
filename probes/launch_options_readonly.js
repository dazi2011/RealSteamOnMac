(async () => {
  const appids = [1174180, 990080, 714010, 1118200];
  const apps = globalThis.SteamClient?.Apps;
  if (typeof apps?.GetLaunchOptionsForApp !== "function") {
    return { error: "Steam launch-options API is unavailable" };
  }

  const result = {};
  for (const appid of appids) {
    try {
      const options = await apps.GetLaunchOptionsForApp(appid);
      result[appid] = (options ?? []).map((option) => ({
        json: JSON.parse(JSON.stringify(option)),
        ownProperties: Object.getOwnPropertyNames(option).sort(),
        prototypeProperties: Object.getOwnPropertyNames(
          Object.getPrototypeOf(option) ?? {},
        ).sort(),
      }));
    } catch (error) {
      result[appid] = { error: String(error?.stack ?? error) };
    }
  }
  return result;
})()
