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
    overview(1118200, {
      size_on_disk: "455945761",
      selected_per_client_data: {
        display_status: 14,
        is_available_on_current_platform: false,
        is_invalid_os_type: true,
        installed: true,
      },
    }),
    overview(990080),
    overview(4000),
  ];
  const detailsByAppid = new Map([
    [1118200, details(1118200)],
    [990080, details(990080)],
    [4000, details(4000, ["windows", "osx", "linux"])],
  ]);
  const nativeSpecifyCalls = [];
  let rejectedNativeTool = null;
  const nativeDetailRegistrations = [];
  const nativeDetailUnregistrations = [];
  const nativeDetailCallbacks = new Map();
  const nativeRepairCalls = [];
  const registryRequests = [];
  const controlRequests = [];
  const actionRequests = [];
  const actionJobs = new Map();
  let nextActionJob = 0;
  const intervalCallbacks = new Map();
  const storage = new Map();
  function allocateActionJob(appid, action, result) {
    nextActionJob += 1;
    const jobId = nextActionJob.toString(16).padStart(32, "0");
    actionJobs.set(jobId, {
      schema: 1,
      appid,
      job_id: jobId,
      action,
      state: "completed",
      result,
    });
    return jobId;
  }
  const context = vm.createContext({
    __REALSTEAMONMAC_CONFIG__: Object.freeze({
      appids: [1118200],
      defaultCompatTool: "realsteamonmac-dxmt",
      registryEndpoint: "http://127.0.0.1:57344/registry",
      controlEndpoint: "http://127.0.0.1:57344/config",
      actionEndpoint: "http://127.0.0.1:57344/action",
      jobEndpoint: "http://127.0.0.1:57344/job",
      registryToken: "0123456789abcdef0123456789abcdef",
      compatTools: [
        {
          strToolName: "realsteamonmac-gptk",
          strDisplayName: "RealSteamOnMac - GPTK 3",
          renderer: "gptk",
          capabilities: {
            msync: true, retina: true, metal_hud: true,
            metalfx: true, dxr: true, avx: true,
          },
        },
        {
          strToolName: "realsteamonmac-dxmt",
          strDisplayName: "RealSteamOnMac - DXMT 0.80",
          renderer: "dxmt",
          capabilities: {
            msync: true, retina: true, metal_hud: true,
            metalfx: true, dxr: false, avx: true,
          },
        },
        {
          strToolName: "realsteamonmac-dxvk",
          strDisplayName: "RealSteamOnMac - DXVK macOS 1.10.3",
          renderer: "dxvk",
          capabilities: {
            msync: true, retina: true, metal_hud: true,
            metalfx: false, dxr: false, avx: true,
          },
        },
        {
          strToolName: "realsteamonmac-wined3d",
          strDisplayName: "RealSteamOnMac - WineD3D 11.10",
          renderer: "wined3d",
          capabilities: {
            msync: true, retina: true, metal_hud: false,
            metalfx: false, dxr: false, avx: true,
          },
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
      AppDetailsChanged(nextDetails) {
        detailsByAppid.set(nextDetails.unAppID, nextDetails);
      },
    },
    SteamClient: {
      Apps: {
        async GetAvailableCompatTools() {
          return [
            {
              strToolName: "proton-native",
              strDisplayName: "Native Proton",
            },
          ];
        },
        async SpecifyCompatTool(appid, tool) {
          if (tool === rejectedNativeTool) {
            throw new Error(`native compatibility tool rejected: ${tool}`);
          }
          nativeSpecifyCalls.push([appid, tool]);
        },
        RegisterForAppDetails(appid, callback) {
          nativeDetailRegistrations.push(appid);
          nativeDetailCallbacks.set(appid, callback);
          const nextDetails = {
            ...detailsByAppid.get(appid),
            eDisplayStatus: appid === 1118200 ? 11 : 9,
            bHasAnyLocalContent: appid === 1118200,
          };
          callback(nextDetails);
          return {
            unregister() {
              nativeDetailUnregistrations.push(appid);
            },
          };
        },
        async VerifyApp(appid) {
          nativeRepairCalls.push(["verify", appid]);
          return { nGameActionID: 17 };
        },
      },
      Downloads: {
        async ResumeAppUpdate(appid, clientid) {
          nativeRepairCalls.push(["resume", appid, clientid]);
        },
      },
      Installs: {
        async OpenInstallWizard(appids) {
          nativeRepairCalls.push(["install", [...appids]]);
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
    setInterval(callback, delay) {
      intervalCallbacks.set(delay, callback);
      return 1;
    },
    async fetch(url, options) {
      if (url.startsWith("http://127.0.0.1:57344/action")) {
        actionRequests.push({ url, options });
        const appid = Number(new URL(url).searchParams.get("appid"));
        const fields = new URLSearchParams(options.body);
        assert.equal(fields.get("action"), "inspect-state");
        const result =
          appid === 1118200
            ? {
                installed: true,
                container_exists: true,
                manifest_diagnostic: "ready",
                install_path_nonempty: true,
                size_on_disk: 455945761,
              }
            : {
                installed: false,
                container_exists: false,
                manifest_diagnostic: "manifest-missing",
                install_path_nonempty: false,
                size_on_disk: 0,
              };
        const jobId = allocateActionJob(appid, "inspect-state", result);
        return {
          ok: true,
          async json() {
            return { job_id: jobId };
          },
        };
      }
      if (url.startsWith("http://127.0.0.1:57344/job")) {
        const jobId = new URL(url).searchParams.get("job");
        const job = actionJobs.get(jobId);
        return {
          ok: true,
          async json() {
            return job;
          },
        };
      }
      if (url.startsWith("http://127.0.0.1:57344/config")) {
        controlRequests.push({ url, options });
        if (options.method === "GET") {
          return {
            ok: true,
            async json() {
              return {
                compat_tool: "realsteamonmac-dxmt",
                renderer: "dxmt",
                msync: true,
                retina: false,
                metal_hud: false,
                metalfx: false,
                dxr: false,
                avx: false,
              };
            },
          };
        }
        return { ok: true, status: 204 };
      }
      registryRequests.push({ url, options });
      if (registryRequests.length === 1) {
        throw new Error("registry server is not ready");
      }
      return {};
    },
    console,
  });

  vm.runInContext(source, context);

  assert.equal(
    typeof context.__REALSTEAMONMAC_IS_MANAGED_APP__,
    "function",
  );
  assert.equal(
    typeof context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__,
    "function",
  );
  assert.equal(context.__REALSTEAMONMAC_UI_STATUS__.version, 15);
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(1118200), true);
  assert.equal(
    context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__(1118200),
    "realsteamonmac-dxmt",
  );

  await waitFor(
    () =>
      context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 1 &&
      context.__REALSTEAMONMAC_UI_STATUS__.appids.length === 2,
  );
  assert.deepEqual(
    [...context.__REALSTEAMONMAC_UI_STATUS__.appids],
    [990080, 1118200],
  );
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(990080), true);
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(4000), false);
  assert.equal(
    context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__(990080),
    "realsteamonmac-dxmt",
  );
  assert.equal(registryRequests.length, 1);
  assert.equal(
    context.__REALSTEAMONMAC_UI_STATUS__.registryNativeSyncs,
    0,
  );
  assert.match(
    context.__REALSTEAMONMAC_UI_STATUS__.registryLastNativeSyncError,
    /registry server is not ready/,
  );

  await intervalCallbacks.get(5000)();
  await waitFor(
    () => context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 2,
  );
  assert.equal(registryRequests.length, 2);
  assert.equal(
    context.__REALSTEAMONMAC_UI_STATUS__.registryNativeSyncs,
    1,
  );
  assert.equal(
    context.__REALSTEAMONMAC_UI_STATUS__.registryLastNativeSyncError,
    null,
  );
  assert.deepEqual(
    [...nativeDetailRegistrations].sort((left, right) => left - right),
    [990080, 1118200],
  );
  assert.equal(
    context.__REALSTEAMONMAC_UI_STATUS__.nativeDetailsSubscriptions,
    2,
  );
  assert.equal(detailsByAppid.get(990080).eDisplayStatus, 9);
  assert.equal(detailsByAppid.get(1118200).eDisplayStatus, 11);
  assert.equal(
    overviews[0].selected_per_client_data.display_status,
    11,
  );
  assert.equal(
    overviews[1].selected_per_client_data.display_status,
    9,
  );
  assert.deepEqual(nativeSpecifyCalls, []);
  const scansBeforeNativeDetailCallback =
    context.__REALSTEAMONMAC_UI_STATUS__.scans;
  nativeDetailCallbacks.get(1118200)({
    ...detailsByAppid.get(1118200),
    eDisplayStatus: 11,
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(
    context.__REALSTEAMONMAC_UI_STATUS__.scans,
    scansBeforeNativeDetailCallback,
  );
  assert.equal(
    registryRequests[1].url,
    "http://127.0.0.1:57344/registry" +
      "?token=0123456789abcdef0123456789abcdef",
  );
  assert.equal(registryRequests[1].options.method, "POST");
  assert.equal(registryRequests[1].options.mode, "no-cors");
  assert.equal(registryRequests[1].options.body, "990080,1118200");
  assert.equal(
    typeof context.__REALSTEAMONMAC_REQUEST_REPAIR__,
    "function",
  );
  assert.equal(
    await context.__REALSTEAMONMAC_REQUEST_REPAIR__(990080),
    "install",
  );
  assert.equal(
    await context.__REALSTEAMONMAC_REQUEST_REPAIR__(1118200),
    "verify",
  );
  assert.deepEqual(nativeRepairCalls, [
    ["install", [990080]],
    ["verify", 1118200],
  ]);
  assert.deepEqual(
    actionRequests.map((request) => [
      Number(new URL(request.url).searchParams.get("appid")),
      request.options.body,
    ]),
    [
      [990080, "action=inspect-state"],
      [1118200, "action=inspect-state"],
    ],
  );
  await assert.rejects(
    context.__REALSTEAMONMAC_REQUEST_REPAIR__(4000),
    /not managed/,
  );

  const tools =
    await context.SteamClient.Apps.GetAvailableCompatTools(990080);
  assert.equal(tools.length, 5);
  assert.equal(tools[0].strToolName, "proton-native");
  assert.equal(
    tools.some((tool) => tool.strToolName === "realsteamonmac-dxmt"),
    true,
  );

  await context.SteamClient.Apps.SpecifyCompatTool(
    990080,
    "realsteamonmac-dxvk",
  );
  assert.deepEqual(nativeSpecifyCalls, []);
  assert.equal(
    context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__(990080),
    "realsteamonmac-dxvk",
  );
  assert.equal(controlRequests.at(-1).options.method, "POST");
  assert.equal(
    controlRequests.at(-1).options.body,
    "compat_tool=realsteamonmac-dxvk&renderer=dxvk&" +
      "msync=1&retina=0&metal_hud=0&" +
      "metalfx=0&dxr=0&avx=0",
  );

  const controlRequestCount = controlRequests.length;
  rejectedNativeTool = "proton-native";
  await assert.rejects(
    context.SteamClient.Apps.SpecifyCompatTool(
      990080,
      "proton-native",
    ),
    /native compatibility tool rejected/,
  );
  assert.equal(
    context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__(990080),
    "realsteamonmac-dxvk",
  );
  assert.equal(controlRequests.length, controlRequestCount);
  rejectedNativeTool = null;

  const controlRequestsBeforeDisable = controlRequests.length;
  await context.SteamClient.Apps.SpecifyCompatTool(990080, "");
  assert.deepEqual(nativeSpecifyCalls.at(-1), [990080, ""]);
  assert.equal(controlRequests.length, controlRequestsBeforeDisable);
  assert.equal(
    context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__(990080),
    "",
  );

  const initializedOverviews = [...overviews];
  overviews.splice(0, overviews.length);
  await intervalCallbacks.get(5000)();
  await waitFor(
    () => context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 3,
  );
  assert.equal(
    context.__REALSTEAMONMAC_IS_MANAGED_APP__(990080),
    true,
  );
  assert.equal(
    context.__REALSTEAMONMAC_IS_MANAGED_APP__(1118200),
    true,
  );
  assert.equal(registryRequests.length, 2);
  assert.deepEqual(nativeDetailUnregistrations, []);
  assert.match(
    context.__REALSTEAMONMAC_UI_STATUS__.registryLastError,
    /overview store is not initialized/,
  );

  overviews.push(...initializedOverviews);
  await intervalCallbacks.get(5000)();
  await waitFor(
    () => context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 4,
  );
  assert.equal(registryRequests.length, 2);
  assert.deepEqual(nativeDetailUnregistrations, []);

  overviews[1].subscribed_to = false;
  await intervalCallbacks.get(5000)();
  await waitFor(
    () => context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 5,
  );
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(990080), false);
  assert.deepEqual(nativeDetailUnregistrations, [990080]);
  assert.equal(
    context.__REALSTEAMONMAC_UI_STATUS__.nativeDetailsSubscriptions,
    1,
  );

  overviews[1].subscribed_to = true;
  await intervalCallbacks.get(5000)();
  await waitFor(
    () => context.__REALSTEAMONMAC_UI_STATUS__.registryScans === 6,
  );
  assert.equal(context.__REALSTEAMONMAC_IS_MANAGED_APP__(990080), true);
  assert.equal(
    context.__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__(990080),
    "",
  );
});

function loadRuntimeHelpers() {
  const module = { exports: {} };
  vm.runInNewContext(source, {
    module,
    exports: module.exports,
  });
  return module.exports;
}

test("does not activate or export the legacy replacement compatibility panel", () => {
  const helpers = loadRuntimeHelpers();

  assert.equal(helpers.buildControlPanelMarkup, undefined);
  assert.doesNotMatch(source, /\n\s+mountControlPanels\(\);/);
  assert.doesNotMatch(source, /function mountControlPanels\(/);
});
