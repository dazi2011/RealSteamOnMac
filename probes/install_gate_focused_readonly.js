(() => {
  const clone = (value) => {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return null;
    }
  };

  const primitiveEntries = (value) => {
    if (!value || typeof value !== "object") return null;
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) =>
          ["string", "number", "boolean"].includes(typeof item),
        )
        .sort(([left], [right]) => left.localeCompare(right)),
    );
  };

  const methodSources = (instance) => {
    if (!instance) return null;
    const methods = {};
    let prototype = instance;
    for (let depth = 0; prototype && depth < 5; depth += 1) {
      for (const name of Object.getOwnPropertyNames(prototype).sort()) {
        if (name === "constructor" || methods[name]) continue;
        let value;
        try {
          value = instance[name];
        } catch {
          continue;
        }
        if (typeof value !== "function") continue;
        if (!/click|install|action|platform|compat|disabled|run/i.test(name)) {
          continue;
        }
        methods[name] = Function.prototype.toString.call(value).slice(0, 5000);
      }
      prototype = Object.getPrototypeOf(prototype);
    }
    return methods;
  };

  return [...document.querySelectorAll("[role=button], button")]
    .filter((element) => element.innerText?.trim() === "安装")
    .map((element, index) => {
      const fiberKey = Object.getOwnPropertyNames(element).find(
        (key) =>
          key.startsWith("__reactFiber$") ||
          key.startsWith("__reactInternalInstance$"),
      );
      let fiber = fiberKey ? element[fiberKey] : null;
      let details = null;
      let overview = null;
      const components = [];

      for (let depth = 0; fiber && depth < 35; depth += 1) {
        if (!details && fiber.memoizedProps?.details) {
          details = fiber.memoizedProps.details;
        }
        if (!overview && fiber.memoizedProps?.overview) {
          overview = fiber.memoizedProps.overview;
        }

        if (fiber.stateNode && typeof fiber.stateNode === "object") {
          const methods = methodSources(fiber.stateNode);
          if (methods && Object.keys(methods).length > 0) {
            components.push({
              depth,
              type:
                fiber.type?.displayName ??
                fiber.type?.name ??
                fiber.elementType?.displayName ??
                fiber.elementType?.name ??
                null,
              state: clone(fiber.stateNode.state),
              props: primitiveEntries(fiber.stateNode.props),
              methods,
            });
          }
        }
        fiber = fiber.return;
      }

      const rect = element.getBoundingClientRect();
      return {
        index,
        rect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        },
        computedStyle: {
          pointerEvents: getComputedStyle(element).pointerEvents,
          backgroundColor: getComputedStyle(element).backgroundColor,
          color: getComputedStyle(element).color,
        },
        details: details
          ? {
              primitives: primitiveEntries(details),
              compat: {
                strCompatToolName: details.strCompatToolName ?? null,
                strCompatToolDisplayName:
                  details.strCompatToolDisplayName ?? null,
                nCompatToolPriority: details.nCompatToolPriority ?? null,
              },
            }
          : null,
        overview: overview
          ? {
              primitives: primitiveEntries(overview),
              per_client_data: clone(overview.per_client_data),
              remote_per_client_data: clone(overview.remote_per_client_data),
            }
          : null,
        components,
      };
    });
})()
