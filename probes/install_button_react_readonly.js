(() => {
  const summarizeProps = (props) => {
    if (!props || typeof props !== "object") return null;

    const result = {};
    for (const key of Object.keys(props).sort()) {
      const value = props[key];
      if (
        value === null ||
        ["string", "number", "boolean", "undefined"].includes(typeof value)
      ) {
        result[key] = value ?? null;
      } else if (typeof value === "function") {
        result[key] = {
          functionName: value.name || null,
          source: Function.prototype.toString.call(value).slice(0, 1200),
        };
      } else if (Array.isArray(value)) {
        result[key] = {
          type: "array",
          length: value.length,
        };
      } else {
        result[key] = {
          type: value?.constructor?.name ?? typeof value,
          keys: Object.keys(value).sort().slice(0, 80),
        };
      }
    }
    return result;
  };

  const typeName = (type) => {
    if (typeof type === "string") return type;
    return type?.displayName ?? type?.name ?? type?.render?.name ?? null;
  };

  return [...document.querySelectorAll("[role=button], button")]
    .filter((element) => element.innerText?.trim() === "安装")
    .map((element, index) => {
      const propsKey = Object.getOwnPropertyNames(element).find((key) =>
        key.startsWith("__reactProps$"),
      );
      const fiberKey = Object.getOwnPropertyNames(element).find(
        (key) =>
          key.startsWith("__reactFiber$") ||
          key.startsWith("__reactInternalInstance$"),
      );

      const fibers = [];
      let fiber = fiberKey ? element[fiberKey] : null;
      for (let depth = 0; fiber && depth < 30; depth += 1) {
        fibers.push({
          depth,
          tag: fiber.tag,
          key: fiber.key ?? null,
          type: typeName(fiber.type),
          elementType: typeName(fiber.elementType),
          memoizedProps: summarizeProps(fiber.memoizedProps),
        });
        fiber = fiber.return;
      }

      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
        index,
        rect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        },
        className: element.className,
        pointerEvents: style.pointerEvents,
        background: style.background,
        backgroundColor: style.backgroundColor,
        color: style.color,
        opacity: style.opacity,
        directProps: propsKey ? summarizeProps(element[propsKey]) : null,
        fibers,
      };
    });
})()
