(() => {
  const body = document.body;
  if (!body) {
    return { error: "document.body is unavailable" };
  }

  const inner = body.querySelector('[class*="DialogContent_InnerWidth"]');
  const dialogBody = inner?.querySelector('[class*="DialogBody"]') ?? null;
  const heading =
    inner?.querySelector("h1, h2, [class*=\"DialogHeader\"]") ?? null;
  const visibleControls = [...body.querySelectorAll("button, input, select")]
    .filter((element) => {
      const style = globalThis.getComputedStyle(element);
      return style.display !== "none" && style.visibility !== "hidden";
    })
    .map((element) => ({
      tag: element.tagName,
      type: element.getAttribute("type"),
      ariaLabel: element.getAttribute("aria-label"),
      text: element.textContent?.trim() ?? "",
    }));

  return {
    title: document.title,
    location: String(globalThis.location),
    heading: heading?.textContent?.trim() ?? null,
    hasSettingsContainer: Boolean(inner),
    hasDialogBody: Boolean(dialogBody),
    dialogBodyChildCount: dialogBody?.childElementCount ?? null,
    dialogBodyText: dialogBody?.textContent?.trim() ?? null,
    bodyText: body.innerText.trim(),
    visibleControls,
  };
})()
