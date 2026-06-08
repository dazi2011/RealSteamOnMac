(async () => {
  const appid = 1118200;
  const invalidPlatformStatus = 14;
  const readyToInstallStatus = 9;
  const stateKey = "__realSteamOnMacPeoplePlaygroundUIExperiment";

  if (globalThis[stateKey]) {
    throw new Error("People Playground UI experiment is already active");
  }

  const installButtons = [...document.querySelectorAll("[role=button], button")]
    .filter((element) => element.innerText?.trim() === "安装");
  if (installButtons.length === 0) {
    throw new Error("People Playground install button was not found");
  }

  const contexts = [];
  const seenActions = new Set();
  for (const button of installButtons) {
    const fiberKey = Object.getOwnPropertyNames(button).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    let fiber = fiberKey ? button[fiberKey] : null;
    let overview = null;
    let details = null;
    let actionComponent = null;
    for (let depth = 0; fiber && depth < 40; depth += 1) {
      overview ??= fiber.memoizedProps?.overview ?? null;
      details ??= fiber.memoizedProps?.details ?? null;
      if (
        !actionComponent &&
        typeof fiber.stateNode?.OnClick === "function" &&
        typeof fiber.stateNode?.forceUpdate === "function"
      ) {
        actionComponent = fiber.stateNode;
      }
      fiber = fiber.return;
    }

    if (!overview || overview.appid !== appid) continue;
    if (!details || details.unAppID !== appid) continue;
    if (!actionComponent) {
      throw new Error("People Playground action component was not found");
    }
    if (seenActions.has(actionComponent)) continue;
    seenActions.add(actionComponent);

    const selected = overview.GetPerClientData?.("selected") ??
      overview.selected_per_client_data ??
      overview.per_client_data?.find(
        (entry) => entry.clientid === overview.selected_clientid,
      );
    if (!selected) {
      throw new Error("People Playground selected client data was not found");
    }
    if (
      selected.display_status !== invalidPlatformStatus &&
      selected.display_status !== readyToInstallStatus
    ) {
      throw new Error(
        `unexpected display status ${selected.display_status}`,
      );
    }
    if (
      details.eDisplayStatus !== invalidPlatformStatus &&
      details.eDisplayStatus !== readyToInstallStatus
    ) {
      throw new Error(
        `unexpected details status ${details.eDisplayStatus}`,
      );
    }

    contexts.push({
      selected,
      details,
      actionComponent,
      originalSelectedStatus: selected.display_status,
      originalDetailsStatus: details.eDisplayStatus,
      originalAvailable: selected.is_available_on_current_platform,
      originalInvalidOS: selected.is_invalid_os_type,
    });
  }
  if (contexts.length === 0) {
    throw new Error("no People Playground React contexts were found");
  }

  globalThis[stateKey] = { appid, contexts };
  for (const context of contexts) {
    context.selected.display_status = readyToInstallStatus;
    context.selected.is_available_on_current_platform = true;
    context.selected.is_invalid_os_type = false;
    context.details.eDisplayStatus = readyToInstallStatus;
    context.actionComponent.forceUpdate();
  }

  await new Promise((resolve) => setTimeout(resolve, 500));

  return {
    appid,
    contextCount: contexts.length,
    before: invalidPlatformStatus,
    after: contexts.map((context) => context.selected.display_status),
    detailsAfter: contexts.map((context) => context.details.eDisplayStatus),
    buttons: [...document.querySelectorAll("[role=button], button")]
      .filter((element) => element.innerText?.trim() === "安装")
      .map((element) => ({
      className: element.className,
      pointerEvents: getComputedStyle(element).pointerEvents,
      backgroundColor: getComputedStyle(element).backgroundColor,
      color: getComputedStyle(element).color,
      })),
  };
})()
