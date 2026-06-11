(() => {
  const findFiber = (element) => {
    const fiberKey = Object.getOwnPropertyNames(element ?? {}).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    return fiberKey ? element[fiberKey] : null;
  };

  const findActionContext = (element) => {
    let fiber = findFiber(element);
    let overview = null;
    let details = null;
    let actionComponent = null;
    for (let depth = 0; fiber && depth < 48; depth += 1) {
      const props = fiber.memoizedProps ?? fiber.pendingProps;
      overview ??= props?.overview ?? null;
      details ??= props?.details ?? null;
      if (
        !actionComponent &&
        typeof fiber.stateNode?.OnClick === "function" &&
        typeof fiber.stateNode?.forceUpdate === "function"
      ) {
        actionComponent = fiber.stateNode;
      }
      fiber = fiber.return;
    }
    const appid = Number(overview?.appid);
    if (
      !Number.isSafeInteger(appid) ||
      appid <= 0 ||
      Number(details?.unAppID) !== appid ||
      !actionComponent
    ) {
      return null;
    }
    const selected =
      overview.GetPerClientData?.("selected") ??
      overview.selected_per_client_data ??
      overview.per_client_data?.find(
        (entry) => entry.clientid === overview.selected_clientid,
      ) ??
      null;
    return { appid, overview, details, selected, actionComponent };
  };

  const windowStore = globalThis.SteamUIStore?.WindowStore;
  const instances = [
    ...(windowStore?.SteamUIWindows ?? []),
    windowStore?.MainWindowInstance,
  ];
  const trackedWindows =
    globalThis.g_FriendsUIApp?.m_IdleTracker?.m_rgWindows ?? [];
  const documents = [];
  const seenDocuments = new Set();
  const addDocument = (documentObject, source) => {
    if (!documentObject || seenDocuments.has(documentObject)) {
      return;
    }
    seenDocuments.add(documentObject);
    documents.push({ documentObject, source });
  };

  for (const instance of instances) {
    try {
      addDocument(instance?.m_BrowserWindow?.document, "window-store");
    } catch {
      // Steam can close a window while this read-only probe is scanning it.
    }
  }
  for (const windowObject of trackedWindows) {
    try {
      if (!windowObject?.closed) {
        addDocument(windowObject?.document, "idle-tracker");
      }
    } catch {
      // Steam can close a popup while this read-only probe is scanning it.
    }
  }

  const actions = [];
  const seenElements = new Set();
  for (const { documentObject, source } of documents) {
    for (const element of documentObject.querySelectorAll(
      "button, [role=button]",
    )) {
      if (seenElements.has(element)) {
        continue;
      }
      const context = findActionContext(element);
      if (!context) {
        continue;
      }
      seenElements.add(element);
      const style = documentObject.defaultView.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      actions.push({
        appid: context.appid,
        documentTitle: documentObject.title,
        source,
        text: element.innerText?.replace(/\s+/g, " ").trim() ?? "",
        pointerEvents: style.pointerEvents,
        display: style.display,
        visibility: style.visibility,
        rect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        },
        overviewStatus: context.selected?.display_status ?? null,
        detailsStatus: context.details.eDisplayStatus,
        installed: context.selected?.installed ?? null,
        hasAnyLocalContent:
          context.details.bHasAnyLocalContent ?? null,
        sizeOnDisk: String(context.overview.size_on_disk ?? ""),
        isAvailableOnCurrentPlatform:
          context.selected?.is_available_on_current_platform ?? null,
        isInvalidOsType:
          context.selected?.is_invalid_os_type ?? null,
        actionComponentName:
          context.actionComponent.constructor?.name ?? null,
      });
    }
  }

  return {
    language: new URL(globalThis.location.href).searchParams.get(
      "LANGUAGE",
    ),
    documents: documents.map(({ documentObject, source }) => ({
      source,
      title: documentObject.title,
      location: String(documentObject.location),
      buttonCount: documentObject.querySelectorAll(
        "button, [role=button]",
      ).length,
    })),
    actions,
  };
})()
