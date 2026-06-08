(async () => {
  const appid = 1118200;
  const result = {
    appid,
    steamClientNamespaces: Object.getOwnPropertyNames(
      globalThis.SteamClient ?? {},
    ).sort(),
  };

  for (const namespaceName of result.steamClientNamespaces) {
    const namespace = globalThis.SteamClient?.[namespaceName];
    if (!namespace || !/App|Install|Download|Compat|Content/i.test(namespaceName)) {
      continue;
    }
    result[`${namespaceName}Methods`] = Object.getOwnPropertyNames(namespace)
      .filter((name) => typeof namespace[name] === "function")
      .sort();
  }

  try {
    result.cachedAppDetails = JSON.parse(
      JSON.stringify(await SteamClient.Apps.GetCachedAppDetails(appid)),
    );
  } catch (error) {
    result.cachedAppDetailsError = String(error?.stack ?? error);
  }

  result.interestingGlobals = Object.getOwnPropertyNames(globalThis)
    .filter((name) => /webpack|appoverview|library|install|compat/i.test(name))
    .sort();

  return result;
})()
