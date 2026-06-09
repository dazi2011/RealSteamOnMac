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
  const CONTROL_CONFIGS_KEY =
    "__REALSTEAMONMAC_CONTROL_CONFIGS_V1__";
  const COMPAT_TOOL_PRIORITY = 250;
  const GAME_APP_TYPE = 1;
  const RECONCILE_INTERVAL_MS = 1000;
  const REGISTRY_REFRESH_INTERVAL_MS = 5000;
  const DETAILS_REFRESH_INTERVAL_MS = 1000;
  const CONTROL_DEFAULTS = Object.freeze({
    renderer: "dxmt",
    msync: true,
    retina: false,
    metal_hud: false,
    metalfx: false,
    dxr: false,
    avx: false,
  });

  function normalizeControlConfig(value, fallbackRenderer = "dxmt") {
    const renderers = new Set(["gptk", "dxmt", "dxvk", "wined3d"]);
    const renderer = renderers.has(value?.renderer)
      ? value.renderer
      : renderers.has(fallbackRenderer)
        ? fallbackRenderer
        : CONTROL_DEFAULTS.renderer;
    const normalized = {
      renderer,
      msync:
        typeof value?.msync === "boolean"
          ? value.msync
          : CONTROL_DEFAULTS.msync,
      retina:
        typeof value?.retina === "boolean"
          ? value.retina
          : CONTROL_DEFAULTS.retina,
      metal_hud:
        typeof value?.metal_hud === "boolean"
          ? value.metal_hud
          : CONTROL_DEFAULTS.metal_hud,
      metalfx:
        typeof value?.metalfx === "boolean"
          ? value.metalfx
          : CONTROL_DEFAULTS.metalfx,
      dxr:
        typeof value?.dxr === "boolean"
          ? value.dxr
          : CONTROL_DEFAULTS.dxr,
      avx:
        typeof value?.avx === "boolean"
          ? value.avx
          : CONTROL_DEFAULTS.avx,
    };
    if (renderer !== "gptk") {
      normalized.metalfx = false;
      normalized.dxr = false;
    }
    return normalized;
  }

  function rendererForCompatTool(toolName, projectTools) {
    const tool = (projectTools ?? []).find(
      (candidate) => candidate?.strToolName === toolName,
    );
    return typeof tool?.renderer === "string"
      ? tool.renderer
      : null;
  }

  function compatToolForRenderer(renderer, projectTools) {
    return (
      (projectTools ?? []).find(
        (candidate) => candidate?.renderer === renderer,
      )?.strToolName ?? ""
    );
  }

  function buildControlPayload(value) {
    const config = normalizeControlConfig(value);
    return [
      `renderer=${config.renderer}`,
      `msync=${config.msync ? 1 : 0}`,
      `retina=${config.retina ? 1 : 0}`,
      `metal_hud=${config.metal_hud ? 1 : 0}`,
      `metalfx=${config.metalfx ? 1 : 0}`,
      `dxr=${config.dxr ? 1 : 0}`,
      `avx=${config.avx ? 1 : 0}`,
    ].join("&");
  }

  function buildControlUrl(endpoint, token, appid) {
    if (
      typeof endpoint !== "string" ||
      !endpoint ||
      typeof token !== "string" ||
      !token ||
      !Number.isSafeInteger(appid) ||
      appid <= 0
    ) {
      throw new Error("native control endpoint is unavailable");
    }
    return (
      `${endpoint}?token=${encodeURIComponent(token)}` +
      `&appid=${appid}`
    );
  }

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
    const trackedWindows =
      globalObject.g_FriendsUIApp?.m_IdleTracker?.m_rgWindows ?? [];
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
    for (const windowObject of trackedWindows) {
      try {
        if (windowObject?.closed) {
          continue;
        }
        const documentObject = windowObject?.document;
        if (!documentObject || seen.has(documentObject)) {
          continue;
        }
        seen.add(documentObject);
        documents.push(documentObject);
      } catch {
        // Steam removes popup windows asynchronously while they are closing.
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
      buildControlPayload,
      buildControlUrl,
      compatToolForRenderer,
      mergeCompatTools,
      normalizeControlConfig,
      refreshAppActionComponents,
      reconcileCompatDetails,
      reconcileAppState,
      rendererForCompatTool,
      CONTROL_DEFAULTS,
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
          tool.strDisplayName &&
          ["gptk", "dxmt", "dxvk", "wined3d"].includes(
            tool.renderer,
          ),
      )
    : [];
  const projectCompatToolNames = new Set(
    projectCompatTools.map((tool) => tool.strToolName),
  );
  const status = {
    version: 8,
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
    controlNativeLoads: 0,
    controlNativeSaves: 0,
    controlLastError: null,
    controlPanels: 0,
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
  const controlConfigs = new Map();
  const nativeLoadedControlAppids = new Set();
  const lastNativeControlPayloads = new Map();
  const nativeSyncedAppids = new Set();
  const nativeDetailsSubscriptions = new Map();
  const nativeDetailsRefreshAt = new Map();
  let storedCompatSelections = {};
  let storedControlConfigs = {};
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
      await refreshNativeControlConfigs();
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
    const migratedTool =
      storedTool === "realsteamonmac-experimental"
        ? config.defaultCompatTool
        : storedTool;
    compatSelections.set(
      appid,
      typeof migratedTool === "string" ? migratedTool : "",
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

  function loadControlConfigs() {
    try {
      storedControlConfigs = JSON.parse(
        globalObject.localStorage?.getItem(CONTROL_CONFIGS_KEY) ?? "{}",
      );
    } catch {
      storedControlConfigs = {};
    }
    for (const appid of managedAppids) {
      ensureControlConfig(appid);
    }
  }

  function ensureControlConfig(appid) {
    if (controlConfigs.has(appid)) {
      return controlConfigs.get(appid);
    }
    const key = String(appid);
    const renderer =
      rendererForCompatTool(
        compatSelections.get(appid),
        projectCompatTools,
      ) ?? CONTROL_DEFAULTS.renderer;
    const stored = Object.prototype.hasOwnProperty.call(
      storedControlConfigs,
      key,
    )
      ? storedControlConfigs[key]
      : null;
    const normalized = normalizeControlConfig(stored, renderer);
    controlConfigs.set(appid, normalized);
    return normalized;
  }

  function persistControlConfigs() {
    const serialized = {};
    for (const [appid, value] of controlConfigs) {
      serialized[String(appid)] = normalizeControlConfig(value);
    }
    globalObject.localStorage?.setItem(
      CONTROL_CONFIGS_KEY,
      JSON.stringify(serialized),
    );
  }

  async function loadNativeControlConfig(appid) {
    if (
      nativeLoadedControlAppids.has(appid) ||
      !managedAppids.has(appid)
    ) {
      return;
    }
    const response = await globalObject.fetch(
      buildControlUrl(
        config.controlEndpoint,
        config.registryToken,
        appid,
      ),
      {
        method: "GET",
        mode: "cors",
        cache: "no-store",
      },
    );
    if (response?.ok === false) {
      throw new Error(
        `native control read failed for AppID ${appid}: ` +
          `${response.status}`,
      );
    }
    if (typeof response?.json !== "function") {
      throw new Error("native control response is invalid");
    }
    const loaded = normalizeControlConfig(await response.json());
    controlConfigs.set(appid, loaded);
    const tool = compatToolForRenderer(
      loaded.renderer,
      projectCompatTools,
    );
    if (tool) {
      compatSelections.set(appid, tool);
    }
    nativeLoadedControlAppids.add(appid);
    status.controlNativeLoads += 1;
    status.controlLastError = null;
    persistControlConfigs();
    persistCompatSelections();
  }

  async function refreshNativeControlConfigs() {
    for (const appid of managedAppids) {
      try {
        await loadNativeControlConfig(appid);
      } catch (error) {
        status.controlLastError = String(error);
      }
    }
  }

  async function saveNativeControlConfig(appid, value) {
    if (!managedAppids.has(appid)) {
      throw new Error(`AppID ${appid} is not managed`);
    }
    const normalized = normalizeControlConfig(value);
    const payload = buildControlPayload(normalized);
    if (lastNativeControlPayloads.get(appid) !== payload) {
      const response = await globalObject.fetch(
        buildControlUrl(
          config.controlEndpoint,
          config.registryToken,
          appid,
        ),
        {
          method: "POST",
          mode: "cors",
          cache: "no-store",
          headers: { "Content-Type": "text/plain" },
          body: payload,
        },
      );
      if (response?.ok === false) {
        throw new Error(
          `native control write failed for AppID ${appid}: ` +
            `${response.status}`,
        );
      }
      lastNativeControlPayloads.set(appid, payload);
      status.controlNativeSaves += 1;
    }
    controlConfigs.set(appid, normalized);
    nativeLoadedControlAppids.add(appid);
    status.controlLastError = null;
    persistControlConfigs();
    return normalized;
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
      if (projectCompatToolNames.has(tool)) {
        const renderer = rendererForCompatTool(
          tool,
          projectCompatTools,
        );
        await saveNativeControlConfig(appid, {
          ...ensureControlConfig(appid),
          renderer,
        });
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
    controlConfigs.delete(appid);
    nativeLoadedControlAppids.delete(appid);
    lastNativeControlPayloads.delete(appid);
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
      ensureControlConfig(appid);
    }
    status.appids = [...managedAppids].sort((left, right) => left - right);
    status.registryAdded += added.length;
    status.registryRemoved += removed.length;
    if (added.length || removed.length) {
      persistCompatSelections();
      persistControlConfigs();
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

  function managedAppidFromDocument(documentObject) {
    const locationText = [
      documentObject?.location?.href,
      documentObject?.location?.hash,
    ]
      .filter((value) => typeof value === "string")
      .join(" ");
    for (const match of locationText.matchAll(/\d{3,10}/g)) {
      const appid = Number(match[0]);
      if (managedAppids.has(appid)) {
        return appid;
      }
    }

    const elements = documentObject?.querySelectorAll?.("*") ?? [];
    let inspected = 0;
    for (const element of elements) {
      inspected += 1;
      if (inspected > 2000) {
        break;
      }
      const fiberKey = Object.getOwnPropertyNames(element).find(
        (key) =>
          key.startsWith("__reactFiber$") ||
          key.startsWith("__reactInternalInstance$"),
      );
      let fiber = fiberKey ? element[fiberKey] : null;
      for (let depth = 0; fiber && depth < 30; depth += 1) {
        const candidates = [
          fiber.memoizedProps?.appid,
          fiber.memoizedProps?.overview?.appid,
          fiber.memoizedProps?.details?.unAppID,
          fiber.pendingProps?.appid,
          fiber.pendingProps?.overview?.appid,
          fiber.pendingProps?.details?.unAppID,
        ];
        for (const candidate of candidates) {
          const appid = Number(candidate);
          if (managedAppids.has(appid)) {
            return appid;
          }
        }
        fiber = fiber.return;
      }
    }
    return null;
  }

  function findCompatControlAnchor(documentObject) {
    const candidates = documentObject?.querySelectorAll?.(
      "[role=combobox], select, button, [class]",
    ) ?? [];
    let inspected = 0;
    for (const element of candidates) {
      inspected += 1;
      if (inspected > 2500) {
        break;
      }
      const text = String(element?.textContent ?? "").trim();
      if (!text || !text.includes("RealSteamOnMac")) {
        continue;
      }
      let anchor = element;
      for (let depth = 0; depth < 3; depth += 1) {
        const parent = anchor.parentElement;
        const parentText = String(parent?.textContent ?? "").trim();
        if (
          !parent ||
          !parentText.includes("RealSteamOnMac") ||
          parentText.length > 1200
        ) {
          break;
        }
        anchor = parent;
      }
      return anchor;
    }
    return null;
  }

  function ensureControlPanelStyle(documentObject) {
    if (
      !documentObject?.head ||
      documentObject.querySelector?.(
        "style[data-realsteamonmac-controls]",
      )
    ) {
      return;
    }
    const style = documentObject.createElement("style");
    style.dataset.realsteamonmacControls = "true";
    style.textContent = `
      .realsteamonmac-controls {
        --rsm-blue: #1a9fff;
        --rsm-cyan: #66c0f4;
        --rsm-ink: #0b1118;
        --rsm-panel: #16202b;
        --rsm-panel-2: #1d2b38;
        --rsm-text: #f4f7fb;
        --rsm-muted: #9eb1c2;
        box-sizing: border-box;
        margin: 14px 0 2px;
        padding: 16px;
        width: min(100%, 720px);
        color: var(--rsm-text);
        background:
          linear-gradient(135deg, rgba(26,159,255,.14), transparent 46%),
          linear-gradient(180deg, var(--rsm-panel-2), var(--rsm-panel));
        border: 1px solid rgba(102,192,244,.45);
        border-left: 4px solid var(--rsm-blue);
        border-radius: 4px;
        box-shadow: 0 12px 28px rgba(0,0,0,.28);
        font-family: "Motiva Sans", "Noto Sans SC", sans-serif;
      }
      .realsteamonmac-controls * { box-sizing: border-box; }
      .realsteamonmac-controls__head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 14px;
      }
      .realsteamonmac-controls__eyebrow {
        color: var(--rsm-cyan);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
      }
      .realsteamonmac-controls__title {
        margin-top: 3px;
        font-size: 18px;
        font-weight: 700;
      }
      .realsteamonmac-controls__renderer {
        padding: 6px 9px;
        color: #07121c;
        background: linear-gradient(180deg, #67c1f5, #1a9fff);
        border-radius: 3px;
        font-size: 12px;
        font-weight: 800;
        white-space: nowrap;
      }
      .realsteamonmac-controls__grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
      }
      .realsteamonmac-toggle {
        display: flex;
        align-items: center;
        gap: 10px;
        min-height: 48px;
        padding: 9px 10px;
        background: rgba(5,12,18,.38);
        border: 1px solid rgba(158,177,194,.15);
        border-radius: 3px;
        cursor: pointer;
      }
      .realsteamonmac-toggle:hover {
        border-color: rgba(102,192,244,.48);
      }
      .realsteamonmac-toggle[data-disabled="true"] {
        opacity: .42;
        cursor: not-allowed;
      }
      .realsteamonmac-toggle input {
        width: 18px;
        height: 18px;
        accent-color: var(--rsm-blue);
      }
      .realsteamonmac-toggle__copy {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .realsteamonmac-toggle__label {
        font-size: 13px;
        font-weight: 700;
      }
      .realsteamonmac-toggle__hint {
        color: var(--rsm-muted);
        font-size: 11px;
        line-height: 1.25;
      }
      .realsteamonmac-controls__foot {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-top: 12px;
        color: var(--rsm-muted);
        font-size: 11px;
      }
      .realsteamonmac-controls__status[data-state="saved"] {
        color: #75d17e;
      }
      .realsteamonmac-controls__status[data-state="saving"] {
        color: #f2c94c;
      }
      .realsteamonmac-controls__status[data-state="error"] {
        color: #ff7b72;
      }
      @media (max-width: 640px) {
        .realsteamonmac-controls__grid { grid-template-columns: 1fr; }
      }
    `;
    documentObject.head.appendChild(style);
  }

  function controlDefinitions(renderer) {
    return [
      {
        key: "msync",
        label: "启用 MSync",
        hint: "降低 Wine 同步开销，默认开启",
        enabled: true,
      },
      {
        key: "retina",
        label: "高分辨率模式",
        hint: "写入当前 PFX 的 Wine RetinaMode",
        enabled: true,
      },
      {
        key: "metal_hud",
        label: "Metal HUD",
        hint: "显示 Metal 图形性能叠加层",
        enabled: renderer !== "wined3d",
      },
      {
        key: "metalfx",
        label: "DLSS 转 MetalFX",
        hint: "安装并启用 GPTK MetalFX 映射",
        enabled: renderer === "gptk",
      },
      {
        key: "dxr",
        label: "DXR",
        hint: "向游戏公开 GPTK 光线追踪能力",
        enabled: renderer === "gptk",
      },
      {
        key: "avx",
        label: "Rosetta AVX",
        hint: "为需要 AVX 的游戏公开指令能力",
        enabled: true,
      },
    ];
  }

  function renderControlPanel(panel, appid) {
    const value = ensureControlConfig(appid);
    const rendererLabel =
      projectCompatTools.find(
        (tool) => tool.renderer === value.renderer,
      )?.strDisplayName ?? value.renderer.toUpperCase();
    const definitions = controlDefinitions(value.renderer);
    const signature = JSON.stringify(value);
    if (panel.dataset.signature === signature) {
      return;
    }
    panel.dataset.signature = signature;
    panel.dataset.appid = String(appid);
    panel.innerHTML = `
      <div class="realsteamonmac-controls__head">
        <div>
          <div class="realsteamonmac-controls__eyebrow">Independent Steam Play</div>
          <div class="realsteamonmac-controls__title">RealSteamOnMac 运行控制</div>
        </div>
        <div class="realsteamonmac-controls__renderer">${rendererLabel}</div>
      </div>
      <div class="realsteamonmac-controls__grid">
        ${definitions
          .map(
            (definition) => `
              <label class="realsteamonmac-toggle"
                     data-disabled="${definition.enabled ? "false" : "true"}">
                <input type="checkbox"
                       data-control="${definition.key}"
                       ${value[definition.key] ? "checked" : ""}
                       ${definition.enabled ? "" : "disabled"}>
                <span class="realsteamonmac-toggle__copy">
                  <span class="realsteamonmac-toggle__label">${definition.label}</span>
                  <span class="realsteamonmac-toggle__hint">${definition.hint}</span>
                </span>
              </label>
            `,
          )
          .join("")}
      </div>
      <div class="realsteamonmac-controls__foot">
        <span>AppID ${appid} · 配置按游戏隔离</span>
        <span class="realsteamonmac-controls__status" data-state="saved">已保存</span>
      </div>
    `;

    const statusElement = panel.querySelector(
      ".realsteamonmac-controls__status",
    );
    for (const input of panel.querySelectorAll("input[data-control]")) {
      input.addEventListener("change", async () => {
        const key = input.dataset.control;
        const previous = ensureControlConfig(appid);
        const next = normalizeControlConfig({
          ...previous,
          [key]: input.checked,
        });
        statusElement.textContent = "保存中";
        statusElement.dataset.state = "saving";
        try {
          await saveNativeControlConfig(appid, next);
          panel.dataset.signature = "";
          renderControlPanel(panel, appid);
        } catch (error) {
          input.checked = previous[key];
          status.controlLastError = String(error);
          statusElement.textContent = "保存失败";
          statusElement.dataset.state = "error";
        }
      });
    }
  }

  function mountControlPanels() {
    let mounted = 0;
    for (const documentObject of getSteamUIDocuments(globalObject)) {
      const appid = managedAppidFromDocument(documentObject);
      const existing = documentObject.querySelector?.(
        ".realsteamonmac-controls",
      );
      if (!appid) {
        existing?.remove?.();
        continue;
      }
      const anchor = findCompatControlAnchor(documentObject);
      if (!anchor?.parentElement) {
        continue;
      }
      ensureControlPanelStyle(documentObject);
      let panel = existing;
      if (!panel) {
        panel = documentObject.createElement("section");
        panel.className = "realsteamonmac-controls";
        anchor.parentElement.insertBefore(panel, anchor.nextSibling);
      }
      renderControlPanel(panel, appid);
      mounted += 1;
    }
    status.controlPanels = mounted;
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
      mountControlPanels();
    } catch (error) {
      status.lastError = String(error);
    } finally {
      reconcileRunning = false;
    }
  }

  loadCompatSelections();
  loadControlConfigs();
  persistCompatSelections();
  persistControlConfigs();
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
