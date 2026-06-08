(async () => {
  await SteamClient.Settings.SpecifyGlobalCompatTool("");
  await new Promise((resolve) => setTimeout(resolve, 1500));
  return { globalCompatTool: "" };
})()
