(() => {
  const appid = 1118200;
  const statusKey = "__REALSTEAMONMAC_UI_STATUS__";

  const findFiber = (element) => {
    const fiberKey = Object.getOwnPropertyNames(element).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    return fiberKey ? element[fiberKey] : null;
  };

  const findContext = (element) => {
    let fiber = findFiber(element);
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
    if (!overview || overview.appid !== appid) return null;
    if (!details || details.unAppID !== appid) return null;
    const selected =
      overview.GetPerClientData?.("selected") ??
      overview.selected_per_client_data ??
      overview.per_client_data?.find(
        (entry) => entry.clientid === overview.selected_clientid,
      );
    if (!selected || !actionComponent) return null;
    return { overview, details, selected, actionComponent };
  };

  const contexts = [];
  const seenActions = new Set();
  for (const element of document.querySelectorAll("[role=button], button")) {
    const context = findContext(element);
    if (!context || seenActions.has(context.actionComponent)) continue;
    seenActions.add(context.actionComponent);

    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    contexts.push({
      text: element.innerText?.trim() ?? "",
      pointerEvents: style.pointerEvents,
      backgroundImage: style.backgroundImage,
      backgroundColor: style.backgroundColor,
      color: style.color,
      rect: {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      },
      overviewStatus: context.selected.display_status,
      detailsStatus: context.details.eDisplayStatus,
      isAvailableOnCurrentPlatform:
        context.selected.is_available_on_current_platform,
      isInvalidOsType: context.selected.is_invalid_os_type,
      hasAnyLocalContent: context.details.bHasAnyLocalContent,
      compatToolName: context.details.strCompatToolName ?? null,
      compatToolDisplayName: context.details.strCompatToolDisplayName ?? null,
      actionComponentName: context.actionComponent.constructor?.name ?? null,
    });
  }

  const visibleButton =
    contexts.find(
      (candidate) =>
        candidate.pointerEvents === "auto" &&
        candidate.rect.width > 0 &&
        candidate.rect.height > 0,
    ) ?? contexts[0] ?? null;

  return {
    appid,
    contextCount: contexts.length,
    overviewStatus: visibleButton?.overviewStatus ?? null,
    detailsStatus: visibleButton?.detailsStatus ?? null,
    pointerEvents: visibleButton?.pointerEvents ?? null,
    backgroundImage: visibleButton?.backgroundImage ?? null,
    backgroundColor: visibleButton?.backgroundColor ?? null,
    patchStatus: globalThis[statusKey] ?? null,
    buttons: contexts,
  };
})()
