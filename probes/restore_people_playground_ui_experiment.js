(async () => {
  const stateKey = "__realSteamOnMacPeoplePlaygroundUIExperiment";
  const state = globalThis[stateKey];
  if (!state) {
    return { restored: false, reason: "experiment is not active" };
  }
  if (state.appid !== 1118200) {
    throw new Error("refusing to restore an unexpected AppID");
  }

  for (const context of state.contexts) {
    context.selected.display_status = context.originalSelectedStatus;
    context.selected.is_available_on_current_platform =
      context.originalAvailable;
    context.selected.is_invalid_os_type = context.originalInvalidOS;
    context.details.eDisplayStatus = context.originalDetailsStatus;
    context.actionComponent.forceUpdate();
  }
  delete globalThis[stateKey];

  await new Promise((resolve) => setTimeout(resolve, 500));
  return {
    restored: true,
    appid: state.appid,
    contextCount: state.contexts.length,
    selectedStatus: state.contexts.map(
      (context) => context.selected.display_status,
    ),
    detailsStatus: state.contexts.map(
      (context) => context.details.eDisplayStatus,
    ),
  };
})()
