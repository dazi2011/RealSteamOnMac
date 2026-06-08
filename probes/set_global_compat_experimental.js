(async () => {
  const toolName = "realsteamonmac-experimental";
  const available = JSON.parse(
    JSON.stringify(await SteamClient.Settings.GetGlobalCompatTools()),
  );

  if (!available.some((tool) => tool.strToolName === toolName)) {
    throw new Error("experimental compatibility tool is unavailable");
  }

  await SteamClient.Settings.SpecifyGlobalCompatTool(toolName);
  await new Promise((resolve) => setTimeout(resolve, 1500));
  return { globalCompatTool: toolName };
})()

