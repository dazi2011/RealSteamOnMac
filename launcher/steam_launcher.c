#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static void log_line(const char *format, ...) {
  const char *home = getenv("HOME");
  if (home == NULL) {
    return;
  }

  char directory[PATH_MAX];
  char path[PATH_MAX];
  if (snprintf(directory, sizeof(directory),
               "%s/Library/Logs/RealSteamOnMac", home) >=
      (int)sizeof(directory)) {
    return;
  }
  (void)mkdir(directory, 0700);
  if (snprintf(path, sizeof(path), "%s/launcher.log", directory) >=
      (int)sizeof(path)) {
    return;
  }

  FILE *stream = fopen(path, "a");
  if (stream == NULL) {
    return;
  }
  va_list arguments;
  va_start(arguments, format);
  vfprintf(stream, format, arguments);
  va_end(arguments);
  fputc('\n', stream);
  fclose(stream);
}

static bool build_path(char *destination, size_t capacity,
                       const char *left, const char *right) {
  return snprintf(destination, capacity, "%s/%s", left, right) <
         (int)capacity;
}

static bool parent_path(char *destination, size_t capacity,
                        const char *path) {
  size_t length = strlen(path);
  if (length == 0 || length >= capacity) {
    return false;
  }
  memcpy(destination, path, length + 1);
  char *slash = strrchr(destination, '/');
  if (slash == NULL || slash == destination) {
    return false;
  }
  *slash = '\0';
  return true;
}

static bool install_steamui_patch(const char *patcher,
                                  const char *steamui,
                                  const char *ui_source,
                                  const char *allowlist) {
  pid_t child = fork();
  if (child < 0) {
    log_line("Steam UI patch failed: fork: %s", strerror(errno));
    return false;
  }
  if (child == 0) {
    char *const arguments[] = {
        "/usr/bin/python3",
        (char *)patcher,
        "install",
        "--steamui-root",
        (char *)steamui,
        "--ui-source",
        (char *)ui_source,
        "--allowlist",
        (char *)allowlist,
        NULL,
    };
    execv(arguments[0], arguments);
    _exit(127);
  }

  int status = 0;
  while (waitpid(child, &status, 0) < 0) {
    if (errno == EINTR) {
      continue;
    }
    log_line("Steam UI patch failed: waitpid: %s", strerror(errno));
    return false;
  }
  if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
    log_line("Steam UI patch failed: helper status=%d", status);
    return false;
  }
  log_line("Steam UI patch verified");
  return true;
}

static int exec_original_bootstrap(int argc, char **argv,
                                   const char *reason) {
  char original[PATH_MAX];
  const char *slash = strrchr(argv[0], '/');
  if (slash == NULL) {
    log_line("fallback failed: launcher path is not absolute");
    return 127;
  }

  size_t directory_length = (size_t)(slash - argv[0]);
  if (directory_length + strlen("/steam_osx.original") + 1 >
      sizeof(original)) {
    log_line("fallback failed: launcher path is too long");
    return 127;
  }
  memcpy(original, argv[0], directory_length);
  strcpy(original + directory_length, "/steam_osx.original");

  char **child_argv = calloc((size_t)argc + 1, sizeof(*child_argv));
  if (child_argv == NULL) {
    log_line("fallback failed: could not allocate argv");
    return 127;
  }
  child_argv[0] = original;
  for (int index = 1; index < argc; ++index) {
    child_argv[index] = argv[index];
  }

  unsetenv("DYLD_INSERT_LIBRARIES");
  unsetenv("REALSTEAMONMAC_FORCE_COMPAT");
  unsetenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH");
  unsetenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS");
  unsetenv("REALSTEAMONMAC_INJECTION_STAGE");
  unsetenv("STEAM_EXTRA_COMPAT_TOOLS_PATHS");
  log_line("fallback to original Steam bootstrap: %s", reason);
  execv(original, child_argv);
  int error = errno;
  log_line("fallback exec failed: %s", strerror(error));
  free(child_argv);
  return 127;
}

static bool has_argument(int argc, char **argv, const char *argument) {
  for (int index = 1; index < argc; ++index) {
    if (strcmp(argv[index], argument) == 0) {
      return true;
    }
  }
  return false;
}

