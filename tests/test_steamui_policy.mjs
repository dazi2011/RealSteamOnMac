import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const {
  buildManagedAppSet,
  buildControlPayload,
  buildControlUrl,
  compatToolForRenderer,
  decideOverviewPatch,
  discoverManagedApps,
  findAppActionComponents,
  getSteamUIDocuments,
  isOwnedWindowsOnlyGame,
  mergeCompatTools,
  normalizeControlConfig,
  refreshAppActionComponents,
  reconcileCompatDetails,
  reconcileAppState,
  rendererForCompatTool,
  DETAILS_REFRESH_INTERVAL_MS,
} = require("../ui/realsteamonmac_ui.js");

const projectTools = [
  {
    strToolName: "realsteamonmac-gptk",
    strDisplayName: "RealSteamOnMac - GPTK 3",
    renderer: "gptk",
  },
  {
    strToolName: "realsteamonmac-dxmt",
    strDisplayName: "RealSteamOnMac - DXMT 0.80",
    renderer: "dxmt",
  },
  {
    strToolName: "realsteamonmac-dxvk",
    strDisplayName: "RealSteamOnMac - DXVK macOS 1.10.3",
    renderer: "dxvk",
  },
  {
    strToolName: "realsteamonmac-wined3d",
    strDisplayName: "RealSteamOnMac - WineD3D 11.10",
    renderer: "wined3d",
  },
];

test("discovers Steam popup documents tracked by the shared context", () => {
  const mainDocument = { title: "Steam" };
  const propertiesDocument = { title: "People Playground" };
  const closedDocument = { title: "Closed" };

  assert.deepEqual(
    getSteamUIDocuments({
      SteamUIStore: {
        WindowStore: {
          SteamUIWindows: [
            { m_BrowserWindow: { document: mainDocument } },
          ],
          MainWindowInstance: {
            m_BrowserWindow: { document: mainDocument },
          },
        },
      },
      g_FriendsUIApp: {
        m_IdleTracker: {
          m_rgWindows: [
            { document: mainDocument, closed: false },
            { document: propertiesDocument, closed: false },
            { document: closedDocument, closed: true },
          ],
        },
      },
    }),
    [mainDocument, propertiesDocument],
  );
});

test("maps compatibility tools to runtime renderers in both directions", () => {
  assert.equal(
    rendererForCompatTool("realsteamonmac-dxvk", projectTools),
    "dxvk",
  );
  assert.equal(
    compatToolForRenderer("wined3d", projectTools),
    "realsteamonmac-wined3d",
  );
  assert.equal(rendererForCompatTool("unknown", projectTools), null);
});

test("normalizes controls and disables GPTK-only features elsewhere", () => {
  assert.deepEqual(
    normalizeControlConfig({
      renderer: "dxmt",
      msync: false,
      retina: true,
      metal_hud: true,
      metalfx: true,
      dxr: true,
      avx: true,
    }),
    {
      renderer: "dxmt",
      msync: false,
      retina: true,
      metal_hud: true,
      metalfx: false,
      dxr: false,
      avx: true,
    },
  );
});

test("builds the fixed native control request shape", () => {
  assert.equal(
    buildControlPayload({
      renderer: "gptk",
      msync: true,
      retina: false,
      metal_hud: true,
      metalfx: true,
      dxr: false,
      avx: true,
    }),
    "renderer=gptk&msync=1&retina=0&metal_hud=1&" +
      "metalfx=1&dxr=0&avx=1",
  );
  assert.equal(
    buildControlUrl(
      "http://127.0.0.1:57344/config",
      "0123456789abcdef",
      1118200,
    ),
    "http://127.0.0.1:57344/config" +
      "?token=0123456789abcdef&appid=1118200",
  );
});

function gameOverview(appid, overrides = {}) {
  return {
    appid,
    app_type: 1,
    subscribed_to: true,
    visible_in_game_list: true,
    ...overrides,
  };
}

function gameDetails(appid, platforms = ["windows"]) {
  return {
    unAppID: appid,
    vecPlatforms: platforms,
  };
}

test("identifies an owned visible Windows-only game", () => {
  assert.equal(
    isOwnedWindowsOnlyGame(
      gameOverview(1118200),
      gameDetails(1118200),
    ),
    true,
  );
});

