(async () => {
  const appid = 1118200;
  if (appid !== 1118200) {
    throw new Error("refusing to open an install wizard for another AppID");
  }

  const before = await SteamClient.Installs.GetInstallManagerInfo();
  const openResult = await SteamClient.Installs.OpenInstallWizard([appid]);
  await new Promise((resolve) => setTimeout(resolve, 1500));
  const after = await SteamClient.Installs.GetInstallManagerInfo();

  return {
    appid,
    openResult: openResult ?? null,
    before: JSON.parse(JSON.stringify(before)),
    after: JSON.parse(JSON.stringify(after)),
  };
})()
