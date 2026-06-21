(function initializeRealSteamOnMacUI(globalObject) {
  "use strict";

  const INVALID_PLATFORM = 14;
  const READY_TO_INSTALL = 9;
  const READY_TO_LAUNCH = 11;
  const VALID_DISPLAY_STATUSES = new Set(
    Array.from({ length: 39 }, (_, index) => index + 1).filter(
      (status) =>
        status !== INVALID_PLATFORM &&
        status !== 15,
    ),
  );
  const STATUS_KEY = "__REALSTEAMONMAC_UI_STATUS__";
  const CONFIG_KEY = "__REALSTEAMONMAC_CONFIG__";
  const MANAGED_PREDICATE_KEY =
    "__REALSTEAMONMAC_IS_MANAGED_APP__";
  const SELECTED_COMPAT_TOOL_KEY =
    "__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__";
  const REPAIR_ACTION_KEY =
    "__REALSTEAMONMAC_REQUEST_REPAIR__";
  const NATIVE_COMPAT_RENDER_KEY =
    "__REALSTEAMONMAC_RENDER_NATIVE_COMPAT_CONTROLS__";
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
  const MANIFEST_INSTALL_DIAGNOSTICS = new Set([
    "manifest-missing",
    "install-directory-missing",
    "not-installed",
  ]);
  const MANIFEST_RESUME_DIAGNOSTICS = new Set([
    "download-incomplete",
  ]);
  const MANIFEST_VERIFY_DIAGNOSTICS = new Set([
    "repair-required",
    "state-blocked",
    "manifest-invalid",
  ]);
  const MANIFEST_STALE_SHELL_DIAGNOSTICS = new Set([
    "content-missing",
    "installed-depots-missing",
  ]);

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
    if (!tool) {
      return normalized;
    }
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

  function buildShortcutControlUrl(endpoint, token, appid) {
    const canonicalAppid = canonicalizePositiveUint32(appid);
    if (
      typeof endpoint !== "string" ||
      !endpoint ||
      typeof token !== "string" ||
      !token ||
      canonicalAppid === null
    ) {
      throw new Error("native control endpoint is unavailable");
    }
    return (
      `${endpoint}?token=${encodeURIComponent(token)}` +
      `&kind=shortcut&id=${canonicalAppid}`
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

  function buildInspectStatePayload() {
    return encodeActionPayload([["action", "inspect-state"]]);
  }

  function canonicalizePositiveUint32(value) {
    if (typeof value === "number") {
      return Number.isInteger(value) &&
        value > 0 &&
        value <= 0xFFFFFFFF
        ? String(value)
        : null;
    }
    if (typeof value === "string" && /^[1-9][0-9]{0,9}$/.test(value)) {
      const numeric = Number(value);
      return Number.isInteger(numeric) &&
        numeric > 0 &&
        numeric <= 0xFFFFFFFF
        ? String(numeric)
        : null;
    }
    return null;
  }

  function encodeAllUtf8Bytes(value) {
    let encoded = "";
    for (const character of String(value)) {
      const codepoint = character.codePointAt(0);
      const bytes =
        codepoint <= 0x7F
          ? [codepoint]
          : codepoint <= 0x7FF
            ? [
                0xC0 | (codepoint >> 6),
                0x80 | (codepoint & 0x3F),
              ]
            : codepoint <= 0xFFFF
              ? [
                  0xE0 | (codepoint >> 12),
                  0x80 | ((codepoint >> 6) & 0x3F),
                  0x80 | (codepoint & 0x3F),
                ]
              : [
                  0xF0 | (codepoint >> 18),
                  0x80 | ((codepoint >> 12) & 0x3F),
                  0x80 | ((codepoint >> 6) & 0x3F),
                  0x80 | (codepoint & 0x3F),
                ];
      for (const byte of bytes) {
        encoded += `%${byte.toString(16).toUpperCase().padStart(2, "0")}`;
      }
    }
    return encoded;
  }

  function isWellFormedUnicode(value) {
    for (let index = 0; index < value.length; index += 1) {
      const unit = value.charCodeAt(index);
      if (unit >= 0xD800 && unit <= 0xDBFF) {
        const next = value.charCodeAt(index + 1);
        if (!(next >= 0xDC00 && next <= 0xDFFF)) {
          return false;
        }
        index += 1;
      } else if (unit >= 0xDC00 && unit <= 0xDFFF) {
        return false;
      }
    }
    return true;
  }

  function normalizeShortcutTargetCandidate(value) {
    if (typeof value !== "string" || !value) {
      return null;
    }
    if (
      /[\u0000-\u001F\u007F]/.test(value) ||
      !isWellFormedUnicode(value)
    ) {
      return null;
    }

    let target = value;
    if (target.startsWith('"') && target.endsWith('"')) {
      target = target.slice(1, -1);
      if (target.startsWith('"') || target.endsWith('"')) {
        return null;
      }
    }
    if (
      !target ||
      /[\u0000-\u001F\u007F]/.test(target) ||
      !isWellFormedUnicode(target)
    ) {
      return null;
    }

    const lastSlash = Math.max(
      target.lastIndexOf("/"),
      target.lastIndexOf("\\"),
    );
    const basename =
      lastSlash >= 0 ? target.slice(lastSlash + 1) : target;
    if (!basename || !/\.exe$/i.test(basename)) {
      return null;
    }
    if (target.startsWith("/") && !target.startsWith("//")) {
      return target;
    }
    return null;
  }

  function isManagedShortcut(overview, details) {
    const overviewAppid = canonicalizePositiveUint32(overview?.appid);
    return (
      overview?.app_type === 0x40000000 &&
      overview?.visible_in_game_list === true &&
      overviewAppid !== null &&
      canonicalizePositiveUint32(details?.unAppID) === overviewAppid &&
      normalizeShortcutTargetCandidate(details?.strShortcutExe) !== null
    );
  }

  function buildManagedRegistryBody({ apps, shortcuts } = {}) {
    const seen = new Set();
    const storeAppids = [];
    const shortcutEntries = [];

    for (const appid of apps ?? []) {
      const canonicalAppid = canonicalizePositiveUint32(appid);
      if (canonicalAppid === null) {
        throw new Error("managed registry app ID is invalid");
      }
      if (seen.has(canonicalAppid)) {
        throw new Error("managed registry app ID is duplicated");
      }
      seen.add(canonicalAppid);
      storeAppids.push(canonicalAppid);
    }

    for (const [appid, target] of shortcuts ?? []) {
      const canonicalAppid = canonicalizePositiveUint32(appid);
      if (canonicalAppid === null) {
        throw new Error("managed registry shortcut ID is invalid");
      }
      if (seen.has(canonicalAppid)) {
        throw new Error("managed registry collision for AppID");
      }
      seen.add(canonicalAppid);
      const normalizedTarget = normalizeShortcutTargetCandidate(target);
      if (normalizedTarget === null) {
        throw new Error("managed registry shortcut target is invalid");
      }
      shortcutEntries.push([
        Number(canonicalAppid),
        canonicalAppid,
        normalizedTarget,
      ]);
    }

    if (shortcutEntries.length > 64) {
      throw new Error("managed registry shortcut capacity exceeded");
    }
    if (storeAppids.length + shortcutEntries.length > 256) {
      throw new Error("managed registry capacity exceeded");
    }

    storeAppids.sort((left, right) => Number(left) - Number(right));
    shortcutEntries.sort((left, right) => left[0] - right[0]);

    let body = "RSMREG\t1\n";
    for (const appid of storeAppids) {
      body += `A\t${appid}\n`;
    }
    for (const [, canonicalAppid, target] of shortcutEntries) {
      body += `S\t${canonicalAppid}\t${encodeAllUtf8Bytes(target)}\n`;
    }

    if (body.length >= 16384) {
      throw new Error("managed registry body capacity exceeded");
    }
    return body;
  }

  function managedIdentityStorageKey(kind, appid, target = "") {
    const canonicalAppid = canonicalizePositiveUint32(appid);
    if (canonicalAppid === null) {
      throw new Error("managed identity ID is invalid");
    }
    if (kind === "store") {
      return `store:${canonicalAppid}`;
    }
    if (kind !== "shortcut") {
      throw new Error("managed identity kind is invalid");
    }
    const normalizedTarget = normalizeShortcutTargetCandidate(target);
    if (normalizedTarget === null) {
      throw new Error("managed shortcut target is invalid");
    }
    return (
      `shortcut:${canonicalAppid}:` +
      encodeAllUtf8Bytes(normalizedTarget)
    );
  }

  function nativeActionSectionsVisible(value) {
    return value?.installed === true;
  }

  function nativeContainerActionDisabled({
    compatEnabled,
    containerExists = true,
    busy,
    operation,
    deleteConfirmed,
  }) {
    if (!compatEnabled) {
      return true;
    }
    if (!containerExists) {
      return true;
    }
    if (busy && operation !== "quit-all") {
      return true;
    }
    return (
      operation === "delete-container" &&
      deleteConfirmed !== true
    );
  }

  async function chooseWindowsExecutableWithSteam(
    steamGlobal,
    initialFile = "",
  ) {
    const system = steamGlobal?.SteamClient?.System;
    if (typeof system?.OpenFileDialog !== "function") {
      return undefined;
    }
    try {
      const selected = await system.OpenFileDialog({
        strTitle: "选择 Windows 可执行文件或批处理文件",
        strInitialFile:
          typeof initialFile === "string" ? initialFile : "",
        rgFilters: [
          {
            strFileTypeName: "Windows 可执行文件",
            rFilePatterns: ["*.exe", "*.bat", "*.cmd"],
            bUseAsDefault: true,
          },
          {
            strFileTypeName: "所有文件",
            rFilePatterns: ["*.*"],
          },
        ],
      });
      if (typeof selected === "string") {
        return selected || null;
      }
      if (Array.isArray(selected)) {
        for (const value of selected) {
          if (typeof value === "string" && value) {
            return value;
          }
          const objectPath =
            value?.strPath ?? value?.path ?? value?.strFileName;
          if (typeof objectPath === "string" && objectPath) {
            return objectPath;
          }
        }
        return null;
      }
      const objectPath =
        selected?.strPath ??
        selected?.path ??
        selected?.strFileName;
      return typeof objectPath === "string" && objectPath
        ? objectPath
        : null;
    } catch {
      return undefined;
    }
  }

  function isNativeCompatToolboxSupported(toolbox) {
    const react = toolbox?.React;
    const jsx = toolbox?.jsx;
    const components = toolbox?.components;
    const styles = toolbox?.styles;
    const isReactComponent = (value) =>
      typeof value === "function" ||
      (value !== null &&
        typeof value === "object" &&
        "$$typeof" in value &&
        typeof value.render === "function");
    return (
      typeof react?.useEffect === "function" &&
      typeof react?.useState === "function" &&
      typeof jsx?.jsx === "function" &&
      typeof jsx?.jsxs === "function" &&
      jsx.Fragment !== undefined &&
      ["$n", "Vb", "XY", "pd", "y4"].every(
        (name) => isReactComponent(components?.[name]),
      ) &&
      [
        "Detail",
        "SettingsDialogButton",
        "TopGap",
      ].every((name) => typeof styles?.[name] === "string")
    );
  }

  const NATIVE_COMPAT_SECTION_LABELS = Object.freeze([
    "兼容性选项",
    "安装 Windows 组件",
    "容器操作",
    "运行命令",
    "最近操作状态",
  ]);

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

  async function discoverTypedRegistry({ overviews, loadDetails }) {
    if (typeof loadDetails !== "function") {
      throw new Error("Steam app detail loader is unavailable");
    }

    const apps = new Set();
    const shortcuts = new Map();
    const seenAppids = new Set();
    for (const overview of overviews ?? []) {
      if (overview?.visible_in_game_list !== true) {
        continue;
      }
      const canonicalAppid = canonicalizePositiveUint32(
        overview?.appid,
      );
      if (canonicalAppid === null) {
        continue;
      }
      const appid = Number(canonicalAppid);
      if (seenAppids.has(appid)) {
        throw new Error(
          `managed registry collision for AppID ${canonicalAppid}`,
        );
      }
      seenAppids.add(appid);
      if (
        overview?.app_type !== GAME_APP_TYPE &&
        overview?.app_type !== 0x40000000
      ) {
        continue;
      }

      const details = await loadDetails(appid);
      if (!details) {
        throw new Error(
          `missing Steam app details for AppID ${canonicalAppid}`,
        );
      }

      const storeQualified = isOwnedWindowsOnlyGame(
        overview,
        details,
      );
      const shortcutQualified = isManagedShortcut(
        overview,
        details,
      );
      if (!storeQualified && !shortcutQualified) {
        continue;
      }
      if (storeQualified && shortcutQualified) {
        throw new Error(
          `managed registry collision for AppID ${canonicalAppid}`,
        );
      }
      if (apps.has(appid) || shortcuts.has(appid)) {
        throw new Error(
          `managed registry collision for AppID ${canonicalAppid}`,
        );
      }
      if (storeQualified) {
        apps.add(appid);
      } else {
        shortcuts.set(
          appid,
          normalizeShortcutTargetCandidate(details.strShortcutExe),
        );
      }
    }
    return { apps, shortcuts };
  }

  async function discoverManagedApps(options) {
    const candidates = (options?.overviews ?? []).filter(
      isOwnedVisibleGameOverview,
    );
    const entries = await Promise.all(
      candidates.map(async (overview) => {
        const details = await options.loadDetails(overview.appid);
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

  function hasPositiveSize(value) {
    if (typeof value === "bigint") {
      return value > 0n;
    }
    if (typeof value === "number") {
      return Number.isFinite(value) && value > 0;
    }
    return (
      typeof value === "string" &&
      /^[0-9]+$/.test(value) &&
      !/^0+$/.test(value)
    );
  }

  function manifestDiagnosticTargetStatus(diagnostic) {
    if (
      MANIFEST_INSTALL_DIAGNOSTICS.has(diagnostic) ||
      MANIFEST_RESUME_DIAGNOSTICS.has(diagnostic) ||
      MANIFEST_STALE_SHELL_DIAGNOSTICS.has(diagnostic) ||
      diagnostic === "manifest-invalid" ||
      diagnostic === "state-blocked"
    ) {
      return READY_TO_INSTALL;
    }
    if (MANIFEST_VERIFY_DIAGNOSTICS.has(diagnostic)) {
      return null;
    }
    return null;
  }

  function manifestDiagnosticRepairAction(diagnostic) {
    if (MANIFEST_INSTALL_DIAGNOSTICS.has(diagnostic)) {
      return "install";
    }
    if (MANIFEST_STALE_SHELL_DIAGNOSTICS.has(diagnostic)) {
      return "reset";
    }
    if (MANIFEST_RESUME_DIAGNOSTICS.has(diagnostic)) {
      return "resume";
    }
    if (MANIFEST_VERIFY_DIAGNOSTICS.has(diagnostic)) {
      return "verify";
    }
    return null;
  }

  function getManagedTargetStatus(state) {
    if (state.allowlisted !== true) {
      return null;
    }
    const manifestTarget = manifestDiagnosticTargetStatus(
      state.manifestDiagnostic,
    );
    if (
      manifestTarget !== null &&
      (
        state.detailsStatus === INVALID_PLATFORM ||
        state.detailsStatus === READY_TO_LAUNCH
      )
    ) {
      return manifestTarget;
    }
    if (state.detailsStatus === INVALID_PLATFORM) {
      return (
        state.hasAnyLocalContent === true &&
        state.installed === true &&
        hasPositiveSize(state.sizeOnDisk)
      )
        ? READY_TO_LAUNCH
        : READY_TO_INSTALL;
    }
    if (!VALID_DISPLAY_STATUSES.has(state.detailsStatus)) {
      return null;
    }
    if (
      state.detailsStatus === READY_TO_LAUNCH &&
      (
        state.hasAnyLocalContent !== true ||
        state.installed !== true ||
        !hasPositiveSize(state.sizeOnDisk)
      )
    ) {
      return READY_TO_INSTALL;
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

  function chooseNativeRepairAction(state) {
    if (!VALID_DISPLAY_STATUSES.has(state.detailsStatus)) {
      return null;
    }
    if (
      new Set([1, 2, 3, 4, 5, 6, 7, 8, 36]).has(
        state.detailsStatus,
      )
    ) {
      return "active";
    }
    const manifestAction = manifestDiagnosticRepairAction(
      state.manifestDiagnostic,
    );
    if (manifestAction) {
      return manifestAction;
    }
    if (
      state.detailsStatus === READY_TO_LAUNCH &&
      getManagedTargetStatus({
        ...state,
        allowlisted: true,
      }) === READY_TO_INSTALL
    ) {
      return "resume";
    }
    if (
      new Set([18, 19, 22, 23, 24, 25, 38]).has(
        state.detailsStatus,
      )
    ) {
      return "resume";
    }
    if (state.detailsStatus === READY_TO_INSTALL) {
      return "install";
    }
    if (
      state.installed === true ||
      state.hasAnyLocalContent === true ||
      state.detailsStatus === 20 ||
      state.detailsStatus === 39
    ) {
      return "verify";
    }
    return "install";
  }

  async function openWindowsInstallWizard(
    steamClient,
    appid,
    sleep = (milliseconds) =>
      new Promise((resolve) =>
        globalObject.setTimeout(resolve, milliseconds),
      ),
  ) {
    if (
      typeof steamClient?.Console?.ExecCommand !== "function" ||
      typeof steamClient?.Installs?.OpenInstallWizard !== "function" ||
      typeof steamClient?.Installs?.GetInstallManagerInfo !== "function"
    ) {
      throw new Error("Steam Windows install-plan APIs are unavailable");
    }
    const before =
      await steamClient.Installs.GetInstallManagerInfo();
    if (Number(before?.currentAppID ?? 0) !== 0) {
      throw new Error("another Steam install is active");
    }
    let plan = null;
    try {
      await steamClient.Console.ExecCommand(
        "@sSteamCmdForcePlatformType windows",
      );
      await steamClient.Installs.OpenInstallWizard([appid]);
      for (let attempt = 0; attempt < 30; attempt += 1) {
        plan = await steamClient.Installs.GetInstallManagerInfo();
        if (
          plan?.currentAppID === appid &&
          Number(plan.nDiskSpaceRequired) > 0 &&
          Number(plan.eAppError ?? 0) === 0
        ) {
          return plan;
        }
        if (Number(plan?.eAppError ?? 0) !== 0) {
          break;
        }
        await sleep(100);
      }
      if (
        plan?.currentAppID === appid &&
        typeof steamClient.Installs.CancelInstall === "function"
      ) {
        await steamClient.Installs.CancelInstall();
      }
      throw new Error(
        `Steam produced an empty Windows depot plan for AppID ${appid}`,
      );
    } finally {
      await steamClient.Console.ExecCommand(
        "@sSteamCmdForcePlatformType macos",
      );
    }
  }

  async function requestNativeRepair({
    steamClient,
    appid,
    allowlisted,
    detailsStatus,
    hasAnyLocalContent,
    installed,
    sizeOnDisk,
    manifestDiagnostic,
    clientid,
  }) {
    if (
      allowlisted !== true ||
      !Number.isSafeInteger(appid) ||
      appid <= 0
    ) {
      throw new Error(`AppID ${appid} is not managed`);
    }
    const action = chooseNativeRepairAction({
      detailsStatus,
      hasAnyLocalContent,
      installed,
      sizeOnDisk,
      manifestDiagnostic,
    });
    if (!action) {
      throw new Error(
        `Steam repair state ${detailsStatus} is unsupported`,
      );
    }
    if (action === "active") {
      return action;
    }
    if (action === "resume") {
      if (
        typeof steamClient?.Downloads?.ResumeAppUpdate !==
        "function"
      ) {
        throw new Error("Steam resume-update API is unavailable");
      }
      await steamClient.Downloads.ResumeAppUpdate(
        appid,
        clientid ?? "0",
      );
      return action;
    }
    if (action === "verify") {
      if (typeof steamClient?.Apps?.VerifyApp !== "function") {
        throw new Error("Steam verify API is unavailable");
      }
      await steamClient.Apps.VerifyApp(appid);
      return action;
    }
    if (action === "reset") {
      if (
        typeof steamClient?.Installs?.OpenUninstallWizard !==
        "function"
      ) {
        throw new Error("Steam stale-install reset API is unavailable");
      }
      await steamClient.Installs.OpenUninstallWizard([appid], true);
      return action;
    }
    if (
      typeof steamClient?.Installs?.OpenInstallWizard !==
      "function"
    ) {
      throw new Error("Steam install API is unavailable");
    }
    await openWindowsInstallWizard(steamClient, appid);
    return action;
  }

  async function runManagedGame({
    gameid,
    options,
    launchOption,
    launchSource,
    managedAppids,
    inspectState,
    originalRunGame,
  }) {
    const appid = Number(gameid);
    if (
      launchOption !== -1 ||
      !Number.isSafeInteger(appid) ||
      appid <= 0 ||
      !managedAppids.has(appid)
    ) {
      return originalRunGame(
        gameid,
        options,
        launchOption,
        launchSource,
      );
    }
    const state = await inspectState(appid);
    if (
      state?.installed !== true ||
      !Number.isSafeInteger(state.launch_entry_id) ||
      state.launch_entry_id < 0 ||
      typeof state.launch_executable !== "string" ||
      !state.launch_executable.toLowerCase().endsWith(".exe")
    ) {
      throw new Error(
        `verified Windows launch entry is unavailable for AppID ${appid}`,
      );
    }
    return originalRunGame(
      gameid,
      options,
      state.launch_entry_id,
      launchSource,
    );
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
      installed: selected.installed,
      sizeOnDisk: overview.size_on_disk,
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
      installed: selected.installed,
      sizeOnDisk: overview.size_on_disk,
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
      isNativeCompatToolboxSupported,
      isOwnedWindowsOnlyGame,
      buildControlPayload,
      buildControlUrl,
      buildActionUrl,
      buildChooseFilePayload,
      buildContainerActionPayload,
      buildDependencyPayload,
      buildInspectStatePayload,
      buildJobUrl,
      buildRunCommandPayload,
      buildManagedRegistryBody,
      buildShortcutControlUrl,
      chooseWindowsExecutableWithSteam,
      applyToolCapabilities,
      chooseNativeRepairAction,
      compatToolRecord,
      compatToolForRenderer,
      discoverTypedRegistry,
      mergeCompatTools,
      managedIdentityStorageKey,
      normalizeControlConfig,
      normalizeDependencyCatalog,
      normalizeShortcutTargetCandidate,
      openWindowsInstallWizard,
      nativeActionSectionsVisible,
      nativeContainerActionDisabled,
      NATIVE_COMPAT_SECTION_LABELS,
      isManagedShortcut,
      refreshAppActionComponents,
      reconcileCompatDetails,
      reconcileAppState,
      requestNativeRepair,
      rendererForCompatTool,
      runManagedGame,
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
  const managedStoreAppids = new Set(managedAppids);
  const managedShortcutTargets = new Map();
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
    version: 15,
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
    nativeCompatRenders: 0,
    nativeCompatLastError: null,
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
  const nativeCompatSelections = new Map();
  const controlConfigs = new Map();
  const actionStates = new Map();
  const nativeLoadedControlAppids = new Set();
  const lastNativeControlPayloads = new Map();
  const nativeSyncedStoreAppids = new Set();
  const nativeDetailsSubscriptions = new Map();
  const nativeDetailsRefreshAt = new Map();
  let storedCompatSelections = {};
  let storedControlConfigs = {};
  let reconcileRunning = false;
  let registryRefreshRunning = false;
  let lastNativeRegistryPayload = null;
  globalObject[SELECTED_COMPAT_TOOL_KEY] = (appid) =>
    compatSelections.get(Number(appid)) ?? "";

  function storageKeyForAppid(appid) {
    return managedShortcutTargets.has(appid)
      ? managedIdentityStorageKey(
          "shortcut", appid, managedShortcutTargets.get(appid),
        )
      : managedIdentityStorageKey("store", appid);
  }

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
    if (!nativeSyncedStoreAppids.has(appid)) {
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
              !nativeSyncedStoreAppids.has(appid) ||
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

  function publishNativeSyncedStoreApps() {
    for (const appid of [...nativeDetailsSubscriptions.keys()]) {
      if (!managedStoreAppids.has(appid)) {
        releaseNativeDetailsSubscription(appid);
      }
    }
    nativeSyncedStoreAppids.clear();
    for (const appid of managedStoreAppids) {
      nativeSyncedStoreAppids.add(appid);
      if (!nativeDetailsSubscriptions.has(appid)) {
        refreshNativeDetailsSubscription(appid, true);
      }
    }
  }

  async function syncNativeRegistry(nextRegistry) {
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
    const payload = buildManagedRegistryBody(nextRegistry);
    if (payload === lastNativeRegistryPayload) {
      return true;
    }
    try {
      const response = await globalObject.fetch(
        `${endpoint}?token=${encodeURIComponent(token)}`,
        {
          method: "POST",
          mode: "cors",
          cache: "no-store",
          headers: { "Content-Type": "text/plain" },
          body: payload,
        },
      );
      if (response?.status !== 204) {
        throw new Error(
          `native registry sync failed: ${
            response?.status ?? "invalid response"
          }`,
        );
      }
      await ensureManagedRegistryApplied(nextRegistry);
      lastNativeRegistryPayload = payload;
      status.registryNativeSyncs += 1;
      status.registryLastNativeSyncAt = new Date().toISOString();
      status.registryLastNativeSyncError = null;
      publishNativeSyncedStoreApps();
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
    const key = storageKeyForAppid(appid);
    const legacyKey = String(appid);
    const storedTool =
      Object.prototype.hasOwnProperty.call(
        storedCompatSelections, key,
      )
        ? storedCompatSelections[key]
        : (
            managedStoreAppids.has(appid) &&
            Object.prototype.hasOwnProperty.call(
              storedCompatSelections, legacyKey,
            )
          )
          ? storedCompatSelections[legacyKey]
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
    const serialized = { ...storedCompatSelections };
    for (const [appid, tool] of compatSelections) {
      serialized[storageKeyForAppid(appid)] = tool;
    }
    storedCompatSelections = serialized;
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
    const key = storageKeyForAppid(appid);
    const legacyKey = String(appid);
    const stored =
      Object.prototype.hasOwnProperty.call(
        storedControlConfigs, key,
      )
        ? storedControlConfigs[key]
        : (
            managedStoreAppids.has(appid) &&
            Object.prototype.hasOwnProperty.call(
              storedControlConfigs, legacyKey,
            )
          )
          ? storedControlConfigs[legacyKey]
          : null;
    const selectedTool = compatToolRecord(
      compatSelections.get(appid),
      projectCompatTools,
    );
    const renderer =
      selectedTool?.renderer ??
      normalizeControlConfig(stored).renderer;
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
    const serialized = { ...storedControlConfigs };
    for (const [appid, value] of controlConfigs) {
      serialized[storageKeyForAppid(appid)] =
        normalizeControlConfig(value);
    }
    storedControlConfigs = serialized;
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
      managedShortcutTargets.has(appid)
        ? buildShortcutControlUrl(
            config.controlEndpoint,
            config.registryToken,
            appid,
          )
        : buildControlUrl(
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
    nativeLoadedControlAppids.add(appid);
    status.controlNativeLoads += 1;
    status.controlLastError = null;
    persistControlConfigs();
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
        managedShortcutTargets.has(appid)
          ? buildShortcutControlUrl(
              config.controlEndpoint,
              config.registryToken,
              appid,
            )
          : buildControlUrl(
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

  function setActionState(appid, value) {
    actionStates.set(appid, {
      ...actionStateFor(appid),
      ...value,
    });
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

  async function inspectNativeActionState(appid) {
    const jobId = await startNativeAction(
      appid,
      buildInspectStatePayload(),
    );
    const job = await waitForNativeActionJob(appid, jobId);
    if (
      job.state !== "completed" ||
      typeof job.result?.installed !== "boolean" ||
      typeof job.result?.container_exists !== "boolean"
    ) {
      throw new Error(
        job.message || "native action availability is invalid",
      );
    }
    if (
      "manifest_diagnostic" in job.result &&
      typeof job.result.manifest_diagnostic !== "string"
    ) {
      throw new Error("native action manifest diagnostic is invalid");
    }
    return job.result;
  }

  async function runNativeAction(
    appid,
    payload,
    label,
    { allowWhileBusy = false } = {},
  ) {
    if (
      actionStateFor(appid).state === "running" &&
      !allowWhileBusy
    ) {
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
    );
    status.actionJobsStarted += 1;
    let jobId = "";
    try {
      jobId = await startNativeAction(appid, payload);
      setActionState(
        appid,
        {
          state: "running",
          message: "任务运行中",
          jobId,
        },
      );
      const result = await waitForNativeActionJob(appid, jobId);
      if (actionStateFor(appid).jobId !== jobId) {
        return result;
      }
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
      if (
        jobId &&
        actionStateFor(appid).jobId !== jobId
      ) {
        return null;
      }
      status.actionJobsFailed += 1;
      status.actionLastError = String(error);
      setActionState(
        appid,
        {
          state: "failed",
          message: String(error),
        },
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
  let originalSpecifyCompatTool = null;
  let originalRunGame = null;

  async function commitNativeCompatSelection(appid, tool) {
    if (nativeCompatSelections.get(appid) === tool) {
      return undefined;
    }
    const result = projectCompatToolNames.has(tool)
      ? undefined
      : await originalSpecifyCompatTool(appid, tool);
    nativeCompatSelections.set(appid, tool);
    status.compatNativeSyncs += 1;
    return result;
  }

  function installCompatToolBridge() {
    const apps = globalObject.SteamClient?.Apps;
    if (
      !apps ||
      typeof apps.SpecifyCompatTool !== "function" ||
      typeof apps.GetAvailableCompatTools !== "function" ||
      typeof apps.RunGame !== "function"
    ) {
      throw new Error("Steam compatibility tool APIs are unavailable");
    }

    originalSpecifyCompatTool = apps.SpecifyCompatTool.bind(apps);
    originalGetAvailableCompatTools =
      apps.GetAvailableCompatTools.bind(apps);
    originalRunGame = apps.RunGame.bind(apps);
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

      const result = await commitNativeCompatSelection(appid, tool);
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
    apps.RunGame = (gameid, options, launchOption, launchSource) =>
      runManagedGame({
        gameid,
        options,
        launchOption,
        launchSource,
        managedAppids: managedStoreAppids,
        inspectState: inspectNativeActionState,
        originalRunGame,
      }).catch((error) => {
        status.actionLastError = String(error);
        throw error;
      });
    return originalSpecifyCompatTool;
  }

  async function syncNativeCompatSelections() {
    for (const appid of managedAppids) {
      const selectedTool = compatSelections.get(appid) ?? "";
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
      await commitNativeCompatSelection(appid, selectedTool);
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

  globalObject[REPAIR_ACTION_KEY] = async (requestedAppid) => {
    const appid = Number(requestedAppid);
    const overview =
      globalObject.appStore?.GetAppOverviewByAppID?.(appid) ?? null;
    const details = await loadAppDetails(appid);
    const selected = getSelectedData(overview);
    if (!overview || !details || !selected) {
      throw new Error(`Steam app state is unavailable for AppID ${appid}`);
    }
    if (!managedStoreAppids.has(appid)) {
      throw new Error(`AppID ${appid} is not managed`);
    }
    const actionState = await inspectNativeActionState(appid);
    return requestNativeRepair({
      steamClient: globalObject.SteamClient,
      appid,
      allowlisted: true,
      detailsStatus: details.eDisplayStatus,
      hasAnyLocalContent:
        typeof actionState.install_path_nonempty === "boolean"
          ? actionState.install_path_nonempty
          : details.bHasAnyLocalContent,
      installed: actionState.installed,
      sizeOnDisk:
        actionState.size_on_disk ?? overview.size_on_disk,
      manifestDiagnostic: actionState.manifest_diagnostic,
      clientid: overview.selected_clientid ?? selected.clientid ?? "0",
    });
  };

  async function restoreRemovedApp(appid, wasStoreApp) {
    try {
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
        if (wasStoreApp) {
          reconcileAppState({
            overview,
            details,
            allowlist: new Set(),
            originalStates,
          });
        }
      }
    } finally {
      compatSelections.delete(appid);
      controlConfigs.delete(appid);
      nativeCompatSelections.delete(appid);
      nativeLoadedControlAppids.delete(appid);
      lastNativeControlPayloads.delete(appid);
      availableCompatTools.delete(appid);
      actionStates.delete(appid);
      releaseNativeDetailsSubscription(appid);
    }
  }

  async function applyManagedRegistry(nextRegistry) {
    const nextManagedAppids = new Set([
      ...nextRegistry.apps,
      ...nextRegistry.shortcuts.keys(),
    ]);
    const retyped = [...managedAppids].filter(
      (appid) =>
        nextManagedAppids.has(appid) &&
        managedStoreAppids.has(appid) !== nextRegistry.apps.has(appid),
    );
    const removed = [...managedAppids].filter(
      (appid) => !nextManagedAppids.has(appid),
    );
    const added = [...nextManagedAppids].filter(
      (appid) => !managedAppids.has(appid),
    );
    const removedIdentities = [...removed, ...retyped].map((appid) => ({
      appid,
      wasStoreApp: managedStoreAppids.has(appid),
    }));

    // The native service has already accepted this snapshot. Commit the
    // in-memory identity sets without awaiting fallible cleanup or storage.
    managedAppids.clear();
    managedStoreAppids.clear();
    managedShortcutTargets.clear();
    for (const appid of nextRegistry.apps) {
      managedStoreAppids.add(appid);
    }
    for (const [appid, target] of nextRegistry.shortcuts) {
      managedShortcutTargets.set(appid, target);
    }
    for (const appid of nextManagedAppids) {
      managedAppids.add(appid);
    }
    status.appids = [...managedAppids].sort((left, right) => left - right);
    status.registryAdded += added.length + retyped.length;
    status.registryRemoved += removed.length + retyped.length;

    for (const { appid, wasStoreApp } of removedIdentities) {
      try {
        await restoreRemovedApp(appid, wasStoreApp);
      } catch (error) {
        status.registryLastError = String(error);
      }
    }
    for (const appid of managedAppids) {
      try {
        ensureCompatSelection(appid);
        ensureControlConfig(appid);
      } catch (error) {
        status.registryLastError = String(error);
      }
    }
    if (added.length || removed.length || retyped.length) {
      try {
        persistCompatSelections();
        persistControlConfigs();
      } catch (error) {
        status.registryLastError = String(error);
      }
    }
  }

  function managedRegistrySnapshot() {
    return {
      apps: new Set(managedStoreAppids),
      shortcuts: new Map(managedShortcutTargets),
    };
  }

  function registryMatchesManagedState(registry) {
    if (
      registry.apps.size !== managedStoreAppids.size ||
      registry.shortcuts.size !== managedShortcutTargets.size
    ) {
      return false;
    }
    for (const appid of registry.apps) {
      if (!managedStoreAppids.has(appid)) {
        return false;
      }
    }
    for (const [appid, target] of registry.shortcuts) {
      if (managedShortcutTargets.get(appid) !== target) {
        return false;
      }
    }
    return true;
  }

  async function ensureManagedRegistryApplied(registry) {
    if (!registryMatchesManagedState(registry)) {
      await applyManagedRegistry(registry);
    }
    return managedRegistrySnapshot();
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
      if (overviews.length === 0 && managedAppids.size > 0) {
        throw new Error(
          "Steam app overview store is not initialized",
        );
      }
      const nextRegistry = await discoverTypedRegistry({
        overviews,
        loadDetails: loadAppDetails,
      });
      if (await syncNativeRegistry(nextRegistry)) {
        await syncNativeCompatSelections();
      }
      await reconcile();
    } catch (error) {
      status.registryLastError = String(error);
    } finally {
      registryRefreshRunning = false;
    }
  }

  function controlDefinitions(tool) {
    const capabilities = tool?.capabilities ?? {};
    return [
      {
        key: "msync",
        label: "启用 MSync",
        enabled: capabilities.msync === true,
      },
      {
        key: "retina",
        label: "高分辨率模式",
        enabled: capabilities.retina === true,
      },
      {
        key: "metal_hud",
        label: "Metal HUD",
        enabled: capabilities.metal_hud === true,
      },
      {
        key: "metalfx",
        label: "DLSS 转 MetalFX",
        enabled: capabilities.metalfx === true,
      },
      {
        key: "dxr",
        label: "DXR",
        enabled: capabilities.dxr === true,
      },
      {
        key: "avx",
        label: "Rosetta AVX",
        enabled: capabilities.avx === true,
      },
    ];
  }

  const containerActionOptions = [
    { data: "open-c-drive", label: "打开 C: 盘" },
    { data: "wine-configuration", label: "Wine 配置" },
    { data: "controllers", label: "Wine 游戏控制器" },
    { data: "restart", label: "模拟重启" },
    { data: "task-manager", label: "任务管理器" },
    { data: "quit-all", label: "退出所有应用程序" },
    { data: "delete-container", label: "移动容器到恢复目录" },
  ];
  const nativeCompatComponentCache = new WeakMap();

  function createNativeCompatControlsComponent(toolbox) {
    const { React, jsx, components, styles } = toolbox;
    const nativeButton = (label, onClick, disabled = false) =>
      jsx.jsx(components.$n, {
        className: styles.SettingsDialogButton,
        disabled,
        onClick,
        children: label,
      });

    return function RealSteamOnMacNativeCompatControls({ details }) {
      const appid = Number(details?.unAppID);
      const [value, setValue] = React.useState(() =>
        ensureControlConfig(appid),
      );
      const [target, setTarget] = React.useState("");
      const [commandArguments, setCommandArguments] =
        React.useState("");
      const [commandEnvironment, setCommandEnvironment] =
        React.useState("");
      const [commandExpanded, setCommandExpanded] =
        React.useState(false);
      const [actionAvailability, setActionAvailability] =
        React.useState(null);
      const [dependencyId, setDependencyId] = React.useState(
        dependencies[0]?.id ?? "",
      );
      const [containerOperation, setContainerOperation] =
        React.useState("open-c-drive");
      const [deleteConfirmed, setDeleteConfirmed] =
        React.useState(false);
      const [activity, setActivity] = React.useState(() => ({
        ...actionStateFor(appid),
      }));
      const selectedToolName =
        compatSelections.get(appid) ?? value.compat_tool;
      const selectedTool =
        compatToolRecord(selectedToolName, projectCompatTools) ??
        null;
      const shortcut = managedShortcutTargets.has(appid);
      const compatEnabled = Boolean(selectedTool);
      const busy = activity.state === "running";

      React.useEffect(() => {
        let active = true;
        void loadNativeControlConfig(appid)
          .then(() => {
            if (active) {
              setValue({ ...ensureControlConfig(appid) });
            }
          })
          .catch((error) => {
            status.nativeCompatLastError = String(error);
          });
        return () => {
          active = false;
        };
      }, [appid]);

      React.useEffect(() => {
        if (shortcut) {
          setActionAvailability(null);
          return undefined;
        }
        let active = true;
        void inspectNativeActionState(appid)
          .then((result) => {
            if (active) {
              setActionAvailability(result);
            }
          })
          .catch((error) => {
            if (active) {
              setActionAvailability(null);
            }
            status.nativeCompatLastError = String(error);
          });
        return () => {
          active = false;
        };
      }, [appid, shortcut]);

      React.useEffect(() => {
        setValue((current) =>
          applyToolCapabilities(
            {
              ...current,
              compat_tool: selectedTool?.strToolName ?? "",
              renderer:
                selectedTool?.renderer ?? current.renderer,
            },
            selectedTool,
          ),
        );
      }, [selectedToolName]);

      const runAction = async (
        payload,
        label,
        { allowWhileBusy = false } = {},
      ) => {
        setActivity({
          ...actionStateFor(appid),
          state: "running",
          label,
          message: "任务运行中",
        });
        await runNativeAction(appid, payload, label, {
          allowWhileBusy,
        });
        setActivity({ ...actionStateFor(appid) });
        try {
          setActionAvailability(
            await inspectNativeActionState(appid),
          );
        } catch (error) {
          setActionAvailability(null);
          status.nativeCompatLastError = String(error);
        }
      };

      const saveToggle = async (key, enabled) => {
        const previous = value;
        const next = applyToolCapabilities(
          {
            ...value,
            compat_tool: selectedTool?.strToolName ?? "",
            renderer: selectedTool?.renderer ?? value.renderer,
            [key]: enabled,
          },
          selectedTool,
        );
        setValue(next);
        try {
          setValue(await saveNativeControlConfig(appid, next));
        } catch (error) {
          setValue(previous);
          status.nativeCompatLastError = String(error);
        }
      };

      const browseTarget = async () => {
        const selected = await chooseWindowsExecutableWithSteam(
          globalObject,
          target,
        );
        if (typeof selected === "string" && selected) {
          setTarget(selected);
          return;
        }
        if (selected === undefined) {
          const result = await runNativeAction(
            appid,
            buildChooseFilePayload(),
            "选择可执行文件",
          );
          const fallback = result?.result?.target;
          if (typeof fallback === "string" && fallback) {
            setTarget(fallback);
          }
        }
        setActivity({ ...actionStateFor(appid) });
      };

      const selectedDependency = dependencies.find(
        (dependency) => dependency.id === dependencyId,
      );
      const actionDisabled = !compatEnabled || busy;
      const actionSectionsVisible =
        nativeActionSectionsVisible(actionAvailability);
      const containerExists =
        actionAvailability?.container_exists === true;
      const containerActionDisabled =
        actionDisabled || !containerExists;
      const deleteNeedsConfirmation =
        containerOperation === "delete-container";
      const containerDisabled = nativeContainerActionDisabled({
        compatEnabled,
        containerExists,
        busy,
        operation: containerOperation,
        deleteConfirmed,
      });

      return jsx.jsxs(jsx.Fragment, {
        children: [
          jsx.jsxs(components.XY, {
            label: NATIVE_COMPAT_SECTION_LABELS[0],
            children: [
              ...controlDefinitions(selectedTool).map((definition) =>
                jsx.jsx(
                  components.y4,
                  {
                    label: definition.label,
                    checked: Boolean(value[definition.key]),
                    disabled:
                      !compatEnabled ||
                      !definition.enabled ||
                      busy,
                    onChange: (enabled) => {
                      void saveToggle(definition.key, enabled);
                    },
                  },
                  definition.key,
                ),
              ),
            ],
          }),
          actionSectionsVisible
            ? jsx.jsxs(components.XY, {
            label: NATIVE_COMPAT_SECTION_LABELS[1],
            children: [
              jsx.jsx(components.Vb, {
                strClassName: styles.TopGap,
                label: "经过校验的 Windows 组件",
                rgOptions: dependencies.map((dependency) => ({
                  data: dependency.id,
                  label: dependency.name,
                })),
                selectedOption: dependencyId,
                disabled: !containerExists || busy,
                onChange: (option) => setDependencyId(option.data),
              }),
              jsx.jsx("div", {
                className: styles.Detail,
                children: selectedDependency
                  ? `${selectedDependency.publisher} · ${selectedDependency.description}`
                  : "当前没有可安装的组件",
              }),
              nativeButton("安装", () => {
                if (selectedDependency) {
                  void runAction(
                    buildDependencyPayload(selectedDependency.id),
                    `安装 ${selectedDependency.name}`,
                  );
                }
              }, containerActionDisabled || !selectedDependency),
            ],
            })
            : null,
          actionSectionsVisible
            ? jsx.jsxs(components.XY, {
            label: NATIVE_COMPAT_SECTION_LABELS[2],
            children: [
              jsx.jsx(components.Vb, {
                strClassName: styles.TopGap,
                label: "操作",
                rgOptions: containerActionOptions,
                selectedOption: containerOperation,
                disabled: !containerExists || busy,
                onChange: (option) => {
                  setContainerOperation(option.data);
                  setDeleteConfirmed(false);
                },
              }),
              deleteNeedsConfirmation
                ? jsx.jsx(components.y4, {
                    label: "确认移动现有容器到恢复目录",
                    checked: deleteConfirmed,
                    disabled: containerActionDisabled,
                    onChange: setDeleteConfirmed,
                  })
                : null,
              nativeButton("执行", () => {
                void runAction(
                  buildContainerActionPayload(containerOperation),
                  containerActionOptions.find(
                    (option) =>
                      option.data === containerOperation,
                  )?.label ?? "容器操作",
                  {
                    allowWhileBusy:
                      containerOperation === "quit-all",
                  },
                );
              }, containerDisabled),
            ],
            })
            : null,
          actionSectionsVisible
            ? jsx.jsxs(components.XY, {
            label: NATIVE_COMPAT_SECTION_LABELS[3],
            children: [
              nativeButton("运行命令...", () => {
                setCommandExpanded(true);
              }, containerActionDisabled || commandExpanded),
              commandExpanded
                ? jsx.jsxs(jsx.Fragment, {
                    children: [
                      jsx.jsx(components.pd, {
                        className: styles.TopGap,
                        label: "命令",
                        placeholder:
                          "cmd、regedit、C:\\path\\tool.exe 或文档",
                        spellCheck: false,
                        disabled: !containerExists || busy,
                        value: target,
                        onChange: (event) =>
                          setTarget(event.target.value),
                      }),
                      nativeButton("浏览...", () => {
                        void browseTarget();
                      }, containerActionDisabled),
                      jsx.jsx(components.pd, {
                        className: styles.TopGap,
                        label: "参数",
                        placeholder: '/c echo "hello"',
                        spellCheck: false,
                        disabled: !containerExists || busy,
                        value: commandArguments,
                        onChange: (event) =>
                          setCommandArguments(event.target.value),
                      }),
                      jsx.jsx(components.pd, {
                        className: styles.TopGap,
                        label: "环境变量，每行 NAME=VALUE",
                        placeholder: "DXVK_HUD=fps",
                        spellCheck: false,
                        disabled: !containerExists || busy,
                        value: commandEnvironment,
                        onChange: (event) =>
                          setCommandEnvironment(event.target.value),
                      }),
                      nativeButton("取消", () => {
                        setCommandExpanded(false);
                      }, busy),
                      nativeButton("运行", () => {
                        void runAction(
                          buildRunCommandPayload({
                            target,
                            arguments: commandArguments,
                            environment: commandEnvironment,
                          }),
                          "运行命令",
                        );
                      }, containerActionDisabled),
                    ],
                  })
                : null,
            ],
            })
            : null,
          actionSectionsVisible
            ? jsx.jsxs(components.XY, {
            label: NATIVE_COMPAT_SECTION_LABELS[4],
            children: [
              jsx.jsx(components.pd, {
                className: styles.TopGap,
                label: activity.label || "操作状态",
                disabled: true,
                readOnly: true,
                value: activity.logPath
                  ? `${activity.message || "等待操作"} · ${activity.logPath}`
                  : activity.message ||
                    `等待操作 · AppID ${appid}`,
              }),
            ],
            })
            : null,
        ],
      });
    };
  }

  function renderNativeCompatControls(toolbox) {
    const appid = Number(toolbox?.details?.unAppID);
    if (
      !managedAppids.has(appid) ||
      !isNativeCompatToolboxSupported(toolbox)
    ) {
      if (managedAppids.has(appid)) {
        status.nativeCompatLastError =
          "Steam native compatibility component shape is unsupported";
      }
      return null;
    }
    let cached = nativeCompatComponentCache.get(toolbox.components);
    if (
      !cached ||
      cached.React !== toolbox.React ||
      cached.jsx !== toolbox.jsx
    ) {
      cached = {
        React: toolbox.React,
        jsx: toolbox.jsx,
        Component: createNativeCompatControlsComponent(toolbox),
      };
      nativeCompatComponentCache.set(toolbox.components, cached);
    }
    status.nativeCompatRenders += 1;
    status.nativeCompatLastError = null;
    return toolbox.jsx.jsx(cached.Component, {
      details: toolbox.details,
    });
  }

  globalObject[NATIVE_COMPAT_RENDER_KEY] =
    renderNativeCompatControls;

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
          nativeSyncedStoreAppids.has(appid) &&
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

        if (!managedStoreAppids.has(appid)) {
          continue;
        }
        const result = reconcileAppState({
          overview,
          details,
          allowlist: nativeSyncedStoreAppids,
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
  loadControlConfigs();
  persistCompatSelections();
  persistControlConfigs();
  installCompatToolBridge();
  globalObject.setInterval(reconcile, RECONCILE_INTERVAL_MS);
  globalObject.setInterval(
    refreshManagedRegistry,
    REGISTRY_REFRESH_INTERVAL_MS,
  );
  void refreshManagedRegistry();
})(globalThis);