for (const [label, overview, details] of [
  [
    "dual-platform game",
    gameOverview(4000),
    gameDetails(4000, ["windows", "osx", "linux"]),
  ],
  [
    "macOS-only game",
    gameOverview(275850),
    gameDetails(275850, ["osx"]),
  ],
  [
    "tool",
    gameOverview(228980, { app_type: 4 }),
    gameDetails(228980),
  ],
  [
    "unsubscribed game",
    gameOverview(42, { subscribed_to: false }),
    gameDetails(42),
  ],
  [
    "hidden game",
    gameOverview(43, { visible_in_game_list: false }),
    gameDetails(43),
  ],
  [
    "mismatched details",
    gameOverview(44),
    gameDetails(45),
  ],
]) {
  test(`excludes a ${label}`, () => {
    assert.equal(isOwnedWindowsOnlyGame(overview, details), false);
  });
}

test("builds a managed registry and removes entries that stop qualifying", () => {
  const detailsByAppid = new Map([
    [1118200, gameDetails(1118200)],
    [4000, gameDetails(4000, ["windows", "osx", "linux"])],
  ]);
  assert.deepEqual(
    buildManagedAppSet(
      [gameOverview(1118200), gameOverview(4000)],
      detailsByAppid,
    ),
    new Set([1118200]),
  );

  assert.deepEqual(
    buildManagedAppSet(
      [gameOverview(1118200, { subscribed_to: false })],
      detailsByAppid,
    ),
    new Set(),
  );
});

test("discovers newly added Windows-only games through the detail loader", async () => {
  const loaded = [];
  const result = await discoverManagedApps({
    overviews: [
      gameOverview(1118200),
      gameOverview(990080),
      gameOverview(4000),
      gameOverview(228980, { app_type: 4 }),
    ],
    loadDetails: async (appid) => {
      loaded.push(appid);
      if (appid === 4000) {
        return gameDetails(appid, ["windows", "osx", "linux"]);
      }
      return gameDetails(appid);
    },
  });

  assert.deepEqual(loaded, [1118200, 990080, 4000]);
  assert.deepEqual(result, new Set([1118200, 990080]));
});

test("rejects an incomplete discovery scan instead of removing known apps", async () => {
  await assert.rejects(
    discoverManagedApps({
      overviews: [gameOverview(1118200), gameOverview(990080)],
      loadDetails: async (appid) =>
        appid === 1118200 ? gameDetails(appid) : null,
    }),
    /missing Steam app details for AppID 990080/,
  );
});

test("merges project tools without duplicating native tools", () => {
  assert.deepEqual(
    mergeCompatTools(
      [
        {
          strToolName: "native-tool",
          strDisplayName: "Native Tool",
        },
      ],
      [
        {
          strToolName: "realsteamonmac-experimental",
          strDisplayName: "RealSteamOnMac Experimental",
        },
        {
          strToolName: "native-tool",
          strDisplayName: "Project Override",
        },
      ],
    ),
    [
      {
        strToolName: "native-tool",
        strDisplayName: "Native Tool",
      },
      {
        strToolName: "realsteamonmac-experimental",
        strDisplayName: "RealSteamOnMac Experimental",
      },
    ],
  );
});

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

test("normalizes an installed backend-ready app to ready-to-launch", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: true,
      detailsStatus: 11,
      overviewStatus: 14,
      hasAnyLocalContent: true,
    }),
    { normalize: true },
  );
});

for (const detailsStatus of [3, 7, 9, 11, 19, 35]) {
  test(`mirrors authoritative native status ${detailsStatus}`, () => {
    assert.deepEqual(
      decideOverviewPatch({
        allowlisted: true,
        detailsStatus,
        overviewStatus: 14,
        hasAnyLocalContent: detailsStatus !== 9,
      }),
      { normalize: true },
    );
  });
}

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

test("does not change an app before the native registry is synchronized", () => {
  assert.deepEqual(
    decideOverviewPatch({
      allowlisted: false,
      detailsStatus: 9,
      overviewStatus: 14,
      hasAnyLocalContent: true,
    }),
    { normalize: false },
  );
});

