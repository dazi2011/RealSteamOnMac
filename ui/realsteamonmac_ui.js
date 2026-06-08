(function initializeRealSteamOnMacUI(globalObject) {
  "use strict";

  const INVALID_PLATFORM = 14;
  const READY_TO_INSTALL = 9;
  const STATUS_KEY = "__REALSTEAMONMAC_UI_STATUS__";
  const CONFIG_KEY = "__REALSTEAMONMAC_CONFIG__";
  const RECONCILE_INTERVAL_MS = 1000;
  const MAX_FIBER_DEPTH = 40;

  function decideOverviewPatch(state) {
    return {
      normalize:
        state.allowlisted === true &&
        state.hasAnyLocalContent !== true &&
        state.detailsStatus === READY_TO_INSTALL &&
        state.overviewStatus === INVALID_PLATFORM,
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      decideOverviewPatch,
      INVALID_PLATFORM,
      READY_TO_INSTALL,
    };
    return;
  }

  const configuredAppids = Array.isArray(globalObject[CONFIG_KEY]?.appids)
    ? globalObject[CONFIG_KEY].appids
    : [];
  const allowlist = new Set(
    configuredAppids.filter(
      (appid) => Number.isSafeInteger(appid) && appid > 0,
    ),
  );
  const status = {
    version: 1,
    enabled: allowlist.size > 0,
    appids: [...allowlist],
    scans: 0,
    normalized: 0,
    restored: 0,
    lastScanAt: null,
    lastError: null,
  };
  globalObject[STATUS_KEY] = status;

  if (!status.enabled || typeof document === "undefined") {
    return;
  }

  const originalStates = new WeakMap();
  let scanScheduled = false;

  function findFiber(element) {
    const key = Object.getOwnPropertyNames(element).find(
      (name) =>
        name.startsWith("__reactFiber$") ||
        name.startsWith("__reactInternalInstance$"),
    );
    return key ? element[key] : null;
  }

  function findContext(element) {
    let fiber = findFiber(element);
    let overview = null;
    let details = null;
    let actionComponent = null;

    for (let depth = 0; fiber && depth < MAX_FIBER_DEPTH; depth += 1) {
      overview ??= fiber.memoizedProps?.overview ?? null;
      details ??= fiber.memoizedProps?.details ?? null;
      if (
        actionComponent === null &&
        typeof fiber.stateNode?.OnClick === "function" &&
        typeof fiber.stateNode?.forceUpdate === "function"
      ) {
        actionComponent = fiber.stateNode;
      }
      fiber = fiber.return;
    }

    if (!overview || !details || !actionComponent) {
      return null;
    }
    if (overview.appid !== details.unAppID) {
      return null;
    }

    const selected =
      overview.GetPerClientData?.("selected") ??
      overview.selected_per_client_data ??
      overview.per_client_data?.find(
        (entry) => entry.clientid === overview.selected_clientid,
      );
    if (!selected) {
      return null;
    }

    return { overview, details, selected, actionComponent };
  }

  function restoreTrackedContext(context) {
    const original = originalStates.get(context.selected);
    if (!original) {
      return false;
    }
    if (context.selected.display_status !== READY_TO_INSTALL) {
      originalStates.delete(context.selected);
      return false;
    }
    if (
      context.details.eDisplayStatus === READY_TO_INSTALL &&
      context.details.bHasAnyLocalContent !== true
    ) {
      return false;
    }

    context.selected.display_status = original.displayStatus;
    context.selected.is_available_on_current_platform =
      original.availableOnCurrentPlatform;
    context.selected.is_invalid_os_type = original.invalidOsType;
    originalStates.delete(context.selected);
    context.actionComponent.forceUpdate();
    status.restored += 1;
    return true;
  }

  function normalizeContext(context) {
    if (restoreTrackedContext(context)) {
      return;
    }

    const decision = decideOverviewPatch({
      allowlisted: allowlist.has(context.overview.appid),
      detailsStatus: context.details.eDisplayStatus,
      overviewStatus: context.selected.display_status,
      hasAnyLocalContent: context.details.bHasAnyLocalContent,
    });
    if (!decision.normalize) {
      return;
    }

    originalStates.set(context.selected, {
      displayStatus: context.selected.display_status,
      availableOnCurrentPlatform:
        context.selected.is_available_on_current_platform,
      invalidOsType: context.selected.is_invalid_os_type,
    });
    context.selected.display_status = READY_TO_INSTALL;
    context.selected.is_available_on_current_platform = true;
    context.selected.is_invalid_os_type = false;
    context.actionComponent.forceUpdate();
    status.normalized += 1;
  }

  function reconcile() {
    scanScheduled = false;
    status.scans += 1;
    status.lastScanAt = new Date().toISOString();
    status.lastError = null;

    try {
      const seenActions = new Set();
      for (const element of document.querySelectorAll(
        "[role=button], button",
      )) {
        const context = findContext(element);
        if (
          !context ||
          !allowlist.has(context.overview.appid) ||
          seenActions.has(context.actionComponent)
        ) {
          continue;
        }
        seenActions.add(context.actionComponent);
        normalizeContext(context);
      }
    } catch (error) {
      status.lastError = String(error);
    }
  }

  function scheduleReconcile() {
    if (scanScheduled) {
      return;
    }
    scanScheduled = true;
    setTimeout(reconcile, 0);
  }

  function start() {
    const observer = new MutationObserver(scheduleReconcile);
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
    globalObject.setInterval(reconcile, RECONCILE_INTERVAL_MS);
    scheduleReconcile();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})(globalThis);
