(() => {
  const appid = 1118200;
  const expectedTool = "RealSteamOnMac Experimental";
  const checkbox = document.querySelector("[role=checkbox]");
  const toolSelector = document.querySelector("[role=combobox]");
  const bodyText = document.body?.innerText ?? "";

  return {
    appid,
    title: document.title,
    hasCompatibilityPage: bodyText
      .split("\n")
      .some((line) => line.trim() === "兼容性"),
    checked: checkbox?.getAttribute("aria-checked") ?? null,
    selectedTool: toolSelector?.innerText?.trim() ?? null,
    expectedTool,
  };
})()