for (const overviewStatus of [3, 4, 5, 7, 9, 10, 11, 12, 13, 19, 35]) {
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

test("uses a bounded retry interval for stale native detail caches", () => {
  assert.equal(DETAILS_REFRESH_INTERVAL_MS, 1000);
});

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

test("normalizes an installed shared app store object to ready-to-launch", () => {
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
    eDisplayStatus: 11,
    bHasAnyLocalContent: true,
  };

  assert.equal(
    reconcileAppState({
      overview,
      details,
      allowlist: new Set([1118200]),
      originalStates: new WeakMap(),
    }),
    "normalized",
  );
  assert.equal(selected.display_status, 11);
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

test("does not repeatedly normalize an already synchronized overview", () => {
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
      eDisplayStatus: 11,
      bHasAnyLocalContent: true,
    },
    allowlist: new Set([1118200]),
    originalStates: new WeakMap(),
  };

  assert.equal(reconcileAppState(state), "normalized");
  assert.equal(reconcileAppState(state), "unchanged");
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

test("mirrors an allowlisted selected compatibility tool into app details", () => {
  const details = {
    unAppID: 1118200,
    strCompatToolName: "",
    strCompatToolDisplayName: "",
    nCompatToolPriority: 0,
  };
  const originalCompatStates = new WeakMap();

  assert.equal(
    reconcileCompatDetails({
      details,
      allowlist: new Set([1118200]),
      selectedTool: "realsteamonmac-experimental",
      availableTools: [
        {
          strToolName: "realsteamonmac-experimental",
          strDisplayName: "RealSteamOnMac Experimental",
        },
      ],
      originalCompatStates,
    }),
    "normalized",
  );
  assert.equal(details.strCompatToolName, "realsteamonmac-experimental");
  assert.equal(
    details.strCompatToolDisplayName,
    "RealSteamOnMac Experimental",
  );
  assert.equal(details.nCompatToolPriority, 250);
});

test("restores compatibility details when the allowlisted selection is cleared", () => {
  const details = {
    unAppID: 1118200,
    strCompatToolName: "",
    strCompatToolDisplayName: "",
    nCompatToolPriority: 0,
  };
  const originalCompatStates = new WeakMap();
  const state = {
    details,
    allowlist: new Set([1118200]),
    selectedTool: "realsteamonmac-experimental",
    availableTools: [
      {
        strToolName: "realsteamonmac-experimental",
        strDisplayName: "RealSteamOnMac Experimental",
      },
    ],
    originalCompatStates,
  };
  reconcileCompatDetails(state);

  state.selectedTool = "";
  assert.equal(reconcileCompatDetails(state), "restored");
  assert.equal(details.strCompatToolName, "");
  assert.equal(details.strCompatToolDisplayName, "");
  assert.equal(details.nCompatToolPriority, 0);
});

test("does not mirror compatibility state for a non-allowlisted app", () => {
  const details = {
    unAppID: 42,
    strCompatToolName: "",
    strCompatToolDisplayName: "",
    nCompatToolPriority: 0,
  };

  assert.equal(
    reconcileCompatDetails({
      details,
      allowlist: new Set([1118200]),
      selectedTool: "realsteamonmac-experimental",
      availableTools: [
        {
          strToolName: "realsteamonmac-experimental",
          strDisplayName: "RealSteamOnMac Experimental",
        },
      ],
      originalCompatStates: new WeakMap(),
    }),
    "unchanged",
  );
  assert.equal(details.strCompatToolName, "");
});

test("restores mirrored compatibility state when an app leaves the registry", () => {
  const details = {
    unAppID: 1118200,
    strCompatToolName: "",
    strCompatToolDisplayName: "",
    nCompatToolPriority: 0,
  };
  const originalCompatStates = new WeakMap();
  reconcileCompatDetails({
    details,
    allowlist: new Set([1118200]),
    selectedTool: "realsteamonmac-experimental",
    availableTools: [
      {
        strToolName: "realsteamonmac-experimental",
        strDisplayName: "RealSteamOnMac Experimental",
      },
    ],
    originalCompatStates,
  });

  assert.equal(
    reconcileCompatDetails({
      details,
      allowlist: new Set(),
      selectedTool: "",
      availableTools: [],
      originalCompatStates,
    }),
    "restored",
  );
  assert.equal(details.strCompatToolName, "");
  assert.equal(details.strCompatToolDisplayName, "");
  assert.equal(details.nCompatToolPriority, 0);
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
