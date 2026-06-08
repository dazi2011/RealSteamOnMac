import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const {
  decideOverviewPatch,
  findAppActionComponents,
  refreshAppActionComponents,
  reconcileAppState,
} = require("../ui/realsteamonmac_ui.js");

test("normalizes an allowlisted backend-ready invalid-platform app", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: false,
    }),
    { normalize: true },
  );
});

test("fails closed while the native backend is still invalid", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 14,
      overviewStatus: 14,
      hasAnyLocalContent: false,
    }),
    { normalize: false },
  );
});

test("does not change a non-allowlisted app", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: false,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: false,
    }),
    { normalize: false },
  );
});

test("does not change an app with local content", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: true,
    }),
    { normalize: false },
  );
});

for (const overviewStatus of [3, 4, 5, 7, 9, 10, 11, 12, 13]) {
  test(`preserves active or non-invalid overview status ${overviewStatus}`, () => {
    assert.deepEqual(
      decideOverviewPatch({
        allowlisted: true,
        detailsStatus: 9,
        overviewStatus,
        hasAnyLocalContent: false,
      }),
      { normalize: false },
    );
  });
}

test("normalizes the shared app store object when backend details are ready", () => {
  const selected = {
    display_status: 14,
    is_available_on_current_platform: false,
    is_invalid_os_type: true,
  };
  const overview = {
    appid: 1118200,
    selected_per_client_data: selected,
  };
  const details = {
    unAppID: 1118200,
    eDisplayStatus: 9,
    bHasAnyLocalContent: false,
  };
  const originals = new WeakMap();

  assert.equal(
    reconcileAppState({
      overview,
      details,
      allowlist: new Set([1118200]),
      originalStates: originals,
    }),
    "normalized",
  );
  assert.equal(selected.display_status, 9);
  assert.equal(selected.is_available_on_current_platform, true);
  assert.equal(selected.is_invalid_os_type, false);
});

test("restores a state normalized by the shared store patch if backend readiness is lost", () => {
  const selected = {
    display_status: 14,
    is_available_on_current_platform: false,
    is_invalid_os_type: true,
  };
  const overview = {
    appid: 1118200,
    selected_per_client_data: selected,
  };
  const details = {
    unAppID: 1118200,
    eDisplayStatus: 9,
    bHasAnyLocalContent: false,
  };
  const originals = new WeakMap();
  reconcileAppState({
    overview,
    details,
    allowlist: new Set([1118200]),
    originalStates: originals,
  });

  details.eDisplayStatus = 14;
  assert.equal(
    reconcileAppState({
      overview,
      details,
      allowlist: new Set([1118200]),
      originalStates: originals,
    }),
    "restored",
  );
  assert.equal(selected.display_status, 14);
  assert.equal(selected.is_available_on_current_platform, false);
  assert.equal(selected.is_invalid_os_type, true);
});

test("renormalizes a tracked overview when Steam writes invalid platform again", () => {
  const selected = {
    display_status: 14,
    is_available_on_current_platform: false,
    is_invalid_os_type: true,
  };
  const overview = {
    appid: 1118200,
    selected_per_client_data: selected,
  };
  const details = {
    unAppID: 1118200,
    eDisplayStatus: 9,
    bHasAnyLocalContent: false,
  };
  const originals = new WeakMap();
  const state = {
    overview,
    details,
    allowlist: new Set([1118200]),
    originalStates: originals,
  };
  reconcileAppState(state);

  selected.display_status = 14;
  selected.is_available_on_current_platform = false;
  selected.is_invalid_os_type = true;

  assert.equal(reconcileAppState(state), "normalized");
  assert.equal(selected.display_status, 9);
  assert.equal(selected.is_available_on_current_platform, true);
  assert.equal(selected.is_invalid_os_type, false);
});

test("retains the original state through an active install and restores if backend readiness is lost", () => {
  const selected = {
    display_status: 14,
    is_available_on_current_platform: false,
    is_invalid_os_type: true,
  };
  const state = {
    overview: {
      appid: 1118200,
      selected_per_client_data: selected,
    },
    details: {
      unAppID: 1118200,
      eDisplayStatus: 9,
      bHasAnyLocalContent: false,
    },
    allowlist: new Set([1118200]),
    originalStates: new WeakMap(),
  };
  reconcileAppState(state);

  selected.display_status = 7;
  assert.equal(reconcileAppState(state), "unchanged");

  selected.display_status = 9;
  state.details.eDisplayStatus = 14;
  assert.equal(reconcileAppState(state), "restored");
  assert.equal(selected.display_status, 14);
  assert.equal(selected.is_available_on_current_platform, false);
  assert.equal(selected.is_invalid_os_type, true);
});

function createActionDocument(appid) {
  const action = {
    refreshes: 0,
    OnClick() {},
    forceUpdate() {
      this.refreshes += 1;
    },
  };
  const detailsFiber = {
    memoizedProps: {
      details: { unAppID: appid },
      overview: { appid },
    },
    return: {
      stateNode: action,
      return: null,
    },
  };
  const element = {};
  Object.defineProperty(element, "__reactFiber$test", {
    value: detailsFiber,
  });
  return {
    action,
    document: {
      querySelectorAll() {
        return [element];
      },
    },
  };
}

test("finds only native action components for the requested AppID", () => {
  const peoplePlayground = createActionDocument(1118200);
  const anotherGame = createActionDocument(42);
  const document = {
    querySelectorAll() {
      return [
        ...peoplePlayground.document.querySelectorAll(),
        ...anotherGame.document.querySelectorAll(),
      ];
    },
  };

  assert.deepEqual(
    findAppActionComponents(document, 1118200),
    [peoplePlayground.action],
  );
});

test("refreshes each matching native action once unless forced", () => {
  const fixture = createActionDocument(1118200);
  const refreshedActions = new WeakSet();

  assert.equal(
    refreshAppActionComponents({
      documents: [fixture.document],
      appid: 1118200,
      refreshedActions,
      force: false,
    }),
    1,
  );
  assert.equal(
    refreshAppActionComponents({
      documents: [fixture.document],
      appid: 1118200,
      refreshedActions,
      force: false,
    }),
    0,
  );
  assert.equal(
    refreshAppActionComponents({
      documents: [fixture.document],
      appid: 1118200,
      refreshedActions,
      force: true,
    }),
    1,
  );
  assert.equal(fixture.action.refreshes, 2);
});