int main(int argc, char **argv) {
  const char *home = getenv("HOME");
  if (home == NULL || *home == '\0') {
    return exec_original_bootstrap(argc, argv, "HOME is unavailable");
  }

  char default_runtime[PATH_MAX];
  char default_support[PATH_MAX];
  if (!build_path(default_runtime, sizeof(default_runtime), home,
                  "Library/Application Support/Steam/Steam.AppBundle/"
                  "Steam/Contents/MacOS/steam_osx") ||
      !build_path(default_support, sizeof(default_support), home,
                  "Library/Application Support/RealSteamOnMac")) {
    return exec_original_bootstrap(argc, argv, "default path is too long");
  }

  const char *runtime_override =
      getenv("REALSTEAMONMAC_RUNTIME_EXECUTABLE");
  const char *support_override = getenv("REALSTEAMONMAC_SUPPORT_ROOT");
  const char *runtime =
      runtime_override != NULL && *runtime_override != '\0'
          ? runtime_override
          : default_runtime;
  const char *support =
      support_override != NULL && *support_override != '\0'
          ? support_override
          : default_support;

  char hook[PATH_MAX];
  char engine[PATH_MAX];
  char patcher[PATH_MAX];
  char ui_source[PATH_MAX];
  char allowlist[PATH_MAX];
  char registry_token[PATH_MAX];
  char runtime_directory[PATH_MAX];
  char steamui[PATH_MAX];
  if (!build_path(hook, sizeof(hook), support,
                  "libRealSteamCompatGate.dylib") ||
      !build_path(engine, sizeof(engine), support,
                  "libRealSteamNativeEngine.dylib") ||
      !build_path(patcher, sizeof(patcher), support,
                  "patch_steamui.py") ||
      !build_path(ui_source, sizeof(ui_source), support,
                  "ui/realsteamonmac_ui.js") ||
      !build_path(allowlist, sizeof(allowlist), support,
                  "allowlist.txt") ||
      !build_path(registry_token, sizeof(registry_token), support,
                  "registry-token") ||
      !parent_path(runtime_directory, sizeof(runtime_directory), runtime) ||
      !build_path(steamui, sizeof(steamui), runtime_directory, "steamui")) {
    return exec_original_bootstrap(argc, argv, "support path is too long");
  }

  if (access(runtime, X_OK) != 0) {
    return exec_original_bootstrap(argc, argv,
                                   "Steam runtime is unavailable");
  }
  if (access(hook, R_OK) != 0 ||
      access(engine, R_OK) != 0 ||
      access(patcher, X_OK) != 0 ||
      access(ui_source, R_OK) != 0 ||
      access(allowlist, R_OK) != 0 ||
      access(registry_token, R_OK) != 0) {
    return exec_original_bootstrap(argc, argv,
                                   "RealSteamOnMac support files are missing");
  }
  if (!install_steamui_patch(patcher, steamui, ui_source, allowlist)) {
    return exec_original_bootstrap(argc, argv,
                                   "Steam UI resource patch failed");
  }

  if (unsetenv("STEAM_EXTRA_COMPAT_TOOLS_PATHS") != 0 ||
      setenv("DYLD_INSERT_LIBRARIES", hook, 1) != 0 ||
      setenv("REALSTEAMONMAC_FORCE_COMPAT", "1", 1) != 0 ||
      setenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH", engine, 1) != 0 ||
      setenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS", "30000", 1) != 0 ||
      setenv("REALSTEAMONMAC_INJECTION_STAGE", "bootstrap", 1) != 0) {
    return exec_original_bootstrap(argc, argv,
                                   "could not configure runtime environment");
  }

  bool add_skip_bootstrap =
      !has_argument(argc, argv, "-skipinitialbootstrap");
  size_t child_count = (size_t)argc + (add_skip_bootstrap ? 1 : 0) + 1;
  char **child_argv = calloc(child_count, sizeof(*child_argv));
  if (child_argv == NULL) {
    return exec_original_bootstrap(argc, argv, "could not allocate argv");
  }

  size_t cursor = 0;
  child_argv[cursor++] = (char *)runtime;
  if (add_skip_bootstrap) {
    child_argv[cursor++] = "-skipinitialbootstrap";
  }
  for (int index = 1; index < argc; ++index) {
    child_argv[cursor++] = argv[index];
  }
  child_argv[cursor] = NULL;

  const char *dry_run = getenv("REALSTEAMONMAC_LAUNCHER_DRY_RUN");
  if (dry_run != NULL && strcmp(dry_run, "1") == 0) {
    printf("steamui=verified\n");
    printf("dyld=%s\n", getenv("DYLD_INSERT_LIBRARIES"));
    printf("engine=%s\n", getenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH"));
    printf("activation_delay_ms=%s\n",
           getenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS"));
    printf("injection_stage=%s\n",
           getenv("REALSTEAMONMAC_INJECTION_STAGE"));
    printf("enabled=%s\n", getenv("REALSTEAMONMAC_FORCE_COMPAT"));
    printf("tools=disabled\n");
    fputs("args=", stdout);
    for (size_t index = 1; child_argv[index] != NULL; ++index) {
      if (index > 1) {
        fputc(' ', stdout);
      }
      fputs(child_argv[index], stdout);
    }
    fputc('\n', stdout);
    free(child_argv);
    return 0;
  }

  log_line("exec Steam runtime: %s", runtime);
  execv(runtime, child_argv);
  int error = errno;
  log_line("runtime exec failed: %s", strerror(error));
  free(child_argv);
  return exec_original_bootstrap(argc, argv, "Steam runtime exec failed");
}
