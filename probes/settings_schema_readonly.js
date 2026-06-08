(() => {
  const chunks = globalThis.webpackChunksteamui;
  if (!Array.isArray(chunks)) {
    return { error: "webpackChunksteamui is unavailable" };
  }

  let webpackRequire = null;
  chunks.push([
    [`realsteamonmac-settings-schema-${Date.now()}-${Math.random()}`],
    {},
    (runtimeRequire) => {
      webpackRequire = runtimeRequire;
    },
  ]);

  const messages = webpackRequire(29788);
  const metadata = messages.Ne?.M?.();
  return {
    messageExports: Object.keys(messages).sort(),
    settingFields: metadata?.fields
      ? Object.fromEntries(
          Object.entries(metadata.fields).map(([name, field]) => [
            name,
            {
              number: field.n,
              defaultValue: field.d ?? null,
              repeated: field.r ?? false,
            },
          ]),
        )
      : null,
  };
})()
