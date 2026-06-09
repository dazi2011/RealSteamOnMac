#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static dispatch_source_t gActivationTimer;

static uint64_t activation_delay_milliseconds(const char *raw) {
  if (raw == NULL || *raw == '\0') {
    return 30000;
  }
  char *end = NULL;
  unsigned long long value = strtoull(raw, &end, 10);
  if (end == raw || *end != '\0' || value > 300000) {
    return 30000;
  }
  return (uint64_t)value;
}

static void activate_native_engine(void *context) {
  const char *engine_path = context;
  if (gActivationTimer != NULL) {
    dispatch_source_cancel(gActivationTimer);
  }
  void *handle = dlopen(engine_path, RTLD_NOW | RTLD_LOCAL);
  if (handle == NULL) {
    return;
  }
  void (*start_worker)(void) =
      (void (*)(void))dlsym(
          handle, "realsteamonmac_start_native_worker");
  if (start_worker != NULL) {
    start_worker();
  }
}

__attribute__((constructor)) static void initialize_injection_guard(void) {
  const char *injection_stage =
      getenv("REALSTEAMONMAC_INJECTION_STAGE");
  if (
      injection_stage != NULL &&
      strcmp(injection_stage, "bootstrap") == 0
  ) {
    if (setenv(
            "REALSTEAMONMAC_INJECTION_STAGE", "runtime", 1) == 0) {
      return;
    }
  }

  bool explicit_runtime =
      injection_stage != NULL &&
      strcmp(injection_stage, "runtime") == 0;
  const char *raw_engine_path =
      getenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH");
  char *engine_path =
      raw_engine_path != NULL && *raw_engine_path != '\0'
          ? strdup(raw_engine_path)
          : NULL;
  uint64_t delay_ms = activation_delay_milliseconds(
      getenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS"));

  unsetenv("DYLD_INSERT_LIBRARIES");
  unsetenv("REALSTEAMONMAC_FORCE_COMPAT");
  unsetenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH");
  unsetenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS");
  unsetenv("REALSTEAMONMAC_INJECTION_STAGE");

  if (
      engine_path == NULL ||
      (explicit_runtime && strcmp(getprogname(), "steam_osx") != 0)
  ) {
    free(engine_path);
    return;
  }
  dispatch_queue_t queue =
      dispatch_get_global_queue(QOS_CLASS_UTILITY, 0);
  gActivationTimer = dispatch_source_create(
      DISPATCH_SOURCE_TYPE_TIMER, 0, 0, queue);
  if (gActivationTimer == NULL) {
    free(engine_path);
    return;
  }
  dispatch_set_context(gActivationTimer, engine_path);
  dispatch_source_set_event_handler_f(
      gActivationTimer, activate_native_engine);
  dispatch_source_set_timer(
      gActivationTimer,
      dispatch_time(
          DISPATCH_TIME_NOW, (int64_t)(delay_ms * NSEC_PER_MSEC)),
      DISPATCH_TIME_FOREVER,
      NSEC_PER_MSEC);
  dispatch_resume(gActivationTimer);
}
