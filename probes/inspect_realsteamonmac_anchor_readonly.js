(() => {
  const panel = document.querySelector(".realsteamonmac-controls");
  const anchor = panel?.previousElementSibling ?? null;
  const rows = [];
  const inspect = (element, label) => {
    const fiberKey = Object.getOwnPropertyNames(element ?? {}).find(
      (key) =>
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );
    let fiber = fiberKey ? element[fiberKey] : null;
    for (let depth = 0; fiber && depth < 40; depth += 1) {
      const props = fiber.memoizedProps ?? fiber.pendingProps ?? null;
      const candidates = [
        props?.appid,
        props?.unAppID,
        props?.overview?.appid,
        props?.details?.unAppID,
        props?.app?.appid,
        props?.app?.unAppID,
      ]
        .map(Number)
        .filter((value) => Number.isSafeInteger(value) && value > 0);
      if (candidates.length) {
        rows.push({
          label,
          depth,
          candidates,
          propKeys:
            props && typeof props === "object"
              ? Object.keys(props).slice(0, 30)
              : [],
        });
      }
      fiber = fiber.return;
    }
  };

  inspect(anchor, "anchor");
  inspect(panel?.parentElement, "panel-parent");
  for (const element of document.querySelectorAll("*")) {
    if (
      String(element.textContent ?? "").trim() === "People Playground"
    ) {
      inspect(element, "people-playground-text");
    }
  }
  return {
    panelAppid: panel?.dataset.appid ?? null,
    anchorTag: anchor?.tagName ?? null,
    anchorText: anchor?.textContent?.replace(/\s+/g, " ").trim() ?? null,
    rows,
  };
})()
