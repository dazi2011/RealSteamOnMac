#include <errno.h>
#include <libproc.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#define HELPER_DRAIN_INTERVAL_US 250000
#define HELPER_DRAIN_MAX_POLLS 60
#define IPCSERVER_DRAIN_MAX_POLLS 20

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
                                  const char *allowlist,
                                  const char *dependencies,
                                  const char *compat_tools) {
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
        "--dependencies",
        (char *)dependencies,
        "--compat-tools-root",
        (char *)compat_tools,
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

static bool process_name_exists(const char *name) {
  int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_ALL, 0};
  size_t size = 0;
  if (sysctl(mib, 4, NULL, &size, NULL, 0) != 0 || size == 0) {
    log_line("could not inspect process table: %s", strerror(errno));
    return false;
  }

  struct kinfo_proc *processes = malloc(size);
  if (processes == NULL) {
    log_line("could not allocate process table");
    return false;
  }
  if (sysctl(mib, 4, processes, &size, NULL, 0) != 0) {
    log_line("could not read process table: %s", strerror(errno));
    free(processes);
    return false;
  }

  bool found = false;
  size_t count = size / sizeof(*processes);
  for (size_t index = 0; index < count; ++index) {
    if (
        processes[index].kp_proc.p_stat != SZOMB &&
        strcmp(processes[index].kp_proc.p_comm, name) == 0
    ) {
      found = true;
      break;
    }
  }
  free(processes);
  return found;
}

static bool canonicalize_process_path(char *destination, size_t capacity,
                                      const char *path) {
  if (realpath(path, destination) != NULL) {
    return true;
  }

  char directory[PATH_MAX];
  char canonical_directory[PATH_MAX];
  if (!parent_path(directory, sizeof(directory), path) ||
      realpath(directory, canonical_directory) == NULL) {
    return false;
  }
  const char *name = strrchr(path, '/');
  return name != NULL &&
         build_path(destination, capacity, canonical_directory, name + 1);
}

static bool process_argument_path_matches(pid_t pid,
                                          const char *expected_path,
                                          const char *update_old_path) {
  int mib[] = {CTL_KERN, KERN_PROCARGS2, pid};
  size_t size = 0;
  if (sysctl(mib, 3, NULL, &size, NULL, 0) != 0 ||
      size <= sizeof(int)) {
    return false;
  }

  char *arguments = malloc(size);
  if (arguments == NULL) {
    return false;
  }
  if (sysctl(mib, 3, arguments, &size, NULL, 0) != 0 ||
      size <= sizeof(int)) {
    free(arguments);
    return false;
  }

  const char *executable = arguments + sizeof(int);
  size_t capacity = size - sizeof(int);
  bool terminated = memchr(executable, '\0', capacity) != NULL;
  char canonical_executable[PATH_MAX];
  bool matches =
      terminated &&
      canonicalize_process_path(
          canonical_executable, sizeof(canonical_executable), executable) &&
      (strcmp(canonical_executable, expected_path) == 0 ||
       strcmp(canonical_executable, update_old_path) == 0);
  free(arguments);
  return matches;
}

static pid_t find_process_by_executable_path(const char *expected_path) {
  char canonical_expected[PATH_MAX];
  if (realpath(expected_path, canonical_expected) == NULL) {
    return 0;
  }
  char update_old_path[PATH_MAX];
  if (snprintf(update_old_path, sizeof(update_old_path), "%s.old",
               canonical_expected) >= (int)sizeof(update_old_path)) {
    return 0;
  }

  int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_ALL, 0};
  size_t size = 0;
  if (sysctl(mib, 4, NULL, &size, NULL, 0) != 0 || size == 0) {
    log_line("could not inspect process table: %s", strerror(errno));
    return 0;
  }

  struct kinfo_proc *processes = malloc(size);
  if (processes == NULL) {
    log_line("could not allocate process table");
    return 0;
  }
  if (sysctl(mib, 4, processes, &size, NULL, 0) != 0) {
    log_line("could not read process table: %s", strerror(errno));
    free(processes);
    return 0;
  }

  pid_t found = 0;
  char path[PROC_PIDPATHINFO_MAXSIZE];
  size_t count = size / sizeof(*processes);
  for (size_t index = 0; index < count; ++index) {
    const struct kinfo_proc *process = &processes[index];
    if (
        process->kp_proc.p_stat == SZOMB ||
        process->kp_eproc.e_ucred.cr_uid != getuid() ||
        strcmp(process->kp_proc.p_comm, "ipcserver") != 0
    ) {
      continue;
    }
    int length = proc_pidpath(
        process->kp_proc.p_pid, path, sizeof(path));
    bool path_matches =
        length > 0 &&
        (size_t)length < sizeof(path) &&
        (strcmp(path, canonical_expected) == 0 ||
         strcmp(path, update_old_path) == 0);
    bool deleted_path_matches =
        length <= 0 &&
        process_argument_path_matches(
            process->kp_proc.p_pid, canonical_expected, update_old_path);
    if (path_matches || deleted_path_matches) {
      found = process->kp_proc.p_pid;
      break;
    }
  }
  free(processes);
  return found;
}

