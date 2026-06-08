(() => {
  const summarize = (value) => {
    if (!value || typeof value !== "object") return value ?? null;
    return {
      type: value.constructor?.name ?? typeof value,
      keys: Object.keys(value).sort(),
      prototypeKeys: Object.getOwnPropertyNames(
        Object.getPrototypeOf(value) ?? {},
      ).sort(),
    };
  };

  return {
    appStore: summarize(globalThis.appStore),
    appDetailsStore: summarize(globalThis.appDetailsStore),
    appDetailsCache: summarize(globalThis.appDetailsCache),
    appInfoStore: summarize(globalThis.appInfoStore),
    libraryEventStore: summarize(globalThis.libraryEventStore),
  };
})()
