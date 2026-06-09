import assert from "node:assert/strict";
import test from "node:test";

import {
  selectSharedContextTarget,
  selectTarget,
} from "../script/steam_cdp.mjs";
import {
  buildRendererSelectionExpression,
} from "../script/select_people_playground_renderer.mjs";

test("selects the Steam shared JavaScript context", () => {
  const targets = [
    { title: "Steam", url: "about:blank", webSocketDebuggerUrl: "ws://main" },
    {
      title: "SharedJSContext",
      url: "https://steamloopback.host/index.html?IN_STEAMUI_SHARED_CONTEXT=true&PLATFORM=macos",
      webSocketDebuggerUrl: "ws://shared",
    },
  ];

  assert.equal(selectSharedContextTarget(targets).webSocketDebuggerUrl, "ws://shared");
});

test("rejects a target list without the shared context", () => {
  assert.throws(
    () => selectSharedContextTarget([{ title: "Steam", url: "about:blank" }]),
    /SharedJSContext/,
  );
});

test("selects a Steam target by exact title", () => {
  const targets = [
    { title: "SharedJSContext", url: "https://steamloopback.host/" },
    { title: "Steam", url: "about:blank", webSocketDebuggerUrl: "ws://main" },
  ];

  assert.equal(
    selectTarget(targets, { title: "Steam" }).webSocketDebuggerUrl,
    "ws://main",
  );
});

test("selects a Steam target by URL fragment", () => {
  const targets = [
    {
      title: "tracking",
      url: "data:text/html,tracking:/library/app/1118200",
      webSocketDebuggerUrl: "ws://tracking",
    },
  ];

  assert.equal(
    selectTarget(targets, { urlIncludes: "/library/app/1118200" })
      .webSocketDebuggerUrl,
    "ws://tracking",
  );
});

test("builds a People Playground renderer selection with fixed scope", () => {
  const expression = buildRendererSelectionExpression("dxvk");

  assert.match(expression, /const appid = 1118200;/);
  assert.match(expression, /realsteamonmac-dxvk/);
  assert.match(expression, /__REALSTEAMONMAC_IS_MANAGED_APP__/);
  assert.match(expression, /SpecifyCompatTool\(appid, toolName\)/);
});

test("rejects an unknown People Playground renderer", () => {
  assert.throws(
    () => buildRendererSelectionExpression("arbitrary"),
    /unsupported renderer/,
  );
});
