(async () => {
  const appid = 1118200;
  const toolName = "realsteamonmac-experimental";

  if (appid !== 1118200) {
    throw new Error("refusing to refresh a non-allowlisted AppID");
  }

  const availableTools = JSON.parse(
    JSON.stringify(await SteamClient.Apps.GetAvailableCompatTools(appid)),
  );
  if (!availableTools.some((tool) => tool.strToolName === toolName)) {
    throw new Error("allowlisted compatibility tool is not available");
  }

  await SteamClient.Apps.SpecifyCompatTool(appid, "");
  await new Promise((resolve) => setTimeout(resolve, 500));
  await SteamClient.Apps.SpecifyCompatTool(appid, toolName);
  await new Promise((resolve) => setTimeout(resolve, 1500));

  return {
    appid,
    toolName,
    availableTools: JSON.parse(
      JSON.stringify(await SteamClient.Apps.GetAvailableCompatTools(appid)),
    ),
  };
})()
