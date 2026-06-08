(() => ({
  title: document.title,
  location: location.href,
  readyState: document.readyState,
  scripts: [...document.scripts].map((script) => script.src || script.textContent.slice(0, 120)),
  hasRealSteamStatus: Boolean(globalThis.__REALSTEAMONMAC_UI_STATUS__),
  realSteamStatus: globalThis.__REALSTEAMONMAC_UI_STATUS__ ?? null,
  globals: Object.getOwnPropertyNames(globalThis)
    .filter((name) => /realsteam|appStore|appDetails|library/i.test(name))
    .sort(),
}))()
