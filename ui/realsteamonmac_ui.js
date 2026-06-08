(function initializeRealSteamOnMacUI(globalObject) {
  "use strict";

  const INVALID_PLATFORM = 14;
  const READY_TO_INSTALL = 9;
  const STATUS_KEY = "__REALSTEAMONMAC_UI_STATUS__";
  const CONFIG_KEY = "__REALSTEAMONMAC_CONFIG__";
  const COMPAT_SELECTIONS_KEY =
    "__REALSTEAMONMAC_COMPAT_SELECTIONS_V1__";
  const COMPAT_TOOL_PRIORITY = 250;
  const RECONCILE_INTERVAL_MS = 1000;

  function decideOverviewPatch(state) {
    return {
      normalize:
        state.allowlisted === true &&
        state.hasAnyLocalContent !== true &&
        state.detailsStatus === READY_TO_INSTALL &&
        state.overviewStatus === INVALID_PLATFORM,
    };
  }

  function getSelectedData(overview) {
    return (
      overview?.GetPerClientData?.("selected") ??
      overview?.selected_per_client_data ??
      overview?.per_client_data?.find(
        (entry) => entry.clientid === overview.selected_clientid,
      ) ??
      null
    );
  }

  function findAppActionComponents(documentObject, appid) {
    if (!documentObject?.querySelectorAll) {
      return [];
    }

    const components = [];
    const seen = new Set();
    for (const element of documentObject.querySelectorAll(
      "[role=button], button",
    )) {
      const fiberKey = Object.getOwnPropertyNames(element).find(
        (key) =>
          key.startsWith("__reactFiber$") ||
          key.startsWith("__reactInternalInstance$"),
      );
      let fiber = fiberKey ? element[fiberKey] : null;
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

      if (
        overview?.appid !== appid ||
        details?.unAppID !== appid ||
        !actionComponent ||
        seen.has(actionComponent)
      ) {
        continue;
      }
      seen.add(actionComponent);
      components.push(actionComponent);
    }
    return components;
  }

  function refreshAppActionComponents({
    documents,
    appid,
    refreshedActions,
    force,
  }) {
    let refreshCount = 0;
    for (const documentObject of documents) {
      for (const actionComponent of findAppActionComponents(
        documentObject,
        appid,
      )) {
        if (!force && refreshedActions.has(actionComponent)) {
          continue;
        }
        actionComponent.forceUpdate();
        refreshedActions.add(actionComponent);
        refreshCount += 1;
      }
    }
    return refreshCount;
  }

  function getSteamUIDocuments(globalObject) {
    const windowStore = globalObject.SteamUIStore?.WindowStore;
    const instances = [
      ...(windowStore?.SteamUIWindows ?? []),
      windowStore?.MainWindowInstance,
    ];
    const documents = [];
    const seen = new Set();
    for (const instance of instances) {
      try {
        const documentObject = instance?.m_BrowserWindow?.document;
        if (!documentObject || seen.has(documentObject)) {
          continue;
        }
        seen.add(documentObject);
        documents.push(documentObject);
      } catch {
        // A Steam window can disappear while the shared context enumerates it.
      }
    }
    return documents;
  }

  function reconcileAppState({
    overview,
    details,
    allowlist,
    originalStates,
  }) {
    if (
      !overview ||
      !details ||
      overview.appid !== details.unAppID
    ) {
      return "unchanged";
    }

    const selected = getSelectedData(overview);
    if (!selected) {
      return "unchanged";
    }

    const allowlisted = allowlist.has(overview.appid);
    const original = originalStates.get(selected);
    if (original) {
      if (selected.display_status !== READY_TO_INSTALL) {
        if (
          selected.display_status === original.displayStatus &&
          allowlisted &&
          details.eDisplayStatus === READY_TO_INSTALL &&
          details.bHasAnyLocalContent !== true
        ) {
          selected.display_status = READY_TO_INSTALL;
          selected.is_available_on_current_platform = true;
          selected.is_invalid_os_type = false;
          return "normalized";
        }
        if (selected.display_status === original.displayStatus) {
          originalStates.delete(selected);
        }
        return "unchanged";
      }
      if (
        allowlisted &&
        details.eDisplayStatus === READY_TO_INSTALL &&
        details.bHasAnyLocalContent !== true
      ) {
        return "unchanged";
      }

      selected.display_status = original.displayStatus;
      selected.is_available_on_current_platform =
        original.availableOnCurrentPlatform;
      selected.is_invalid_os_type = original.invalidOsType;
      originalStates.delete(selected);
      return "restored";
    }

    const decision = decideOverviewPatch({
      allowlisted,
      detailsStatus: details.eDisplayStatus,
      overviewStatus: selected.display_status,
      hasAnyLocalContent: details.bHasAnyLocalContent,
    });
    if (!decision.normalize) {
      return "unchanged";
    }

    originalStates.set(selected, {
      displayStatus: selected.display_status,
      availableOnCurrentPlatform:
        selected.is_available_on_current_platform,
      invalidOsType: selected.is_invalid_os_type,
    });
    selected.display_status = READY_TO_INSTALL;
    selected.is_available_on_current_platform = true;
    selected.is_invalid_os_type = false;
    return "normalized";
  }

  function reconcileCompatDetails({
    details,
    allowlist,
    selectedTool,
    availableTools,
    originalCompatStates,
  }) {
    if (!details || !allowlist.has(details.unAppID)) {
      return "unchanged";
    }

    const selected = availableTools.find(
      (tool) => tool.strToolName === selectedTool,
    );
    const original = originalCompatStates.get(details);
    if (!selected) {
      if (!original) {
        return "unchanged";
      }
      details.strCompatToolName = original.toolName;
      details.strCompatToolDisplayName = original.displayName;
      details.nCompatToolPriority = original.priority;
      originalCompatStates.delete(details);
      return "restored";
    }

    if (
      details.strCompatToolName === selected.strToolName &&
      details.strCompatToolDisplayName === selected.strDisplayName &&
      details.nCompatToolPriority === COMPAT_TOOL_PRIORITY
    ) {
      return "unchanged";
    }
    if (!original) {
      originalCompatStates.set(details, {
        toolName: details.strCompatToolName,
        displayName: details.strCompatToolDisplayName,
        priority: details.nCompatToolPriority,
      });
    }
    details.strCompatToolName = selected.strToolName;
    details.strCompatToolDisplayName = selected.strDisplayName;
    details.nCompatToolPriority = COMPAT_TOOL_PRIORITY;
    return "normalized";
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      decideOverviewPatch,
      findAppActionComponents,
      getSelectedData,
      getSteamUIDocuments,
      refreshAppActionComponents,
      reconcileCompatDetails,
      reconcileAppState,
      COMPAT_TOOL_PRIORITY,
      INVALID_PLATFORM,
      READY_TO_INSTALL,
    };
    return;
  }

  const config = globalObject[CONFIG_KEY] ?? {};
  const configuredAppids = Array.isArray(config.appids)
    ? config.appids
    : [];
  const allowlist = new Set(
    configuredAppids.filter(
      (appid) => Number.isSafeInteger(appid) && appid > 0,
    ),
  );
  const status = {
    version: 4,
    mode: "shared-app-store-native-actions-and-compatibility",
    enabled: allowlist.size > 0,
    appids: [...allowlist],
    scans: 0,
    normalized: 0,
    restored: 0,
    compatNormalized: 0,
    compatRestored: 0,
    compatNativeSyncs: 0,
    actionRefreshes: 0,
    missingOverview: 0,
    missingDetails: 0,
    lastScanAt: null,
    lastError: null,
  };
  globalObject[STATUS_KEY] = status;

  if (!status.enabled) {
    return;
  }

  const originalStates = new WeakMap();
  const originalCompatStates = new WeakMap();
  const refreshedActions = new WeakSet();
  const availableCompatTools = new Map();
  const compatSelections = new Map();
  let reconcileRunning = false;

  function loadCompatSelections() {
    let stored = {};
    try {
      stored = JSON.parse(
        globalObject.localStorage?.getItem(COMPAT_SELECTIONS_KEY) ?? "{}",
      );
    } catch {
      stored = {};
    }
    for (const appid of allowlist) {
      const key = String(appid);
      const storedTool = Object.prototype.hasOwnProperty.call(stored, key)
        ? stored[key]
        : config.compatTools?.[key];
      compatSelections.set(
        appid,
        typeof storedTool === "string" ? storedTool : "",
      );
    }
  }

  function persistCompatSelections() {
    const serialized = {};
    for (const [appid, tool] of compatSelections) {
      serialized[String(appid)] = tool;
    }
    globalObject.localStorage?.setItem(
      COMPAT_SELECTIONS_KEY,
      JSON.stringify(serialized),
    );
  }

  async function getAvailableCompatTools(appid) {
    if (availableCompatTools.has(appid)) {
      return availableCompatTools.get(appid);
    }
    const tools =
      await globalObject.SteamClient.Apps.GetAvailableCompatTools(appid);
    const normalized = Array.isArray(tools) ? tools : [];
    availableCompatTools.set(appid, normalized);
    return normalized;
  }

  function installCompatToolBridge() {
    const apps = globalObject.SteamClient?.Apps;
    if (
      !apps ||
      typeof apps.SpecifyCompatTool !== "function" ||
      typeof apps.GetAvailableCompatTools !== "function"
    ) {
      throw new Error("Steam compatibility tool APIs are unavailable");
    }

    const originalSpecifyCompatTool =
      apps.SpecifyCompatTool.bind(apps);
    apps.SpecifyCompatTool = async (appid, requestedTool) => {
      if (!allowlist.has(appid)) {
        return originalSpecifyCompatTool(appid, requestedTool);
      }

      const tool =
        typeof requestedTool === "string" ? requestedTool : "";
      if (tool) {
        const tools = await getAvailableCompatTools(appid);
        if (!tools.some((candidate) => candidate.strToolName === tool)) {
          throw new Error(
            `compatibility tool ${tool} is unavailable for AppID ${appid}`,
          );
        }
      }

      const result = await originalSpecifyCompatTool(appid, tool);
      compatSelections.set(appid, tool);
      persistCompatSelections();
      void reconcile();
      return result;
    };
    return originalSpecifyCompatTool;
  }

  async function syncNativeCompatSelections(originalSpecifyCompatTool) {
    for (const [appid, selectedTool] of compatSelections) {
      if (!selectedTool) {
        continue;
      }
      const tools = await getAvailableCompatTools(appid);
      if (
        !tools.some((tool) => tool.strToolName === selectedTool)
      ) {
        throw new Error(
          `configured compatibility tool ${selectedTool} is unavailable ` +
            `for AppID ${appid}`,
        );
      }
      await originalSpecifyCompatTool(appid, selectedTool);
      status.compatNativeSyncs += 1;
    }
  }

  async function reconcile() {
    if (reconcileRunning) {
      return;
    }
    reconcileRunning = true;
    status.scans += 1;
    status.lastScanAt = new Date().toISOString();
    status.lastError = null;

    try {
      for (const appid of allowlist) {
        const overview =
          globalObject.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
        if (!overview) {
          status.missingOverview += 1;
          continue;
        }

        const detailsResult =
          globalObject.appDetailsStore?.GetAppDetails?.(appid) ??
          globalObject.appDetailsStore?.m_mapAppData?.get?.(appid)?.details ??
          null;
        const details =
          detailsResult && typeof detailsResult.then === "function"
            ? await detailsResult
            : detailsResult;
        if (!details) {
          status.missingDetails += 1;
          continue;
        }

        const compatResult = reconcileCompatDetails({
          details,
          allowlist,
          selectedTool: compatSelections.get(appid) ?? "",
          availableTools: await getAvailableCompatTools(appid),
          originalCompatStates,
        });
        if (compatResult === "normalized") {
          status.compatNormalized += 1;
        } else if (compatResult === "restored") {
          status.compatRestored += 1;
        }

        const result = reconcileAppState({
          overview,
          details,
          allowlist,
          originalStates,
        });
        if (result === "normalized") {
          status.normalized += 1;
        } else if (result === "restored") {
          status.restored += 1;
        }
        status.actionRefreshes += refreshAppActionComponents({
          documents: getSteamUIDocuments(globalObject),
          appid,
          refreshedActions,
          force: result !== "unchanged",
        });
      }
    } catch (error) {
      status.lastError = String(error);
    } finally {
      reconcileRunning = false;
    }
  }

  loadCompatSelections();
  persistCompatSelections();
  const originalSpecifyCompatTool = installCompatToolBridge();
  globalObject.setInterval(reconcile, RECONCILE_INTERVAL_MS);
  void syncNativeCompatSelections(originalSpecifyCompatTool)
    .then(reconcile)
    .catch((error) => {
      status.lastError = String(error);
    });
})(globalThis);
