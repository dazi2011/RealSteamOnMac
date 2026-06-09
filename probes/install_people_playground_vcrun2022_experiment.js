(() => {
  const appid = 1118200;
  const dependency = "vcrun2022";
  const panel = document.querySelector(".realsteamonmac-controls");
  if (Number(panel?.dataset.appid) !== appid) {
    throw new Error(
      `refusing mismatched action panel AppID ${panel?.dataset.appid}`,
    );
  }
  const button = panel.querySelector(
    `[data-install-dependency="${dependency}"]`,
  );
  if (!button) {
    throw new Error(`dependency button is unavailable: ${dependency}`);
  }
  if (button.disabled) {
    throw new Error("People Playground action panel is busy");
  }
  button.click();
  return {
    clicked: true,
    appid,
    dependency,
  };
})()
