(async () => {
  const appid = 1118200;
  const readyToInstallStatus = 9;
  const candidates = [];

  for (const element of document.querySelectorAll("[role=button], button")) {
    const text = element.innerText?.trim() ?? "";
    if (!/^(安装|Install)$/.test(text)) {
      continue;
    }

    const fiberKey = Object.getOwnPropertyNames(element).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    let fiber = fiberKey ? element[fiberKey] : null;
    let overview = null;
    let details = null;
    for (let depth = 0; fiber && depth < 40; depth += 1) {
      overview ??= fiber.memoizedProps?.overview ?? null;
      details ??= fiber.memoizedProps?.details ?? null;
      fiber = fiber.return;
    }
    if (overview?.appid !== appid || details?.unAppID !== appid) {
      continue;
    }

    const selected =
      overview.GetPerClientData?.("selected") ??
      overview.selected_per_client_data ??
      overview.per_client_data?.find(
        (entry) => entry.clientid === overview.selected_clientid,
      );
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    if (
      selected?.display_status === readyToInstallStatus &&
      details.eDisplayStatus === readyToInstallStatus &&
      style.pointerEvents === "auto" &&
      style.backgroundImage.includes("linear-gradient") &&
      rect.width > 0 &&
      rect.height > 0
    ) {
      candidates.push(element);
    }
  }

  if (candidates.length !== 1) {
    throw new Error(
      `expected one visible native People Playground install button, found ${candidates.length}`,
    );
  }

  candidates[0].click();
  await new Promise((resolve) => setTimeout(resolve, 1500));

  return {
    appid,
    clicked: true,
    buttonText: candidates[0].innerText?.trim() ?? "",
    route: globalThis.location?.href ?? null,
  };
})()
