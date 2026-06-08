(() => {
  const apps = globalThis.SteamClient?.Apps;
  if (!apps) return { error: "SteamClient.Apps is unavailable" };

  const own = Object.getOwnPropertyNames(apps);
  const prototype = Object.getOwnPropertyNames(Object.getPrototypeOf(apps) ?? {});
  return {
    own: own.sort(),
    prototype: prototype.sort(),
  };
})()
