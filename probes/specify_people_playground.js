(async () => {
  const appid = 1118200;
  const toolName = "realsteamonmac-experimental";

  if (appid !== 1118200) {
    throw new Error("refusing to modify a non-allowlisted AppID");
  }

  const before = JSON.parse(
    JSON.stringify(await SteamClient.Apps.GetAvailableCompatTools(appid)),
  );
  if (!before.some((tool) => tool.strToolName === toolName)) {
    throw new Error("allowlisted compatibility tool is not available");
  }

  const specifyResult = await SteamClient.Apps.SpecifyCompatTool(
    appid,
    toolName,
  );
  await new Promise((resolve) => setTimeout(resolve, 1500));

  return {
    appid,
    toolName,
    specifyResult: specifyResult ?? null,
    availableTools: JSON.parse(
      JSON.stringify(await SteamClient.Apps.GetAvailableCompatTools(appid)),
    ),
  };
})()