static void drain_stale_native_ipcserver(const char *expected_path) {
  if (process_name_exists("steam_osx")) {
    return;
  }

  pid_t pid = find_process_by_executable_path(expected_path);
  if (pid <= 0) {
    return;
  }
  log_line("terminating stale native Steam ipcserver pid %d", pid);
  if (kill(pid, SIGTERM) != 0 && errno != ESRCH) {
    log_line(
        "could not terminate stale native Steam ipcserver pid %d: %s",
        pid, strerror(errno));
    return;
  }

  unsigned int polls = 0;
  while (
      polls < IPCSERVER_DRAIN_MAX_POLLS &&
      find_process_by_executable_path(expected_path) > 0
  ) {
    usleep(HELPER_DRAIN_INTERVAL_US);
    ++polls;
  }
  pid = find_process_by_executable_path(expected_path);
  if (pid > 0) {
    log_line(
        "stale native Steam ipcserver pid %d did not exit after %u ms",
        pid, polls * (HELPER_DRAIN_INTERVAL_US / 1000));
    return;
  }
  log_line(
      "stale native Steam ipcserver drained after %u ms",
      polls * (HELPER_DRAIN_INTERVAL_US / 1000));
}

static void wait_for_stale_steam_helpers(void) {
  if (process_name_exists("steam_osx")) {
    log_line("existing Steam runtime detected; forwarding launch");
    return;
  }

  unsigned int polls = 0;
  while (
      polls < HELPER_DRAIN_MAX_POLLS &&
      process_name_exists("Steam Helper")
  ) {
    if (polls == 0) {
      log_line("waiting for stale Steam Helper processes");
    }
    usleep(HELPER_DRAIN_INTERVAL_US);
    ++polls;
  }
  if (polls == 0) {
    return;
  }
  if (process_name_exists("Steam Helper")) {
    log_line(
        "stale Steam Helper drain timed out after %u ms",
        polls * (HELPER_DRAIN_INTERVAL_US / 1000)
    );
    return;
  }
  log_line(
      "stale Steam Helper processes drained after %u ms",
      polls * (HELPER_DRAIN_INTERVAL_US / 1000)
  );
}

int main(int argc, char **argv) {
  const char *home = getenv("HOME");
  if (home == NULL || *home == '\0') {
    return exec_original_bootstrap(argc, argv, "HOME is unavailable");
  }

  char default_runtime[PATH_MAX];
  char default_support[PATH_MAX];
  char native_ipcserver[PATH_MAX];
  if (!build_path(default_runtime, sizeof(default_runtime), home,
                  "Library/Application Support/Steam/Steam.AppBundle/"
                  "Steam/Contents/MacOS/steam_osx") ||
      !build_path(native_ipcserver, sizeof(native_ipcserver), home,
                  "Library/Application Support/Steam/Steam.AppBundle/"
                  "Steam/Contents/MacOS/ipcserver") ||
      !build_path(default_support, sizeof(default_support), home,
                  "Library/Application Support/RealSteamOnMac")) {
    return exec_original_bootstrap(argc, argv, "default path is too long");
  }

  const char *runtime_override =
      getenv("REALSTEAMONMAC_RUNTIME_EXECUTABLE");
  const char *support_override = getenv("REALSTEAMONMAC_SUPPORT_ROOT");
  const char *compat_tools_override =
      getenv("REALSTEAMONMAC_COMPAT_TOOLS_ROOT");
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
  char dependencies[PATH_MAX];
  char compat_tools[PATH_MAX];
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
      !build_path(dependencies, sizeof(dependencies), support,
                  "dependencies/catalog.json") ||
      !build_path(registry_token, sizeof(registry_token), support,
                  "registry-token") ||
      !parent_path(runtime_directory, sizeof(runtime_directory), runtime) ||
      !build_path(steamui, sizeof(steamui), runtime_directory, "steamui")) {
    return exec_original_bootstrap(argc, argv, "support path is too long");
  }
  if (compat_tools_override != NULL && *compat_tools_override != '\0') {
    if (strlen(compat_tools_override) >= sizeof(compat_tools)) {
      return exec_original_bootstrap(argc, argv,
                                     "compatibility tool path is too long");
    }
    strcpy(compat_tools, compat_tools_override);
  } else {
    const char *home = getenv("HOME");
    if (home == NULL ||
        snprintf(compat_tools, sizeof(compat_tools),
                 "%s/Library/Application Support/Steam/"
                 "compatibilitytools.d",
                 home) >= (int)sizeof(compat_tools)) {
      return exec_original_bootstrap(argc, argv,
                                     "compatibility tool path is unavailable");
    }
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
      access(dependencies, R_OK) != 0 ||
      access(compat_tools, R_OK) != 0 ||
      access(registry_token, R_OK) != 0) {
    return exec_original_bootstrap(argc, argv,
                                   "RealSteamOnMac support files are missing");
  }
  drain_stale_native_ipcserver(native_ipcserver);
  wait_for_stale_steam_helpers();
  if (!install_steamui_patch(
          patcher, steamui, ui_source, allowlist, dependencies,
          compat_tools)) {
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
