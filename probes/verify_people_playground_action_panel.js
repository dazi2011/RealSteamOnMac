(() => {
  const appid = 1118200;
  const panel = document.querySelector(".realsteamonmac-controls");
  if (Number(panel?.dataset.appid) !== appid) {
    throw new Error(
      `People Playground panel AppID mismatch: ${panel?.dataset.appid}`,
    );
  }
  const actionStatus = panel?.querySelector(
    ".realsteamonmac-action-status",
  );
  return {
    panelCount: document.querySelectorAll(
      ".realsteamonmac-controls",
    ).length,
    appid,
    renderer:
      panel
        ?.querySelector(".realsteamonmac-controls__renderer")
        ?.textContent?.trim() ?? null,
    runCommand: {
      target: Boolean(panel?.querySelector("[data-run-target]")),
      arguments: Boolean(
        panel?.querySelector("[data-run-arguments]"),
      ),
      environment: Boolean(
        panel?.querySelector("[data-run-environment]"),
      ),
      button: Boolean(panel?.querySelector("[data-run-command]")),
      noShell: (panel?.textContent ?? "").includes("NO SHELL"),
    },
    dependencies: Array.from(
      panel?.querySelectorAll("[data-dependency-card]") ?? [],
    ).map((card) => ({
      id:
        card.querySelector("[data-install-dependency]")?.dataset
          ?.installDependency ?? null,
      text: card.textContent?.replace(/\s+/g, " ").trim() ?? "",
    })),
    actionStatus: actionStatus
      ? {
          state: actionStatus.dataset.state ?? null,
          text: actionStatus.textContent?.replace(/\s+/g, " ").trim(),
        }
      : null,
  };
})()
