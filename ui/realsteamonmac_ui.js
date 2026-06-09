(function initializeRealSteamOnMacUI(globalObject) {
  "use strict";

  const INVALID_PLATFORM = 14;
  const READY_TO_INSTALL = 9;
  const READY_TO_LAUNCH = 11;
  const STATUS_KEY = "__REALSTEAMONMAC_UI_STATUS__";
  const CONFIG_KEY = "__REALSTEAMONMAC_CONFIG__";
  const MANAGED_PREDICATE_KEY =
    "__REALSTEAMONMAC_IS_MANAGED_APP__";
  const COMPAT_SELECTIONS_KEY =
    "__REALSTEAMONMAC_COMPAT_SELECTIONS_V1__";
  const COMPAT_TOOL_PRIORITY = 250;
  const GAME_APP_TYPE = 1;
  const RECONCILE_INTERVAL_MS = 1000;
  const REGISTRY_REFRESH_INTERVAL_MS = 5000;
  const DETAILS_REFRESH_INTERVAL_MS = 1000;

  function isOwnedVisibleGameOverview(overview) {
    return (
      Number.isSafeInteger(overview?.appid) &&
      overview.appid > 0 &&
      overview.app_type === GAME_APP_TYPE &&
      overview.subscribed_to === true &&
      overview.visible_in_game_list === true
    );
  }

  function isOwnedWindowsOnlyGame(overview, details) {
    if (
      !isOwnedVisibleGameOverview(overview) ||
      details?.unAppID !== overview.appid ||
      !Array.isArray(details.vecPlatforms)
    ) {
      return false;
    }
    const platforms = new Set(
      details.vecPlatforms.map((platform) =>
        String(platform).toLowerCase(),
      ),
    );
    return platforms.has("windows") && !platforms.has("osx");
  }

  function buildManagedAppSet(overviews, detailsByAppid) {
    const managed = new Set();
    for (const overview of overviews ?? []) {
      const details = detailsByAppid?.get?.(overview?.appid) ?? null;
      if (isOwnedWindowsOnlyGame(overview, details)) {
        managed.add(overview.appid);
      }
    }
    return managed;
  }

  async function discoverManagedApps({ overviews, loadDetails }) {
    const candidates = (overviews ?? []).filter(
      isOwnedVisibleGameOverview,
    );
    const entries = await Promise.all(
      candidates.map(async (overview) => {
        const details = await loadDetails(overview.appid);
        if (!details) {
          throw new Error(
            `missing Steam app details for AppID ${overview.appid}`,
          );
        }
        return [overview.appid, details];
      }),
    );
    return buildManagedAppSet(candidates, new Map(entries));
  }

  function mergeCompatTools(nativeTools, projectTools) {
    const merged = [];
    const seen = new Set();
    for (const tool of [...(nativeTools ?? []), ...(projectTools ?? [])]) {
      if (
        typeof tool?.strToolName !== "string" ||
        !tool.strToolName ||
        seen.has(tool.strToolName)
      ) {
        continue;
      }
      seen.add(tool.strToolName);
      merged.push(tool);
    }
    return merged;
  }

  function getManagedTargetStatus(state) {
    if (
      state.allowlisted !== true ||
      !Number.isSafeInteger(state.detailsStatus) ||
      state.detailsStatus <= 0 ||
      state.detailsStatus === INVALID_PLATFORM
    ) {
      return null;
    }
    return state.detailsStatus;
  }

  function decideOverviewPatch(state) {
    return {
      normalize:
        getManagedTargetStatus(state) !== null &&
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
    const targetStatus = getManagedTargetStatus({
      allowlisted,
      detailsStatus: details.eDisplayStatus,
      hasAnyLocalContent: details.bHasAnyLocalContent,
    });
    const original = originalStates.get(selected);
    if (original) {
      if (targetStatus !== null) {
        if (
          selected.display_status === targetStatus &&
          selected.is_available_on_current_platform === true &&
          selected.is_invalid_os_type === false
        ) {
          original.normalizedStatus = targetStatus;
          return "unchanged";
        }
        if (
          selected.display_status === original.displayStatus ||
          selected.display_status === original.normalizedStatus ||
          selected.display_status === INVALID_PLATFORM
        ) {
          selected.display_status = targetStatus;
          selected.is_available_on_current_platform = true;
          selected.is_invalid_os_type = false;
          original.normalizedStatus = targetStatus;
          return "normalized";
        }
        return "unchanged";
      }
      if (selected.display_status !== original.normalizedStatus) {
        if (selected.display_status === original.displayStatus) {
          originalStates.delete(selected);
        }
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
      normalizedStatus: targetStatus,
    });
    selected.display_status = targetStatus;
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
    if (!details) {
      return "unchanged";
    }

    const original = originalCompatStates.get(details);
    if (!allowlist.has(details.unAppID)) {
      if (!original) {
        return "unchanged";
      }
      details.strCompatToolName = original.toolName;
      details.strCompatToolDisplayName = original.displayName;
      details.nCompatToolPriority = original.priority;
      originalCompatStates.delete(details);
      return "restored";
    }

    const selected = availableTools.find(
      (tool) => tool.strToolName === selectedTool,
    );
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
      buildManagedAppSet,
      decideOverviewPatch,
      discoverManagedApps,
      findAppActionComponents,
      getSelectedData,
      getSteamUIDocuments,
      getManagedTargetStatus,
      isOwnedWindowsOnlyGame,
      mergeCompatTools,
      refreshAppActionComponents,
      reconcileCompatDetails,
      reconcileAppState,
      COMPAT_TOOL_PRIORITY,
      DETAILS_REFRESH_INTERVAL_MS,
      INVALID_PLATFORM,
      READY_TO_INSTALL,
      READY_TO_LAUNCH,
    };
    return;
  }

  const config = globalObject[CONFIG_KEY] ?? {};
  const configuredAppids = Array.isArray(config.appids)
    ? config.appids
    : [];
  const managedAppids = new Set(
    configuredAppids.filter(
      (appid) => Number.isSafeInteger(appid) && appid > 0,
    ),
  );
  const projectCompatTools = Array.isArray(config.compatTools)
    ? config.compatTools.filter(
        (tool) =>
          typeof tool?.strToolName === "string" &&
          tool.strToolName &&
          typeof tool.strDisplayName === "string" &&
          tool.strDisplayName,
      )
    : [];
  const projectCompatToolNames = new Set(
    projectCompatTools.map((tool) => tool.strToolName),
  );
  const status = {
    version: 7,
    mode: "dynamic-owned-windows-only-registry",
    enabled: true,
    appids: [...managedAppids],
    registryScans: 0,
    registryAdded: 0,
    registryRemoved: 0,
    registryLastScanAt: null,
    registryLastError: null,
    registryNativeSyncs: 0,
    registryLastNativeSyncAt: null,
    registryLastNativeSyncError: null,
    nativeDetailsSubscriptions: 0,
    nativeDetailsRefreshes: 0,
    nativeDetailsRefreshErrors: 0,
    nativeDetailsLastError: null,
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
  globalObject[MANAGED_PREDICATE_KEY] = (appid) =>
    managedAppids.has(Number(appid));

  const originalStates = new WeakMap();
  const originalCompatStates = new WeakMap();
  const refreshedActions = new WeakSet();
  const availableCompatTools = new Map();
  const compatSelections = new Map();
  const nativeSyncedAppids = new Set();
  const nativeDetailsSubscriptions = new Map();
  const nativeDetailsRefreshAt = new Map();
  let storedCompatSelections = {};
  let reconcileRunning = false;
  let registryRefreshRunning = false;
  let lastNativeRegistryPayload = null;

  function releaseNativeDetailsSubscription(appid) {
    const subscription = nativeDetailsSubscriptions.get(appid);
    if (subscription) {
      try {
        subscription.unregister?.();
      } catch {
        // Steam can tear down a subscription during a window/process refresh.
      }
    }
    nativeDetailsSubscriptions.delete(appid);
    nativeDetailsRefreshAt.delete(appid);
    status.nativeDetailsSubscriptions =
      nativeDetailsSubscriptions.size;
  }

  function refreshNativeDetailsSubscription(appid, force = false) {
    if (!nativeSyncedAppids.has(appid)) {
      releaseNativeDetailsSubscription(appid);
      return false;
    }

    const now = Date.now();
    const lastRefresh = nativeDetailsRefreshAt.get(appid) ?? 0;
    if (
      !force &&
      nativeDetailsSubscriptions.has(appid) &&
      now - lastRefresh < DETAILS_REFRESH_INTERVAL_MS
    ) {
      return false;
    }

    releaseNativeDetailsSubscription(appid);
    nativeDetailsRefreshAt.set(appid, now);
    try {
      const subscription =
        globalObject.SteamClient.Apps.RegisterForAppDetails(
          appid,
          (details) => {
            if (
              !nativeSyncedAppids.has(appid) ||
              details?.unAppID !== appid
            ) {
              return;
            }
            globalObject.appDetailsStore?.AppDetailsChanged?.(details);
            void reconcile();
          },
        );
      nativeDetailsSubscriptions.set(appid, subscription);
      status.nativeDetailsSubscriptions =
        nativeDetailsSubscriptions.size;
      status.nativeDetailsRefreshes += 1;
      status.nativeDetailsLastError = null;
      return true;
    } catch (error) {
      status.nativeDetailsRefreshErrors += 1;
      status.nativeDetailsLastError = String(error);
      return false;
    }
  }

  function publishNativeSyncedApps() {
    for (const appid of [...nativeDetailsSubscriptions.keys()]) {
      if (!managedAppids.has(appid)) {
        releaseNativeDetailsSubscription(appid);
      }
    }
    nativeSyncedAppids.clear();
    for (const appid of managedAppids) {
      nativeSyncedAppids.add(appid);
      if (!nativeDetailsSubscriptions.has(appid)) {
        refreshNativeDetailsSubscription(appid, true);
      }
    }
  }

  async function syncNativeRegistry() {
    const endpoint = config.registryEndpoint;
    const token = config.registryToken;
    if (
      typeof endpoint !== "string" ||
      !endpoint ||
      typeof token !== "string" ||
      !token
    ) {
      throw new Error("native registry endpoint is unavailable");
    }
    const payload = [...managedAppids]
      .sort((left, right) => left - right)
      .join(",");
    if (payload === lastNativeRegistryPayload) {
      return true;
    }
    try {
      await globalObject.fetch(
        `${endpoint}?token=${encodeURIComponent(token)}`,
        {
          method: "POST",
          mode: "no-cors",
          headers: { "Content-Type": "text/plain" },
          body: payload,
        },
      );
      lastNativeRegistryPayload = payload;
      status.registryNativeSyncs += 1;
      status.registryLastNativeSyncAt = new Date().toISOString();
      status.registryLastNativeSyncError = null;
      publishNativeSyncedApps();
      return true;
    } catch (error) {
      status.registryLastNativeSyncError = String(error);
      return false;
    }
  }

  function loadCompatSelections() {
    try {
      storedCompatSelections = JSON.parse(
        globalObject.localStorage?.getItem(COMPAT_SELECTIONS_KEY) ?? "{}",
      );
    } catch {
      storedCompatSelections = {};
    }
    for (const appid of managedAppids) {
      ensureCompatSelection(appid);
    }
  }

  function ensureCompatSelection(appid) {
    if (compatSelections.has(appid)) {
      return;
    }
    const key = String(appid);
    const storedTool = Object.prototype.hasOwnProperty.call(
      storedCompatSelections,
      key,
    )
      ? storedCompatSelections[key]
      : config.defaultCompatTool;
    compatSelections.set(
      appid,
      typeof storedTool === "string" ? storedTool : "",
    );
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
    const tools = await originalGetAvailableCompatTools(appid);
    const normalized = mergeCompatTools(
      Array.isArray(tools) ? tools : [],
      managedAppids.has(appid) ? projectCompatTools : [],
    );
    availableCompatTools.set(appid, normalized);
    return normalized;
  }

  let originalGetAvailableCompatTools = null;

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
    originalGetAvailableCompatTools =
      apps.GetAvailableCompatTools.bind(apps);
    apps.GetAvailableCompatTools = async (appid) => {
      if (!managedAppids.has(appid)) {
        return originalGetAvailableCompatTools(appid);
      }
      return getAvailableCompatTools(appid);
    };
    apps.SpecifyCompatTool = async (appid, requestedTool) => {
      if (!managedAppids.has(appid)) {
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

      let result;
      if (!tool || projectCompatToolNames.has(tool)) {
        result = undefined;
      } else {
        result = await originalSpecifyCompatTool(appid, tool);
      }
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
      if (!projectCompatToolNames.has(selectedTool)) {
        await originalSpecifyCompatTool(appid, selectedTool);
      }
      status.compatNativeSyncs += 1;
    }
  }

  async function loadAppDetails(appid) {
    let result =
      globalObject.appDetailsStore?.GetAppDetails?.(appid) ??
      globalObject.appDetailsStore?.m_mapAppData?.get?.(appid)?.details ??
      null;
    if (result && typeof result.then === "function") {
      result = await result;
    }
    if (!result) {
      result =
        await globalObject.appDetailsStore?.RequestAppDetails?.(appid);
    }
    return result?.details ?? result ?? null;
  }

  async function restoreRemovedApp(appid) {
    const overview =
      globalObject.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
    const details = await loadAppDetails(appid);
    if (overview && details) {
      reconcileCompatDetails({
        details,
        allowlist: new Set(),
        selectedTool: "",
        availableTools: [],
        originalCompatStates,
      });
      reconcileAppState({
        overview,
        details,
        allowlist: new Set(),
        originalStates,
      });
    }
    compatSelections.delete(appid);
    availableCompatTools.delete(appid);
    releaseNativeDetailsSubscription(appid);
  }

  async function applyManagedRegistry(nextManagedAppids) {
    const removed = [...managedAppids].filter(
      (appid) => !nextManagedAppids.has(appid),
    );
    const added = [...nextManagedAppids].filter(
      (appid) => !managedAppids.has(appid),
    );
    for (const appid of removed) {
      await restoreRemovedApp(appid);
    }
    managedAppids.clear();
    for (const appid of nextManagedAppids) {
      managedAppids.add(appid);
      ensureCompatSelection(appid);
    }
    status.appids = [...managedAppids].sort((left, right) => left - right);
    status.registryAdded += added.length;
    status.registryRemoved += removed.length;
    if (added.length || removed.length) {
      persistCompatSelections();
    }
  }

  async function refreshManagedRegistry() {
    if (registryRefreshRunning) {
      return;
    }
    registryRefreshRunning = true;
    status.registryScans += 1;
    status.registryLastScanAt = new Date().toISOString();
    status.registryLastError = null;
    try {
      const overviews = globalObject.appStore?.allApps;
      if (!Array.isArray(overviews)) {
        throw new Error("Steam app overview store is unavailable");
      }
      const nextManagedAppids = await discoverManagedApps({
        overviews,
        loadDetails: loadAppDetails,
      });
      await applyManagedRegistry(nextManagedAppids);
      await syncNativeRegistry();
      await reconcile();
    } catch (error) {
      status.registryLastError = String(error);
    } finally {
      registryRefreshRunning = false;
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
      for (const appid of managedAppids) {
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
        if (
          nativeSyncedAppids.has(appid) &&
          details.eDisplayStatus === INVALID_PLATFORM
        ) {
          refreshNativeDetailsSubscription(appid);
        }

        const compatResult = reconcileCompatDetails({
          details,
          allowlist: managedAppids,
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
          allowlist: nativeSyncedAppids,
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
  globalObject.setInterval(
    refreshManagedRegistry,
    REGISTRY_REFRESH_INTERVAL_MS,
  );
  void syncNativeCompatSelections(originalSpecifyCompatTool)
    .then(refreshManagedRegistry)
    .catch((error) => {
      status.lastError = String(error);
    });
})(globalThis);
