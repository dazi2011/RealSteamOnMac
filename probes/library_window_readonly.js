(() => {
  const summarizeElement = (element) => {
    const attributes = {};
    for (const attribute of element.attributes ?? []) {
      attributes[attribute.name] = attribute.value;
    }

    const reactKeys = Object.getOwnPropertyNames(element).filter(
      (key) =>
        key.startsWith("__reactProps$") ||
        key.startsWith("__reactFiber$") ||
        key.startsWith("__reactInternalInstance$"),
    );

    const reactProps = {};
    for (const key of reactKeys.filter((name) => name.startsWith("__reactProps$"))) {
      const props = element[key];
      reactProps[key] = {
        keys: props && typeof props === "object" ? Object.keys(props).sort() : [],
        disabled: props?.disabled ?? null,
        className:
          typeof props?.className === "string" ? props.className : null,
        hasOnClick: typeof props?.onClick === "function",
      };
    }

    const style = getComputedStyle(element);
    return {
      tag: element.tagName,
      text: element.innerText?.trim().slice(0, 300) ?? "",
      attributes,
      disabledProperty: "disabled" in element ? element.disabled : null,
      ariaDisabled: element.getAttribute("aria-disabled"),
      pointerEvents: style.pointerEvents,
      opacity: style.opacity,
      cursor: style.cursor,
      reactProps,
    };
  };

  const inspectDocument = (doc, label) => {
    const candidates = [...doc.querySelectorAll("button, [role=button], a")]
      .filter((element) => {
        const text = element.innerText?.trim() ?? "";
        return /安装|下载|开始游戏|适用于|Install|Download|Play/i.test(text);
      })
      .map(summarizeElement);

    return {
      label,
      title: doc.title,
      location: doc.location?.href ?? null,
      readyState: doc.readyState,
      bodyText: doc.body?.innerText?.slice(0, 2000) ?? null,
      candidates,
    };
  };

  const documents = [inspectDocument(document, "top")];
  const frames = [];
  for (let index = 0; index < globalThis.frames.length; index += 1) {
    const frame = globalThis.frames[index];
    try {
      frames.push({
        index,
        location: frame.location.href,
        accessible: true,
      });
      frames.push(inspectDocument(frame.document, `frame-${index}`));
    } catch (error) {
      frames.push({
        index,
        accessible: false,
        error: String(error),
      });
    }
  }

  return {
    location: globalThis.location.href,
    title: document.title,
    frameCount: globalThis.frames.length,
    documents,
    frames,
    globals: Object.getOwnPropertyNames(globalThis)
      .filter((name) => /app|library|install|compat/i.test(name))
      .sort()
      .slice(0, 300),
  };
})()
