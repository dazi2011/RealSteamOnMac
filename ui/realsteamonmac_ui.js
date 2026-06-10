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
  const DETAILS_REFRESH_INTERVAL_MS = 5000;
  const ACTION_POLL_INTERVAL_MS = 1000;
  const ACTION_POLL_LIMIT = 3600;
  const ACTION_JOB_ID_PATTERN = /^[0-9a-f]{32}$/;
  const CONTROL_DEFAULTS = Object.freeze({
    compat_tool: "",
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
      compat_tool:
        typeof value?.compat_tool === "string"
          ? value.compat_tool
          : CONTROL_DEFAULTS.compat_tool,
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
    return normalized;
  }

  function compatToolRecord(toolName, projectTools) {
    return (
      (projectTools ?? []).find(
        (candidate) => candidate?.strToolName === toolName,
      ) ?? null
    );
  }

  function applyToolCapabilities(value, tool) {
    const normalized = normalizeControlConfig(
      value,
      tool?.renderer,
    );
    if (!tool?.capabilities?.metalfx) {
      normalized.metalfx = false;
    }
    if (!tool?.capabilities?.dxr) {
      normalized.dxr = false;
    }
    if (!tool?.capabilities?.metal_hud) {
      normalized.metal_hud = false;
    }
    if (!tool?.capabilities?.msync) {
      normalized.msync = false;
    }
    if (!tool?.capabilities?.retina) {
      normalized.retina = false;
    }
    if (!tool?.capabilities?.avx) {
      normalized.avx = false;
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
      `compat_tool=${encodeURIComponent(config.compat_tool)}`,
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

  function buildActionUrl(endpoint, token, appid) {
    if (
      typeof endpoint !== "string" ||
      !endpoint ||
      typeof token !== "string" ||
      !token ||
      !Number.isSafeInteger(appid) ||
      appid <= 0
    ) {
      throw new Error("native action endpoint is unavailable");
    }
    return (
      `${endpoint}?token=${encodeURIComponent(token)}` +
      `&appid=${appid}`
    );
  }

  function buildJobUrl(endpoint, token, appid, jobId) {
    if (
      !ACTION_JOB_ID_PATTERN.test(String(jobId ?? ""))
    ) {
      throw new Error("native action job ID is invalid");
    }
    return (
      buildActionUrl(endpoint, token, appid) +
      `&job=${jobId}`
    );
  }

  function encodeActionPayload(entries) {
    return entries
      .map(
        ([key, value]) =>
          `${encodeURIComponent(key)}=${encodeURIComponent(
            String(value ?? ""),
          )}`,
      )
      .join("&");
  }

  function buildRunCommandPayload({
    target = "",
    arguments: commandArguments = "",
    environment = "",
  } = {}) {
    return encodeActionPayload([
      ["action", "run-command"],
      ["target", target],
      ["arguments", commandArguments],
      ["environment", environment],
    ]);
  }

  function buildDependencyPayload(dependency) {
    if (
      typeof dependency !== "string" ||
      !/^[a-z0-9][a-z0-9-]{1,31}$/.test(dependency)
    ) {
      throw new Error("dependency ID is invalid");
    }
    return encodeActionPayload([
      ["action", "install-dependency"],
      ["dependency", dependency],
    ]);
  }

  function buildContainerActionPayload(operation) {
    const operations = new Set([
      "open-c-drive",
      "install-application",
      "wine-configuration",
      "controllers",
      "restart",
      "task-manager",
      "quit-all",
      "delete-container",
    ]);
    if (!operations.has(operation)) {
      throw new Error("container operation is invalid");
    }
    return encodeActionPayload([
      ["action", "container"],
      ["operation", operation],
    ]);
  }

  function buildChooseFilePayload() {
    return encodeActionPayload([["action", "choose-file"]]);
  }

  function normalizeDependencyCatalog(value) {
    if (!Array.isArray(value)) {
      return [];
    }
    const normalized = [];
    const seen = new Set();
    for (const dependency of value) {
      if (
        typeof dependency?.id !== "string" ||
        !/^[a-z0-9][a-z0-9-]{1,31}$/.test(dependency.id) ||
        seen.has(dependency.id) ||
        typeof dependency.name !== "string" ||
        !dependency.name ||
        typeof dependency.description !== "string" ||
        typeof dependency.publisher !== "string" ||
        !Number.isSafeInteger(dependency.size) ||
        dependency.size <= 0
      ) {
        continue;
      }
      seen.add(dependency.id);
      normalized.push({
        id: dependency.id,
        name: dependency.name,
        description: dependency.description,
        publisher: dependency.publisher,
        size: dependency.size,
      });
    }
    return normalized;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatByteSize(value) {
    if (!Number.isFinite(value) || value <= 0) {
      return "未知大小";
    }
    if (value >= 1024 * 1024) {
      return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${Math.ceil(value / 1024)} KB`;
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
      buildControlPanelMarkup,
      decideOverviewPatch,
      discoverManagedApps,
      findCompatForceToolAnchor,
      findAppActionComponents,
      findCompatControlAnchor,
      findManagedAppidForControls,
      getSelectedData,
      getSteamUIDocuments,
      getManagedTargetStatus,
      hideNativeCompatAnchor,
      isCompatibilityPropertiesDocument,
      isOwnedWindowsOnlyGame,
      buildControlPayload,
      buildControlUrl,
      buildActionUrl,
      buildChooseFilePayload,
      buildContainerActionPayload,
      buildDependencyPayload,
      buildJobUrl,
      buildRunCommandPayload,
      applyToolCapabilities,
      compatToolRecord,
      compatToolForRenderer,
      mergeCompatTools,
      normalizeControlConfig,
      normalizeDependencyCatalog,
      refreshAppActionComponents,
      reconcileCompatDetails,
      reconcileAppState,
      rendererForCompatTool,
      restoreNativeCompatAnchors,
      CONTROL_DEFAULTS,
      ACTION_POLL_INTERVAL_MS,
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
          ) &&
          typeof tool.capabilities === "object" &&
          tool.capabilities !== null,
      )
    : [];
  const projectCompatToolNames = new Set(
    projectCompatTools.map((tool) => tool.strToolName),
  );
  const dependencies = normalizeDependencyCatalog(
    config.dependencies,
  );
  const status = {
    version: 10,
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
    actionJobsStarted: 0,
    actionJobsCompleted: 0,
    actionJobsFailed: 0,
    actionLastError: null,
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
  const actionStates = new Map();
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
    const selectedTool =
      compatToolRecord(
        compatSelections.get(appid),
        projectCompatTools,
      ) ??
      projectCompatTools.find(
        (tool) => tool.renderer === renderer,
      ) ??
      null;
    const normalized = applyToolCapabilities(
      {
        ...stored,
        compat_tool: selectedTool?.strToolName ?? "",
        renderer,
      },
      selectedTool,
    );
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
    const responseValue = await response.json();
    const loadedTool =
      compatToolRecord(
        responseValue?.compat_tool,
        projectCompatTools,
      ) ??
      projectCompatTools.find(
        (tool) => tool.renderer === responseValue?.renderer,
      ) ??
      null;
    const loaded = applyToolCapabilities(
      responseValue,
      loadedTool,
    );
    controlConfigs.set(appid, loaded);
    const tool =
      loaded.compat_tool ||
      compatToolForRenderer(
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
    const selectedTool =
      compatToolRecord(value?.compat_tool, projectCompatTools) ??
      projectCompatTools.find(
        (tool) => tool.renderer === value?.renderer,
      ) ??
      null;
    const normalized = applyToolCapabilities(value, selectedTool);
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

  function actionStateFor(appid) {
    if (!actionStates.has(appid)) {
      actionStates.set(appid, {
        state: "idle",
        label: "",
        message: "等待操作",
        jobId: "",
        logPath: "",
      });
    }
    return actionStates.get(appid);
  }

  function setActionState(appid, value, panel = null) {
    actionStates.set(appid, {
      ...actionStateFor(appid),
      ...value,
    });
    if (panel) {
      panel.dataset.signature = "";
      renderControlPanel(panel, appid);
    }
  }

  async function startNativeAction(appid, payload) {
    const response = await globalObject.fetch(
      buildActionUrl(
        config.actionEndpoint,
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
    if (response?.ok !== true || typeof response.json !== "function") {
      throw new Error(
        `native action start failed for AppID ${appid}: ` +
          `${response?.status ?? "invalid response"}`,
      );
    }
    const value = await response.json();
    if (!ACTION_JOB_ID_PATTERN.test(String(value?.job_id ?? ""))) {
      throw new Error("native action response has an invalid job ID");
    }
    return value.job_id;
  }

  async function readNativeActionJob(appid, jobId) {
    const response = await globalObject.fetch(
      buildJobUrl(
        config.jobEndpoint,
        config.registryToken,
        appid,
        jobId,
      ),
      {
        method: "GET",
        mode: "cors",
        cache: "no-store",
      },
    );
    if (response?.status === 404) {
      return null;
    }
    if (response?.ok !== true || typeof response.json !== "function") {
      throw new Error(
        `native action status failed for AppID ${appid}: ` +
          `${response?.status ?? "invalid response"}`,
      );
    }
    const value = await response.json();
    if (
      value?.schema !== 1 ||
      value.appid !== appid ||
      value.job_id !== jobId ||
      !["running", "completed", "failed"].includes(value.state)
    ) {
      throw new Error("native action status response is invalid");
    }
    return value;
  }

  async function waitForNativeActionJob(appid, jobId) {
    for (let attempt = 0; attempt < ACTION_POLL_LIMIT; attempt += 1) {
      const value = await readNativeActionJob(appid, jobId);
      if (value && value.state !== "running") {
        return value;
      }
      await new Promise((resolve) =>
        globalObject.setTimeout(resolve, ACTION_POLL_INTERVAL_MS),
      );
    }
    throw new Error("native action timed out");
  }

  async function runNativeAction(appid, payload, label, panel) {
    if (actionStateFor(appid).state === "running") {
      return null;
    }
    setActionState(
      appid,
      {
        state: "running",
        label,
        message: "正在提交任务",
        jobId: "",
        logPath: "",
      },
      panel,
    );
    status.actionJobsStarted += 1;
    try {
      const jobId = await startNativeAction(appid, payload);
      setActionState(
        appid,
        {
          state: "running",
          message: "任务运行中",
          jobId,
        },
        panel,
      );
      const result = await waitForNativeActionJob(appid, jobId);
      const failed = result.state === "failed";
      setActionState(
        appid,
        {
          state: result.state,
          message: failed
            ? result.message || "任务执行失败"
            : "任务已完成",
          logPath: result.log_path || "",
        },
        panel,
      );
      if (failed) {
        status.actionJobsFailed += 1;
        status.actionLastError = result.message || "native action failed";
      } else {
        status.actionJobsCompleted += 1;
        status.actionLastError = null;
      }
      return result;
    } catch (error) {
      status.actionJobsFailed += 1;
      status.actionLastError = String(error);
      setActionState(
        appid,
        {
          state: "failed",
          message: String(error),
        },
        panel,
      );
      return null;
    }
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
          compat_tool: tool,
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

  function reactFiberForElement(element) {
    const fiberKey = Object.getOwnPropertyNames(element ?? {}).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    return fiberKey ? element[fiberKey] : null;
  }

  function collectManagedAppidsFromElements(
    elements,
    managedAppidSet,
  ) {
    const strong = new Set();
    const weak = new Set();
    const visitedFibers = new Set();
    let inspected = 0;
    for (const element of elements ?? []) {
      inspected += 1;
      if (inspected > 2500) {
        break;
      }
      let fiber = reactFiberForElement(element);
      for (let depth = 0; fiber && depth < 40; depth += 1) {
        if (visitedFibers.has(fiber)) {
          break;
        }
        visitedFibers.add(fiber);
        for (const props of [
          fiber.memoizedProps,
          fiber.pendingProps,
        ]) {
          const overviewAppid = Number(props?.overview?.appid);
          const detailsAppid = Number(props?.details?.unAppID);
          if (
            overviewAppid === detailsAppid &&
            managedAppidSet.has(overviewAppid)
          ) {
            strong.add(overviewAppid);
          }
          for (const candidate of [
            props?.appid,
            props?.unAppID,
            props?.overview?.appid,
            props?.details?.unAppID,
            props?.app?.appid,
            props?.app?.unAppID,
          ]) {
            const appid = Number(candidate);
            if (managedAppidSet.has(appid)) {
              weak.add(appid);
            }
          }
        }
        fiber = fiber.return;
      }
    }
    return { strong, weak };
  }

  function uniqueAppid(candidates) {
    return candidates.size === 1 ? [...candidates][0] : null;
  }

  function findManagedAppidForControls(
    documentObject,
    anchor,
    managedAppidSet,
  ) {
    const locationText = [
      documentObject?.location?.href,
      documentObject?.location?.hash,
    ]
      .filter((value) => typeof value === "string")
      .join(" ");
    for (const match of locationText.matchAll(/\d{3,10}/g)) {
      const appid = Number(match[0]);
      if (managedAppidSet.has(appid)) {
        return appid;
      }
    }

    const scopedElements = [
      anchor,
      ...(anchor?.querySelectorAll?.("*") ?? []),
    ].filter(Boolean);
    const scoped = collectManagedAppidsFromElements(
      scopedElements,
      managedAppidSet,
    );
    const scopedStrong = uniqueAppid(scoped.strong);
    if (scopedStrong) {
      return scopedStrong;
    }
    if (scoped.strong.size > 1) {
      return null;
    }
    const scopedWeak = uniqueAppid(scoped.weak);
    if (scopedWeak) {
      return scopedWeak;
    }

    const documentEvidence = collectManagedAppidsFromElements(
      documentObject?.querySelectorAll?.("*") ?? [],
      managedAppidSet,
    );
    return uniqueAppid(documentEvidence.strong);
  }

  function isCompatibilityPropertiesDocument(documentObject) {
    const bodyText = String(
      documentObject?.body?.innerText ??
        documentObject?.body?.textContent ??
        "",
    );
    const lines = bodyText
      .split(/\r?\n/)
      .map((line) => line.replace(/\s+/g, " ").trim())
      .filter(Boolean);
    const hasCompatibilityHeading = lines.some((line) =>
      /^(兼容性|Compatibility)$/i.test(line),
    );
    const hasForceToolText =
      /强制使用(?:特定)?\s*Steam Play\s*兼容性工具/i.test(bodyText) ||
      /Force the use of (?:a )?specific Steam Play compatibility tool/i.test(
        bodyText,
      );
    const title = String(documentObject?.title ?? "").trim();
    const locationText = [
      documentObject?.location?.href,
      documentObject?.location?.hash,
    ]
      .filter((value) => typeof value === "string")
      .join(" ");
    const hasPopupEvidence =
      Boolean(documentObject?.querySelector?.("[role=dialog]")) ||
      /(?:properties|app-properties|compatibility)/i.test(locationText) ||
      Boolean(title && title.toLowerCase() !== "steam");
    return (
      hasPopupEvidence &&
      hasCompatibilityHeading &&
      hasForceToolText
    );
  }

  function isProjectControlElement(element) {
    for (
      let current = element;
      current;
      current = current.parentElement
    ) {
      const className = String(current.className ?? "");
      if (
        className
          .split(/\s+/)
          .includes("realsteamonmac-controls")
      ) {
        return true;
      }
    }
    return false;
  }

  function normalizedElementText(element) {
    return String(element?.textContent ?? "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function isForceToolText(value) {
    return (
      /^强制使用(?:特定)?\s*Steam Play\s*兼容性工具$/i.test(value) ||
      /^Force the use of (?:a )?specific Steam Play compatibility tool$/i.test(
        value,
      )
    );
  }

  function containsForceToolText(value) {
    return (
      /强制使用(?:特定)?\s*Steam Play\s*兼容性工具/i.test(value) ||
      /Force the use of (?:a )?specific Steam Play compatibility tool/i.test(
        value,
      )
    );
  }

  function findForceToolAncestor(element) {
    let current = element;
    for (let depth = 0; current && depth < 5; depth += 1) {
      const text = normalizedElementText(current);
      if (text.length <= 800 && containsForceToolText(text)) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  function expandCompatAnchor(element, maxDepth, exactTextOnly = false) {
    let anchor = element;
    for (let depth = 0; depth < maxDepth; depth += 1) {
      const parent = anchor?.parentElement;
      const parentText = normalizedElementText(parent);
      if (
        !parent ||
        parent === parent.ownerDocument?.documentElement ||
        parent === parent.ownerDocument?.body ||
        parentText.length > 800 ||
        (exactTextOnly && !isForceToolText(parentText))
      ) {
        break;
      }
      anchor = parent;
    }
    return anchor;
  }

  function findCompatForceToolAnchor(documentObject) {
    let inspected = 0;
    const matches = [];
    const candidates =
      documentObject?.querySelectorAll?.("*") ?? [];
    for (const element of candidates) {
      inspected += 1;
      if (inspected > 2500) {
        break;
      }
      if (
        element === documentObject?.documentElement ||
        element === documentObject?.body ||
        isProjectControlElement(element) ||
        !isForceToolText(normalizedElementText(element))
      ) {
        continue;
      }
      matches.push(element);
    }
    const innermost = matches.filter(
      (candidate) =>
        !matches.some(
          (other) =>
            other !== candidate &&
            candidate.contains?.(other),
        ),
    );
    if (innermost.length !== 1) {
      return null;
    }
    return expandCompatAnchor(innermost[0], 4, true);
  }

  function findCompatControlAnchor(documentObject) {
    if (!isCompatibilityPropertiesDocument(documentObject)) {
      return null;
    }
    let inspected = 0;
    const matches = [];
    const candidates =
      documentObject?.querySelectorAll?.(
        "[role=combobox], select",
      ) ?? [];
    for (const element of candidates) {
      inspected += 1;
      if (inspected > 250) {
        return null;
      }
      if (
        element === documentObject?.documentElement ||
        element === documentObject?.body ||
        isProjectControlElement(element)
      ) {
        continue;
      }
      const text = String(element?.textContent ?? "").trim();
      if (!text || text.length > 240) {
        continue;
      }
      matches.push(element);
    }
    if (matches.length === 1) {
      return (
        findForceToolAncestor(matches[0]) ??
        expandCompatAnchor(matches[0], 3)
      );
    }
    return findCompatForceToolAnchor(documentObject);
  }

  function hideNativeCompatAnchor(anchor) {
    if (
      !anchor?.style ||
      isProjectControlElement(anchor) ||
      anchor.dataset?.realsteamonmacNativeHidden === "true"
    ) {
      return;
    }
    anchor.dataset.realsteamonmacNativeHidden = "true";
    anchor.dataset.realsteamonmacOriginalDisplay =
      anchor.style.display ?? "";
    anchor.style.display = "none";
  }

  function restoreNativeCompatAnchors(documentObject) {
    const anchors =
      documentObject?.querySelectorAll?.(
        '[data-realsteamonmac-native-hidden="true"]',
      ) ?? [];
    for (const anchor of anchors) {
      if (!anchor?.style) {
        continue;
      }
      anchor.style.display =
        anchor.dataset?.realsteamonmacOriginalDisplay ?? "";
      delete anchor.dataset?.realsteamonmacNativeHidden;
      delete anchor.dataset?.realsteamonmacOriginalDisplay;
    }
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
        width: min(100%, 760px);
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
      .realsteamonmac-tools {
        margin-top: 16px;
        padding-top: 15px;
        border-top: 1px solid rgba(102,192,244,.22);
      }
      .realsteamonmac-tools__head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 10px;
      }
      .realsteamonmac-tools__title {
        font-size: 14px;
        font-weight: 800;
      }
      .realsteamonmac-tools__copy {
        margin-top: 3px;
        color: var(--rsm-muted);
        font-size: 11px;
        line-height: 1.35;
      }
      .realsteamonmac-tools__badge {
        padding: 4px 7px;
        color: var(--rsm-cyan);
        background: rgba(102,192,244,.08);
        border: 1px solid rgba(102,192,244,.3);
        border-radius: 2px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .08em;
        white-space: nowrap;
      }
      .realsteamonmac-field {
        display: flex;
        flex-direction: column;
        gap: 5px;
        margin-top: 8px;
      }
      .realsteamonmac-field__label {
        color: #dce8f3;
        font-size: 11px;
        font-weight: 700;
      }
      .realsteamonmac-field input,
      .realsteamonmac-field textarea,
      .realsteamonmac-dependencies__search {
        width: 100%;
        color: var(--rsm-text);
        background: #0c141d;
        border: 1px solid #3d4f5f;
        border-radius: 2px;
        outline: none;
        font: 12px/1.4 "SFMono-Regular", Consolas, monospace;
      }
      .realsteamonmac-field input,
      .realsteamonmac-dependencies__search {
        height: 34px;
        padding: 0 9px;
      }
      .realsteamonmac-field textarea {
        min-height: 58px;
        padding: 8px 9px;
        resize: vertical;
      }
      .realsteamonmac-field input:focus,
      .realsteamonmac-field textarea:focus,
      .realsteamonmac-dependencies__search:focus {
        border-color: var(--rsm-blue);
        box-shadow: 0 0 0 1px rgba(26,159,255,.25);
      }
      .realsteamonmac-run__grid {
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(0, .8fr);
        gap: 10px;
      }
      .realsteamonmac-button {
        min-width: 112px;
        height: 34px;
        padding: 0 13px;
        color: #07121c;
        background: linear-gradient(180deg, #67c1f5, #1a9fff);
        border: 0;
        border-radius: 2px;
        font-size: 12px;
        font-weight: 800;
        cursor: pointer;
      }
      .realsteamonmac-button:hover:not(:disabled) {
        filter: brightness(1.1);
      }
      .realsteamonmac-button:disabled {
        cursor: wait;
        filter: saturate(.3);
        opacity: .55;
      }
      .realsteamonmac-run__actions {
        display: flex;
        justify-content: flex-end;
        margin-top: 10px;
      }
      .realsteamonmac-dependencies__search {
        margin-bottom: 9px;
      }
      .realsteamonmac-dependencies__list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
      }
      .realsteamonmac-dependency {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: 10px;
        min-height: 76px;
        padding: 10px;
        background: rgba(5,12,18,.38);
        border: 1px solid rgba(158,177,194,.15);
        border-radius: 3px;
      }
      .realsteamonmac-dependency[hidden] { display: none; }
      .realsteamonmac-dependency__name {
        font-size: 12px;
        font-weight: 800;
      }
      .realsteamonmac-dependency__meta {
        margin-top: 3px;
        color: var(--rsm-cyan);
        font-size: 10px;
      }
      .realsteamonmac-dependency__description {
        margin-top: 4px;
        color: var(--rsm-muted);
        font-size: 10px;
        line-height: 1.3;
      }
      .realsteamonmac-dependency .realsteamonmac-button {
        min-width: 68px;
      }
      .realsteamonmac-action-status {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 7px 10px;
        align-items: center;
        margin-top: 12px;
        padding: 9px 10px;
        color: var(--rsm-muted);
        background: rgba(7,14,21,.62);
        border: 1px solid rgba(158,177,194,.16);
        border-radius: 3px;
        font-size: 11px;
      }
      .realsteamonmac-action-status__lamp {
        width: 8px;
        height: 8px;
        background: #70808e;
        border-radius: 50%;
      }
      .realsteamonmac-action-status[data-state="running"]
        .realsteamonmac-action-status__lamp {
        background: #f2c94c;
        box-shadow: 0 0 0 4px rgba(242,201,76,.1);
      }
      .realsteamonmac-action-status[data-state="completed"]
        .realsteamonmac-action-status__lamp {
        background: #75d17e;
      }
      .realsteamonmac-action-status[data-state="failed"]
        .realsteamonmac-action-status__lamp {
        background: #ff7b72;
      }
      .realsteamonmac-action-status__log {
        grid-column: 2;
        overflow: hidden;
        color: #7890a3;
        font: 10px/1.3 "SFMono-Regular", Consolas, monospace;
        text-overflow: ellipsis;
        white-space: nowrap;
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
      .realsteamonmac-controls {
        margin: 12px 0 2px;
        padding: 0;
        width: 100%;
        max-width: none;
        background: transparent;
        border: 0;
        border-radius: 0;
        box-shadow: none;
      }
      .realsteamonmac-settings {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
        color: #dcdedf;
        font-family: "Motiva Sans", "Noto Sans SC", sans-serif;
      }
      .realsteamonmac-force-tool {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 14px;
        background: #25282e;
        border-radius: 3px;
      }
      .realsteamonmac-force-tool__check {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #f0f1f1;
        font-size: 14px;
        cursor: pointer;
      }
      .realsteamonmac-force-tool__check input {
        width: 18px;
        height: 18px;
        margin: 0;
        accent-color: #1a9fff;
      }
      .realsteamonmac-force-tool select {
        width: 100%;
        min-height: 38px;
        padding: 0 38px 0 12px;
        color: #f0f1f1;
        background: #3d4450;
        border: 0;
        border-radius: 2px;
        outline: none;
        font: 13px "Motiva Sans", "Noto Sans SC", sans-serif;
      }
      .realsteamonmac-force-tool select:hover:not(:disabled) {
        background: #4e5968;
      }
      .realsteamonmac-force-tool select:disabled {
        color: #8b929a;
        opacity: .55;
      }
      .realsteamonmac-settings__heading {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 34px;
        color: #8b929a;
        font-size: 13px;
        font-weight: 600;
      }
      .realsteamonmac-settings__renderer {
        color: #66c0f4;
        font-size: 12px;
        font-weight: 500;
      }
      .realsteamonmac-settings__rows {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .realsteamonmac-setting-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        min-height: 54px;
        padding: 8px 14px;
        background: #25282e;
        cursor: pointer;
      }
      .realsteamonmac-setting-row:first-child {
        border-radius: 3px 3px 0 0;
      }
      .realsteamonmac-setting-row:last-child {
        border-radius: 0 0 3px 3px;
      }
      .realsteamonmac-setting-row:hover {
        background: #2d3138;
      }
      .realsteamonmac-setting-row[data-disabled="true"] {
        opacity: .42;
        cursor: not-allowed;
      }
      .realsteamonmac-setting-row__copy {
        display: flex;
        flex: 1;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
      }
      .realsteamonmac-setting-row__label {
        color: #f0f1f1;
        font-size: 14px;
      }
      .realsteamonmac-setting-row__hint {
        overflow: hidden;
        color: #8b929a;
        font-size: 11px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .realsteamonmac-switch {
        position: relative;
        flex: 0 0 auto;
        width: 42px;
        height: 24px;
      }
      .realsteamonmac-switch input {
        position: absolute;
        width: 1px;
        height: 1px;
        opacity: 0;
        pointer-events: none;
      }
      .realsteamonmac-switch__track {
        position: absolute;
        inset: 0;
        background: #4a4d52;
        border-radius: 14px;
        transition: background .12s ease;
      }
      .realsteamonmac-switch__track::after {
        position: absolute;
        top: 3px;
        left: 3px;
        width: 18px;
        height: 18px;
        background: #dfe3e6;
        border-radius: 50%;
        content: "";
        transition: transform .12s ease;
      }
      .realsteamonmac-switch input:checked + .realsteamonmac-switch__track {
        background: #1a9fff;
      }
      .realsteamonmac-switch input:checked +
        .realsteamonmac-switch__track::after {
        transform: translateX(18px);
      }
      .realsteamonmac-switch input:focus-visible +
        .realsteamonmac-switch__track {
        box-shadow: 0 0 0 2px rgba(102,192,244,.55);
      }
      .realsteamonmac-settings__actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding-top: 4px;
      }
      .realsteamonmac-native-button {
        min-height: 34px;
        padding: 0 16px;
        color: #dfe3e6;
        background: #3d4450;
        border: 0;
        border-radius: 2px;
        font: 13px "Motiva Sans", "Noto Sans SC", sans-serif;
        cursor: pointer;
      }
      .realsteamonmac-native-button:hover:not(:disabled) {
        color: #fff;
        background: #4e5968;
      }
      .realsteamonmac-native-button.primary {
        color: #fff;
        background: linear-gradient(90deg, #06bfff, #2d73ff);
      }
      .realsteamonmac-native-button:disabled {
        opacity: .45;
        cursor: wait;
      }
      .realsteamonmac-settings__status {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        color: #8b929a;
        font-size: 11px;
      }
      .realsteamonmac-settings__status[data-state="completed"] {
        color: #75d17e;
      }
      .realsteamonmac-settings__status[data-state="failed"] {
        color: #ff7b72;
      }
      .realsteamonmac-modal-layer {
        position: fixed;
        z-index: 100000;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        background: rgba(0,0,0,.62);
      }
      .realsteamonmac-modal {
        display: flex;
        flex-direction: column;
        width: min(680px, calc(100vw - 48px));
        max-height: min(760px, calc(100vh - 48px));
        color: #dcdedf;
        background: #24282f;
        border: 1px solid #434953;
        border-radius: 3px;
        box-shadow: 0 18px 70px rgba(0,0,0,.56);
        font-family: "Motiva Sans", "Noto Sans SC", sans-serif;
      }
      .realsteamonmac-modal__title {
        padding: 18px 20px 14px;
        color: #f3f3f3;
        font-size: 20px;
        font-weight: 500;
      }
      .realsteamonmac-modal__body {
        overflow: auto;
        padding: 4px 20px 18px;
      }
      .realsteamonmac-modal__field {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-top: 12px;
        color: #b8bcbf;
        font-size: 12px;
      }
      .realsteamonmac-modal__field input,
      .realsteamonmac-modal__field textarea,
      .realsteamonmac-modal__search {
        width: 100%;
        padding: 9px 10px;
        color: #f2f2f2;
        background: #1b1e23;
        border: 1px solid #3b414a;
        border-radius: 2px;
        outline: none;
        font: 13px "Motiva Sans", "Noto Sans SC", sans-serif;
      }
      .realsteamonmac-modal__field textarea {
        min-height: 78px;
        resize: vertical;
      }
      .realsteamonmac-modal__browse-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 8px;
      }
      .realsteamonmac-modal__check {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 14px;
        font-size: 13px;
      }
      .realsteamonmac-modal__actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding: 14px 20px 18px;
      }
      .realsteamonmac-modal__dependency-list,
      .realsteamonmac-modal__menu {
        display: flex;
        flex-direction: column;
        gap: 2px;
        margin-top: 10px;
      }
      .realsteamonmac-modal__dependency {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: #2b2f36;
      }
      .realsteamonmac-modal__dependency[hidden] {
        display: none;
      }
      .realsteamonmac-modal__dependency span {
        display: flex;
        flex-direction: column;
        gap: 3px;
      }
      .realsteamonmac-modal__dependency small {
        color: #9299a1;
      }
      .realsteamonmac-modal__menu button {
        min-height: 46px;
        padding: 0 14px;
        color: #e6e7e8;
        text-align: left;
        background: #2b2f36;
        border: 0;
        cursor: pointer;
      }
      .realsteamonmac-modal__menu button:hover {
        background: #343a43;
      }
      .realsteamonmac-modal__menu button.danger {
        color: #ff7b72;
      }
      @media (max-width: 640px) {
        .realsteamonmac-controls__grid,
        .realsteamonmac-run__grid,
        .realsteamonmac-dependencies__list {
          grid-template-columns: 1fr;
        }
      }
    `;
    documentObject.head.appendChild(style);
  }

  function controlDefinitions(tool) {
    const capabilities = tool?.capabilities ?? {};
    return [
      {
        key: "msync",
        label: "启用 MSync",
        hint: "降低 Wine 同步开销，默认开启",
        enabled: capabilities.msync === true,
      },
      {
        key: "retina",
        label: "高分辨率模式",
        hint: "写入当前 PFX 的 Wine RetinaMode",
        enabled: capabilities.retina === true,
      },
      {
        key: "metal_hud",
        label: "Metal HUD",
        hint: "显示 Metal 图形性能叠加层",
        enabled: capabilities.metal_hud === true,
      },
      {
        key: "metalfx",
        label: "DLSS 转 MetalFX",
        hint: "将受支持的 DLSS 超分辨率请求映射到 MetalFX",
        enabled: capabilities.metalfx === true,
      },
      {
        key: "dxr",
        label: "DXR",
        hint: "向游戏公开 GPTK 光线追踪能力",
        enabled: capabilities.dxr === true,
      },
      {
        key: "avx",
        label: "Rosetta AVX",
        hint: "为需要 AVX 的游戏公开指令能力",
        enabled: capabilities.avx === true,
      },
    ];
  }

  function buildControlPanelMarkup({
    appid,
    value,
    rendererLabel,
    tool,
    compatTools = [],
    selectedCompatTool = "",
    actionState,
  }) {
    const normalized = applyToolCapabilities(value, tool);
    const definitions = controlDefinitions(tool);
    const running = actionState?.state === "running";
    const compatEnabled = Boolean(selectedCompatTool);
    const effectiveTool =
      selectedCompatTool || normalized.compat_tool || tool?.strToolName || "";
    return `
      <div class="realsteamonmac-settings"
           data-compat-enabled="${compatEnabled ? "true" : "false"}">
        <div class="realsteamonmac-force-tool">
          <label class="realsteamonmac-force-tool__check">
            <input type="checkbox"
                   data-control-force-compat
                   ${compatEnabled ? "checked" : ""}>
            <span>强制使用特定 Steam Play 兼容性工具</span>
          </label>
          <select data-control-compat-tool
                  ${compatEnabled ? "" : "disabled"}>
            ${compatTools
              .map(
                (candidate) => `
                  <option value="${escapeHtml(candidate.strToolName)}"
                          ${candidate.strToolName === effectiveTool ? "selected" : ""}>
                    ${escapeHtml(
                      candidate.strDisplayName.replace(
                        /^RealSteamOnMac\s*-\s*/i,
                        "",
                      ),
                    )}
                  </option>
                `,
              )
              .join("")}
          </select>
        </div>
        <div class="realsteamonmac-settings__heading">
          <span>兼容性选项</span>
          <span class="realsteamonmac-settings__renderer">${escapeHtml(rendererLabel)}</span>
        </div>
        <div class="realsteamonmac-settings__rows">
          ${definitions
            .map(
              (definition) => `
                <label class="realsteamonmac-setting-row"
                       data-disabled="${definition.enabled ? "false" : "true"}">
                  <span class="realsteamonmac-setting-row__copy">
                    <span class="realsteamonmac-setting-row__label">${escapeHtml(definition.label)}</span>
                    <span class="realsteamonmac-setting-row__hint">${escapeHtml(definition.hint)}</span>
                  </span>
                  <span class="realsteamonmac-switch">
                    <input type="checkbox"
                           role="switch"
                           data-control="${definition.key}"
                           ${normalized[definition.key] ? "checked" : ""}
                           ${definition.enabled && compatEnabled ? "" : "disabled"}>
                    <span class="realsteamonmac-switch__track"></span>
                  </span>
                </label>
              `,
            )
            .join("")}
        </div>
        <div class="realsteamonmac-settings__actions">
          <button type="button"
                  class="realsteamonmac-native-button"
                  data-open-dialog="run-command"
                  ${running || !compatEnabled ? "disabled" : ""}>运行命令</button>
          <button type="button"
                  class="realsteamonmac-native-button"
                  data-open-dialog="dependencies"
                  ${running || !compatEnabled ? "disabled" : ""}>安装 Windows 组件</button>
          <button type="button"
                  class="realsteamonmac-native-button"
                  data-open-dialog="container"
                  ${running || !compatEnabled ? "disabled" : ""}>容器操作</button>
        </div>
        <div class="realsteamonmac-settings__status"
             data-state="${escapeHtml(actionState?.state ?? "idle")}">
          <span class="realsteamonmac-settings__status-text">${escapeHtml(
            actionState?.message ?? "已保存",
          )}</span>
          <span>AppID ${appid}</span>
        </div>
      </div>
    `;
  }

  function buildActionDialogMarkup(kind) {
    if (kind === "run-command") {
      return `
        <div class="realsteamonmac-modal__title">运行命令</div>
        <div class="realsteamonmac-modal__body">
          <label class="realsteamonmac-modal__field">
            <span>命令</span>
            <span class="realsteamonmac-modal__browse-row">
              <input type="text" data-run-target
                     placeholder="C:\\windows\\system32\\reg.exe">
              <button type="button" class="realsteamonmac-native-button"
                      data-browse-target>浏览...</button>
            </span>
          </label>
          <label class="realsteamonmac-modal__field">
            <span>参数</span>
            <textarea data-run-arguments
                      placeholder='query "HKCU\\Software\\Wine"'></textarea>
          </label>
          <label class="realsteamonmac-modal__field">
            <span>环境变量 · 每行 NAME=VALUE</span>
            <textarea data-run-environment
                      placeholder="DXVK_HUD=fps"></textarea>
          </label>
          <label class="realsteamonmac-modal__check">
            <input type="checkbox" data-create-log>
            <span>创建日志文件</span>
          </label>
        </div>
        <div class="realsteamonmac-modal__actions">
          <button type="button" class="realsteamonmac-native-button"
                  data-close-dialog>取消</button>
          <button type="button" class="realsteamonmac-native-button primary"
                  data-submit-run>运行</button>
        </div>
      `;
    }
    if (kind === "dependencies") {
      return `
        <div class="realsteamonmac-modal__title">安装 Windows 组件</div>
        <div class="realsteamonmac-modal__body">
          <input type="search"
                 class="realsteamonmac-modal__search"
                 data-dependency-search
                 placeholder="搜索 C++、.NET、字体或发布者">
          <div class="realsteamonmac-modal__dependency-list">
            ${dependencies
              .map(
                (dependency) => `
                  <article class="realsteamonmac-modal__dependency"
                           data-dependency-card
                           data-search="${escapeHtml(
                             `${dependency.name} ${dependency.description} ${dependency.publisher}`.toLowerCase(),
                           )}">
                    <span>
                      <strong>${escapeHtml(dependency.name)}</strong>
                      <small>${escapeHtml(dependency.publisher)} · ${formatByteSize(dependency.size)}</small>
                      <small>${escapeHtml(dependency.description)}</small>
                    </span>
                    <button type="button"
                            class="realsteamonmac-native-button primary"
                            data-install-dependency="${escapeHtml(dependency.id)}">安装</button>
                  </article>
                `,
              )
              .join("")}
          </div>
        </div>
        <div class="realsteamonmac-modal__actions">
          <button type="button" class="realsteamonmac-native-button"
                  data-close-dialog>关闭</button>
        </div>
      `;
    }
    return `
      <div class="realsteamonmac-modal__title">容器操作</div>
      <div class="realsteamonmac-modal__body">
        <div class="realsteamonmac-modal__menu">
          <button type="button" data-container-action="open-c-drive">打开 C: 盘</button>
          <button type="button" data-container-action="install-application">安装应用程序到容器</button>
          <button type="button" data-container-action="wine-configuration">Wine 配置</button>
          <button type="button" data-container-action="controllers">Game Controllers</button>
          <button type="button" data-container-action="restart">模拟重启</button>
          <button type="button" data-container-action="task-manager">任务管理器</button>
          <button type="button" data-container-action="quit-all">退出所有应用程序</button>
          <button type="button" class="danger" data-container-action="delete-container">删除容器</button>
        </div>
      </div>
      <div class="realsteamonmac-modal__actions">
        <button type="button" class="realsteamonmac-native-button"
                data-close-dialog>关闭</button>
      </div>
    `;
  }

  function openActionDialog(documentObject, panel, appid, kind) {
    documentObject
      .querySelector?.(".realsteamonmac-modal-layer")
      ?.remove?.();
    const layer = documentObject.createElement("div");
    layer.className = "realsteamonmac-modal-layer";
    layer.innerHTML = `
      <div class="realsteamonmac-modal" role="dialog" aria-modal="true">
        ${buildActionDialogMarkup(kind)}
      </div>
    `;
    documentObject.body.appendChild(layer);
    const onKeydown = (event) => {
      if (event.key === "Escape") {
        close();
      }
    };
    const close = () => {
      documentObject.removeEventListener?.(
        "keydown",
        onKeydown,
        true,
      );
      layer.remove();
    };
    documentObject.addEventListener?.("keydown", onKeydown, true);
    layer.addEventListener("click", (event) => {
      if (event.target === layer) {
        close();
      }
    });
    layer
      .querySelector("[data-close-dialog]")
      ?.addEventListener("click", close);

    if (kind === "run-command") {
      layer
        .querySelector("[data-browse-target]")
        ?.addEventListener("click", () => {
          void (async () => {
            const result = await runNativeAction(
              appid,
              buildChooseFilePayload(),
              "选择可执行文件",
              panel,
            );
            const target = result?.result?.target;
            if (typeof target === "string" && target) {
              const input = layer.querySelector("[data-run-target]");
              if (input) {
                input.value = target;
              }
            }
          })();
        });
      layer
        .querySelector("[data-submit-run]")
        ?.addEventListener("click", () => {
          const target =
            layer.querySelector("[data-run-target]")?.value ?? "";
          const commandArguments =
            layer.querySelector("[data-run-arguments]")?.value ?? "";
          const environment =
            layer.querySelector("[data-run-environment]")?.value ?? "";
          close();
          void runNativeAction(
            appid,
            buildRunCommandPayload({
              target,
              arguments: commandArguments,
              environment,
            }),
            "运行命令",
            panel,
          );
        });
      return;
    }

    if (kind === "dependencies") {
      for (const button of layer.querySelectorAll(
        "[data-install-dependency]",
      )) {
        button.addEventListener("click", () => {
          const dependencyId = button.dataset.installDependency;
          const dependency = dependencies.find(
            (candidate) => candidate.id === dependencyId,
          );
          if (!dependency) {
            return;
          }
          close();
          void runNativeAction(
            appid,
            buildDependencyPayload(dependency.id),
            `安装 ${dependency.name}`,
            panel,
          );
        });
      }
      const search = layer.querySelector(
        "[data-dependency-search]",
      );
      search?.addEventListener("input", () => {
        const query = search.value.trim().toLowerCase();
        for (const card of layer.querySelectorAll(
          "[data-dependency-card]",
        )) {
          card.hidden =
            Boolean(query) &&
            !String(card.dataset.search ?? "").includes(query);
        }
      });
      return;
    }

    for (const button of layer.querySelectorAll(
      "[data-container-action]",
    )) {
      button.addEventListener("click", () => {
        const operation = button.dataset.containerAction;
        close();
        void runNativeAction(
          appid,
          buildContainerActionPayload(operation),
          button.textContent?.trim() || "容器操作",
          panel,
        );
      });
    }
  }

  function renderControlPanel(panel, appid) {
    const value = ensureControlConfig(appid);
    const actionState = actionStateFor(appid);
    const selectedCompatTool = compatSelections.get(appid) ?? "";
    const selectedTool =
      compatToolRecord(value.compat_tool, projectCompatTools) ??
      projectCompatTools.find(
        (tool) => tool.renderer === value.renderer,
      ) ??
      null;
    const rendererLabel =
      selectedTool?.strDisplayName?.replace(
        /^RealSteamOnMac\s*-\s*/i,
        "",
      ) ?? value.renderer.toUpperCase();
    const signature = JSON.stringify({
      value,
      actionState,
      selectedCompatTool,
    });
    if (panel.dataset.signature === signature) {
      return;
    }
    panel.dataset.signature = signature;
    panel.dataset.appid = String(appid);
    panel.innerHTML = buildControlPanelMarkup({
      appid,
      value,
      rendererLabel,
      tool: selectedTool,
      compatTools: projectCompatTools,
      selectedCompatTool,
      actionState,
    });

    const statusElement = panel.querySelector(
      ".realsteamonmac-settings__status-text",
    );
    const forceCompatInput = panel.querySelector(
      "[data-control-force-compat]",
    );
    const compatToolSelect = panel.querySelector(
      "[data-control-compat-tool]",
    );
    const selectCompatTool = async (toolName) => {
      statusElement.textContent = "保存中";
      statusElement.dataset.state = "saving";
      try {
        await globalObject.SteamClient.Apps.SpecifyCompatTool(
          appid,
          toolName,
        );
        panel.dataset.signature = "";
        renderControlPanel(panel, appid);
      } catch (error) {
        status.controlLastError = String(error);
        panel.dataset.signature = "";
        renderControlPanel(panel, appid);
      }
    };
    forceCompatInput?.addEventListener("change", () => {
      const fallbackTool =
        compatToolSelect?.value ||
        value.compat_tool ||
        config.defaultCompatTool ||
        projectCompatTools[0]?.strToolName ||
        "";
      void selectCompatTool(
        forceCompatInput.checked ? fallbackTool : "",
      );
    });
    compatToolSelect?.addEventListener("change", () => {
      void selectCompatTool(compatToolSelect.value);
    });
    for (const input of panel.querySelectorAll("input[data-control]")) {
      input.addEventListener("change", async () => {
        const key = input.dataset.control;
        const previous = ensureControlConfig(appid);
        const next = applyToolCapabilities(
          {
            ...previous,
            [key]: input.checked,
          },
          selectedTool,
        );
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
        }
      });
    }

    for (const button of panel.querySelectorAll(
      "[data-open-dialog]",
    )) {
      button.addEventListener("click", () => {
        openActionDialog(
          panel.ownerDocument,
          panel,
          appid,
          button.dataset.openDialog,
        );
      });
    }
  }

  function mountControlPanels() {
    let mounted = 0;
    for (const documentObject of getSteamUIDocuments(globalObject)) {
      const existing = documentObject.querySelector?.(
        ".realsteamonmac-controls",
      );
      const anchor = findCompatControlAnchor(documentObject);
      const appid = anchor
        ? findManagedAppidForControls(
            documentObject,
            anchor,
            managedAppids,
          )
        : null;
      if (!appid) {
        existing?.remove?.();
        restoreNativeCompatAnchors(documentObject);
        continue;
      }
      if (!anchor?.parentElement) {
        continue;
      }
      hideNativeCompatAnchor(anchor);
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
