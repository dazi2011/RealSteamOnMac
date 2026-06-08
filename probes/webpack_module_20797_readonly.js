(() => {
  const chunks = globalThis.webpackChunksteamui;
  if (!Array.isArray(chunks)) {
    return { error: "webpackChunksteamui is unavailable" };
  }

  let webpackRequire = null;
  chunks.push([
    [`realsteamonmac-module-${Date.now()}-${Math.random()}`],
    {},
    (runtimeRequire) => {
      webpackRequire = runtimeRequire;
    },
  ]);

  const moduleIDs = [20797, 5808, 59865, 32700, 2444, 73291, 33867];
  return {
    modules: Object.fromEntries(
      moduleIDs.map((moduleID) => {
        const factory = webpackRequire?.m?.[moduleID];
        return [
          moduleID,
          factory ? Function.prototype.toString.call(factory) : null,
        ];
      }),
    ),
  };
})()
