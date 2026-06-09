#!/usr/bin/env node

import { pathToFileURL } from "node:url";

import {
  evaluateExpression,
  selectSharedContextTarget,
} from "./steam_cdp.mjs";

const TOOL_BY_RENDERER = Object.freeze({
  gptk: "realsteamonmac-gptk",
  dxmt: "realsteamonmac-dxmt",
  dxvk: "realsteamonmac-dxvk",
  wined3d: "realsteamonmac-wined3d",
});

export function buildRendererSelectionExpression(renderer) {
  const toolName = TOOL_BY_RENDERER[renderer];
  if (!toolName) {
    throw new Error(`unsupported renderer: ${renderer}`);
  }
  return `(async () => {
    const appid = 1118200;
    const renderer = ${JSON.stringify(renderer)};
    const toolName = ${JSON.stringify(toolName)};
    if (globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__?.(appid) !== true) {
      throw new Error("People Playground is not in the managed registry");
    }
    const availableTools = JSON.parse(JSON.stringify(
      await SteamClient.Apps.GetAvailableCompatTools(appid)
    ));
    if (!availableTools.some((tool) => tool?.strToolName === toolName)) {
      throw new Error("requested project renderer is unavailable");
    }
    await SteamClient.Apps.SpecifyCompatTool(appid, toolName);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const controls = JSON.parse(
      localStorage.getItem("__REALSTEAMONMAC_CONTROL_CONFIGS_V1__") ?? "{}"
    );
    const selections = JSON.parse(
      localStorage.getItem("__REALSTEAMONMAC_COMPAT_SELECTIONS_V1__") ?? "{}"
    );
    return {
      appid,
      renderer,
      toolName,
      storedTool: selections[String(appid)] ?? null,
      storedControl: controls[String(appid)] ?? null,
      status: globalThis.__REALSTEAMONMAC_UI_STATUS__ ?? null,
    };
  })()`;
}

async function main() {
  const args = process.argv.slice(2);
  const rendererIndex = args.indexOf("--renderer");
  const endpointIndex = args.indexOf("--endpoint");
  const renderer =
    rendererIndex >= 0 ? args[rendererIndex + 1] : null;
  const endpoint =
    endpointIndex >= 0
      ? args[endpointIndex + 1]
      : "http://127.0.0.1:8080";
  if (!renderer) {
    throw new Error(
      "usage: select_people_playground_renderer.mjs " +
        "--renderer gptk|dxmt|dxvk|wined3d [--endpoint URL]",
    );
  }

  const response = await fetch(`${endpoint}/json/list`);
  if (!response.ok) {
    throw new Error(
      `Steam CDP target request failed: HTTP ${response.status}`,
    );
  }
  const target = selectSharedContextTarget(await response.json());
  const result = await evaluateExpression(
    target,
    buildRendererSelectionExpression(renderer),
  );
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
