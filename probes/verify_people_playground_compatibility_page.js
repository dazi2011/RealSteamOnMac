(() => {
  const appid = 1118200;
  const bodyText = document.body?.innerText ?? "";
  const comboboxes = Array.from(
    document.querySelectorAll("[role=combobox]"),
  );

  return {
    appid,
    title: document.title,
    hasCompatibilityPage: bodyText
      .split("\n")
      .some((line) => line.trim() === "兼容性"),
    hasSteamPlaySelector: bodyText.includes(
      "强制使用特定 Steam Play 兼容性工具",
    ),
    hasNativeControlSections: [
      "RealSteamOnMac 兼容性选项",
      "运行命令",
      "安装应用程序到容器",
      "容器操作",
    ].every((label) => bodyText.includes(label)),
    comboboxes: comboboxes.map((element) => ({
      text: element.innerText?.replace(/\s+/g, " ").trim() ?? "",
      className: String(element.className),
      isSteamDialogDropDown: element.classList.contains(
        "DialogDropDown",
      ),
    })),
    nativeCheckboxCount: document.querySelectorAll(
      "[role=checkbox]",
    ).length,
    legacyControlPanelCount: document.querySelectorAll(
      ".realsteamonmac-controls",
    ).length,
    legacyModalLayerCount: document.querySelectorAll(
      ".realsteamonmac-modal-layer",
    ).length,
  };
})()
