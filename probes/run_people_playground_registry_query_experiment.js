(() => {
  const appid = 1118200;
  const panel = document.querySelector(".realsteamonmac-controls");
  const target = panel?.querySelector("[data-run-target]");
  const argumentsInput = panel?.querySelector(
    "[data-run-arguments]",
  );
  const environment = panel?.querySelector(
    "[data-run-environment]",
  );
  const button = panel?.querySelector("[data-run-command]");
  if (!panel || !target || !argumentsInput || !environment || !button) {
    throw new Error("People Playground action panel is unavailable");
  }
  if (Number(panel.dataset.appid) !== appid) {
    throw new Error(
      `refusing mismatched action panel AppID ${panel.dataset.appid}`,
    );
  }
  if (button.disabled) {
    throw new Error("People Playground action panel is busy");
  }
  target.value = String.raw`C:\windows\system32\reg.exe`;
  argumentsInput.value = String.raw`query "HKCU\Software\Wine\Mac Driver"`;
  environment.value = "";
  button.click();
  return {
    clicked: true,
    appid,
    target: target.value,
    arguments: argumentsInput.value,
  };
})()
