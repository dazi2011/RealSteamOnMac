import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = fs.readFileSync(
  new URL("../ui/realsteamonmac_ui.js", import.meta.url),
  "utf8",
);

function overview(appid, overrides = {}) {
  return {
    appid,
    app_type: 1,
    subscribed_to: true,
    visible_in_game_list: true,
    selected_per_client_data: {
      display_status: 14,
      is_available_on_current_platform: false,
      is_invalid_os_type: true,
    },
    ...overrides,
  };
}

function details(appid, platforms = ["windows"]) {
  return {
    unAppID: appid,
    vecPlatforms: platforms,
    eDisplayStatus: 14,
    bHasAnyLocalContent: false,
    strCompatToolName: "",
    strCompatToolDisplayName: "",
    nCompatToolPriority: 0,
  };
}

async function waitFor(predicate) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (predicate()) {
      return;
    }
    await new Promise((resolve) => setImmediate(resolve));
  }
  assert.fail("timed out waiting for Steam UI runtime");
}

test("installs the predicate before dynamically replacing the bootstrap registry", async () => {
  const overviews = [
    overview(1118200),
    overview(990080),
    overview(4000),
  ];
  const detailsByAppid = new Map([
    [1118200, details(1118200)],
    [990080, details(990080)],
    [4000, details(4000, ["windows", "osx", "linux"])],
  ]);
  const nativeSpecifyCalls = [];
  const storage = new Map();
  const context = vm.createContext({
    __REALSTEAMONMAC_CONFIG__: Object.freeze({
      appids: [1118200],
      defaultCompatTool: "realsteamonmac-experimental",
      compatTools: [
        {
          strToolName: "realsteamonmac-experimental",
          strDisplayName: "RealSteamOnMac Experimental",
        },
      ],
    }),
    appStore: {
      allApps: overviews,
      GetAppOverviewByAppID(appid) {
        return overviews.find((entry) => entry.appid === appid) ?? null;
      },
    },
    appDetailsStore: {
      GetAppDetails(appid) {
        return detailsByAppid.get(appid) ?? null;
      },
      async RequestAppDetails(appid) {
        return detailsByAppid.get(appid) ?? null;
      },
    },
    SteamClient: {
      Apps: {
        async GetAvailableCompatTools() {
          return [];
        },
        async SpecifyCompatTool(appid, tool) {
          nativeSpecifyCalls.push([appid, tool]);
        },
      },
    },
    SteamUIStore: {
      WindowStore: {
        SteamUIWindows: [],
        MainWindowInstance: null,
      },
    },
    localStorage: {
      getItem(key) {
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        storage.set(key, value);
      },
    },
    setInterval() {
      return 1;
    },
    console,
  });

  vm.runInContext(source, context);

  assert.equal(
    typeof context.__REALSTEAMONMAC_IS_MANAGED_APP__,
    "function",
  );
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(1118200), true);

  await waitFor(
    () => context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 1,
  );
  assert.deepEqual(
    [...context.__REALSTEAMONMAC_UI_STATUS__.appids],
    [990080, 1118200],
  );
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(990080), true);
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(4000), false);

  const tools =
    await context.SteamClient.Apps.GetAvailableCompatTools(990080);
  assert.equal(tools.length, 1);
  assert.equal(
    tools[0].strToolName,
    "realsteamonmac-experimental",
  );

  await context.SteamClient.Apps.SpecifyCompatTool(
    990080,
    "realsteamonmac-experimental",
  );
  assert.deepEqual(nativeSpecifyCalls, []);
});
