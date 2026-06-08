#!/usr/bin/env node

import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";

export function selectSharedContextTarget(targets) {
  return selectTarget(targets, {
    title: "SharedJSContext",
    urlIncludes: "IN_STEAMUI_SHARED_CONTEXT=true",
    description: "Steam SharedJSContext",
  });
}

export function selectTarget(
  targets,
  { title, urlIncludes, description = "Steam CDP" } = {},
) {
  const target = targets.find((candidate) => {
    if (title && candidate.title === title) return true;
    if (urlIncludes && candidate.url?.includes(urlIncludes)) return true;
    return false;
  });

  if (!target?.webSocketDebuggerUrl) {
    throw new Error(`${description} target was not found`);
  }

  return target;
}

export async function evaluateExpression(target, expression) {
  const socket = new WebSocket(target.webSocketDebuggerUrl);

  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener(
      "error",
      () => reject(new Error("failed to connect to Steam CDP target")),
      { once: true },
    );
  });

  const id = 1;
  const response = await new Promise((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error("Steam CDP evaluation timed out")),
      15_000,
    );

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id !== id) return;
      clearTimeout(timeout);
      resolve(message);
    });

    socket.send(
      JSON.stringify({
        id,
        method: "Runtime.evaluate",
        params: {
          expression,
          awaitPromise: true,
          returnByValue: true,
        },
      }),
    );
  });

  socket.close();

  if (response.error) {
    throw new Error(response.error.message);
  }
  if (response.result?.exceptionDetails) {
    const detail =
      response.result.exceptionDetails.exception?.description ??
      response.result.exceptionDetails.text;
    throw new Error(detail);
  }

  return response.result?.result?.value;
}

async function main() {
  const args = process.argv.slice(2);
  const endpointIndex = args.indexOf("--endpoint");
  const expressionFileIndex = args.indexOf("--expression-file");
  const targetTitleIndex = args.indexOf("--target-title");
  const targetUrlIndex = args.indexOf("--target-url-contains");
  const endpoint =
    endpointIndex >= 0 ? args[endpointIndex + 1] : "http://127.0.0.1:8080";

  if (expressionFileIndex < 0 || !args[expressionFileIndex + 1]) {
    throw new Error(
      "usage: steam_cdp.mjs --expression-file PATH [--endpoint URL] " +
        "[--target-title TITLE | --target-url-contains TEXT]",
    );
  }
  if (targetTitleIndex >= 0 && targetUrlIndex >= 0) {
    throw new Error("--target-title and --target-url-contains are mutually exclusive");
  }

  const expression = await fs.readFile(args[expressionFileIndex + 1], "utf8");
  const response = await fetch(`${endpoint}/json/list`);
  if (!response.ok) {
    throw new Error(`Steam CDP target request failed: HTTP ${response.status}`);
  }

  const targets = await response.json();
  const target =
    targetTitleIndex >= 0
      ? selectTarget(targets, {
          title: args[targetTitleIndex + 1],
          description: `Steam target titled ${args[targetTitleIndex + 1]}`,
        })
      : targetUrlIndex >= 0
        ? selectTarget(targets, {
            urlIncludes: args[targetUrlIndex + 1],
            description: `Steam target containing URL ${args[targetUrlIndex + 1]}`,
          })
        : selectSharedContextTarget(targets);
  const result = await evaluateExpression(target, expression);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
