(() => {
  const appid = 1118200;
  const expectedTool = "RealSteamOnMac - DXMT 0.80";
  const toolSelector = document.querySelector("[role=combobox]");
  const controlPanel = document.querySelector(
    ".realsteamonmac-controls",
  );
  const bodyText = document.body?.innerText ?? "";

  return {
    appid,
    title: document.title,
    hasCompatibilityPage: bodyText
      .split("\n")
      .some((line) => line.trim() === "兼容性"),
    selectedTool: toolSelector?.innerText?.trim() ?? null,
    expectedTool,
    controlPanelCount: document.querySelectorAll(
      ".realsteamonmac-controls",
    ).length,
    controlRenderer:
      controlPanel?.querySelector(
        ".realsteamonmac-controls__renderer",
      )?.textContent?.trim() ?? null,
    controls: Array.from(
      controlPanel?.querySelectorAll("input[data-control]") ?? [],
    ).map((input) => ({
      key: input.dataset.control,
      checked: input.checked,
      disabled: input.disabled,
    })),
  };
})()
