(() => {
  const appid = 1118200;
  const bodyText = document.body?.innerText ?? "";
  const comboboxes = Array.from(
    document.querySelectorAll("[role=combobox]"),
  );
  const expectedNativeControlSectionOrder = [
    "兼容性选项",
    "安装 Windows 组件",
    "容器操作",
    "运行命令",
    "最近操作状态",
  ];
  const nativeControlSectionOrder = Array.from(
    document.querySelectorAll(".DialogSettingsSection"),
  )
    .map((section) => {
      const lines = (section.innerText ?? "")
        .split("\n")
        .map((line) => line.trim());
      return expectedNativeControlSectionOrder.find((label) =>
        lines.includes(label),
      );
    })
    .filter(Boolean);

  return {
    appid,
    title: document.title,
    hasCompatibilityPage: bodyText
      .split("\n")
      .some((line) => line.trim() === "兼容性"),
    hasSteamPlaySelector: bodyText.includes(
      "强制使用特定 Steam Play 兼容性工具",
    ),
    hasNativeControlSections:
      nativeControlSectionOrder.length ===
        expectedNativeControlSectionOrder.length &&
      nativeControlSectionOrder.every(
        (label, index) =>
          label === expectedNativeControlSectionOrder[index],
      ),
    nativeControlSectionOrder,
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
