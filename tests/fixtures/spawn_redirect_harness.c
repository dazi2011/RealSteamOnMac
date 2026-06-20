#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

typedef int (*decision_function)(const char *, char *const []);
typedef int (*spawn_function)(
    pid_t *,
    const char *,
    const posix_spawn_file_actions_t *,
    const posix_spawnattr_t *,
    char *const [],
    char *const []);
typedef int (*test_spawn_function)(
    spawn_function, const char *, char *const [], char *const []);

static char gSpawnPath[PATH_MAX];
static char gSpawnArguments[16][PATH_MAX];
static size_t gSpawnArgumentCount = 0;
static char gSpawnEnvironment[16][PATH_MAX];
static size_t gSpawnEnvironmentCount = 0;

static void fail(const char *message) {
  fprintf(stderr, "%s\n", message);
  exit(1);
}

static bool make_directory(const char *path) {
  return mkdir(path, 0700) == 0 || errno == EEXIST;
}

static bool write_bytes(
    const char *path, const char *bytes, size_t length, mode_t mode) {
  int descriptor = open(path, O_WRONLY | O_CREAT | O_TRUNC, mode);
  if (descriptor < 0) {
    return false;
  }
  bool success =
      write(descriptor, bytes, length) == (ssize_t)length &&
      close(descriptor) == 0;
  if (!success) {
    (void)close(descriptor);
  }
  return success;
}

static bool percent_encode(
    const char *input, char *output, size_t output_capacity) {
  static const char hexadecimal[] = "0123456789ABCDEF";
  size_t length = strlen(input);
  if (length > (output_capacity - 1) / 3) {
    return false;
  }
  for (size_t index = 0; index < length; ++index) {
    unsigned char byte = (unsigned char)input[index];
    output[index * 3] = '%';
    output[(index * 3) + 1] = hexadecimal[byte >> 4];
    output[(index * 3) + 2] = hexadecimal[byte & 0x0f];
  }
  output[length * 3] = '\0';
  return true;
}

static int capture_spawn(
    pid_t *pid,
    const char *path,
    const posix_spawn_file_actions_t *file_actions,
    const posix_spawnattr_t *attributes,
    char *const argv[],
    char *const envp[]) {
  (void)pid;
  (void)file_actions;
  (void)attributes;
  if (strlen(path) >= sizeof(gSpawnPath)) {
    return ENAMETOOLONG;
  }
  strcpy(gSpawnPath, path);
  gSpawnArgumentCount = 0;
  while (
      argv != NULL &&
      gSpawnArgumentCount <
          sizeof(gSpawnArguments) / sizeof(gSpawnArguments[0]) &&
      argv[gSpawnArgumentCount] != NULL
  ) {
    if (strlen(argv[gSpawnArgumentCount]) >= PATH_MAX) {
      return E2BIG;
    }
    strcpy(
        gSpawnArguments[gSpawnArgumentCount],
        argv[gSpawnArgumentCount]);
    ++gSpawnArgumentCount;
  }
  gSpawnEnvironmentCount = 0;
  while (
      envp != NULL &&
      gSpawnEnvironmentCount <
          sizeof(gSpawnEnvironment) / sizeof(gSpawnEnvironment[0]) &&
      envp[gSpawnEnvironmentCount] != NULL
  ) {
    if (strlen(envp[gSpawnEnvironmentCount]) >= PATH_MAX) {
      return E2BIG;
    }
    strcpy(
        gSpawnEnvironment[gSpawnEnvironmentCount],
        envp[gSpawnEnvironmentCount]);
    ++gSpawnEnvironmentCount;
  }
  return 73;
}

static bool captured_argument(size_t index, const char *expected) {
  return
      index < gSpawnArgumentCount &&
      strcmp(gSpawnArguments[index], expected) == 0;
}

static bool captured_environment(const char *expected) {
  for (size_t index = 0; index < gSpawnEnvironmentCount; ++index) {
    if (strcmp(gSpawnEnvironment[index], expected) == 0) {
      return true;
    }
  }
  return false;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fail("usage: spawn_redirect_harness TEST_ENGINE");
  }

  char home[] = "/tmp/realsteamonmac-spawn-home.XXXXXX";
  if (mkdtemp(home) == NULL) {
    fail("could not create spawn HOME");
  }
  char trusted_home[PATH_MAX];
  if (realpath(home, trusted_home) == NULL) {
    fail("could not canonicalize spawn HOME");
  }
  char library[PATH_MAX];
  char application_support[PATH_MAX];
  char support[PATH_MAX];
  char runtimes[PATH_MAX];
  char bin[PATH_MAX];
  char runtime[PATH_MAX];
  char cache[PATH_MAX];
  if (
      snprintf(
          library, sizeof(library), "%s/Library",
          trusted_home) >= PATH_MAX ||
      snprintf(
          application_support, sizeof(application_support),
          "%s/Application Support", library) >= PATH_MAX ||
      snprintf(
          support, sizeof(support),
          "%s/RealSteamOnMac", application_support) >= PATH_MAX ||
      snprintf(runtimes, sizeof(runtimes), "%s/runtimes", support) >=
          PATH_MAX ||
      snprintf(bin, sizeof(bin), "%s/bin", runtimes) >= PATH_MAX ||
      snprintf(
          runtime, sizeof(runtime),
          "%s/realsteamonmac-runtime", bin) >= PATH_MAX ||
      snprintf(
          cache, sizeof(cache),
          "%s/managed-registry-v1.txt", support) >= PATH_MAX ||
      !make_directory(library) ||
      !make_directory(application_support) ||
      !make_directory(support) ||
      !make_directory(runtimes) ||
      !make_directory(bin) ||
      !write_bytes(runtime, "# fixture\n", 10, 0600)
  ) {
    fail("could not prepare spawn runtime");
  }

  char fixture_template[] = "/tmp/realsteamonmac-shortcut.XXXXXX";
  int descriptor = mkstemp(fixture_template);
  if (descriptor < 0 || write(descriptor, "MZfixture", 9) != 9 ||
      close(descriptor) != 0) {
    fail("could not create shortcut PE fixture");
  }
  char registered_candidate[PATH_MAX];
  char registered[PATH_MAX];
  if (
      snprintf(
          registered_candidate, sizeof(registered_candidate),
          "%s.exe", fixture_template) >= PATH_MAX ||
      rename(fixture_template, registered_candidate) != 0 ||
      realpath(registered_candidate, registered) == NULL
  ) {
    fail("could not name shortcut PE fixture");
  }

  char other_pe[PATH_MAX];
  char non_pe[PATH_MAX];
  char symlink_path[PATH_MAX];
  if (
      snprintf(other_pe, sizeof(other_pe), "%s-other.exe", registered) >=
          PATH_MAX ||
      snprintf(non_pe, sizeof(non_pe), "%s-plain.exe", registered) >=
          PATH_MAX ||
      snprintf(symlink_path, sizeof(symlink_path), "%s-link.exe", registered) >=
          PATH_MAX ||
      !write_bytes(other_pe, "MZother", 7, 0600) ||
      !write_bytes(non_pe, "plain", 5, 0600) ||
      symlink(registered, symlink_path) != 0
  ) {
    fail("could not create rejection fixtures");
  }

  char encoded[PATH_MAX * 3];
  char cache_body[(PATH_MAX * 3) + 128];
  if (
      !percent_encode(registered, encoded, sizeof(encoded)) ||
      snprintf(
          cache_body, sizeof(cache_body),
          "RSMREG\t1\nA\t1118200\nS\t4000\t%s\n",
          encoded) >= (int)sizeof(cache_body) ||
      !write_bytes(cache, cache_body, strlen(cache_body), 0600) ||
      setenv("HOME", trusted_home, 1) != 0
  ) {
    fail("could not prepare typed registry cache");
  }

  void *engine = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (engine == NULL) {
    fail(dlerror());
  }
  decision_function should_redirect =
      (decision_function)dlsym(
          engine, "realsteamonmac_should_redirect_spawn");
  test_spawn_function invoke_spawn =
      (test_spawn_function)dlsym(
          engine, "realsteamonmac_test_spawn_redirect");
  if (should_redirect == NULL || invoke_spawn == NULL) {
    fail("spawn redirect test exports were not found");
  }

  char store[] = "SteamAppId=1118200";
  char shortcut[] = "SteamAppId=4000";
  char unmanaged[] = "SteamAppId=9999";
  char *store_environment[] = {store, NULL};
  char *shortcut_environment[] = {
      shortcut,
      (char *)"HOME=/tmp/untrusted-home",
      (char *)"RSM_FIXTURE_ENV=preserved",
      (char *)"PYTHONPATH=/tmp/untrusted-python",
      (char *)"DYLD_INSERT_LIBRARIES=/tmp/untrusted.dylib",
      (char *)"REALSTEAMONMAC_RUNTIME_ROOT=/tmp/untrusted-runtime",
      NULL,
  };
  char *unmanaged_environment[] = {unmanaged, NULL};

  if (
      should_redirect(registered, store_environment) != 1 ||
      should_redirect(
          "/tmp/realsteamonmac-missing-store.exe",
          store_environment) != 1 ||
      should_redirect(
          "/tmp/realsteamonmac-stale-store.app",
          store_environment) != 1
  ) {
    fail("store redirect regression");
  }
  if (
      should_redirect(registered, unmanaged_environment) != 0 ||
      should_redirect(non_pe, store_environment) != 0
  ) {
    fail("unmanaged or native target was redirected");
  }

  if (should_redirect(registered, shortcut_environment) != 1) {
    fail("exact registered shortcut was not redirected");
  }
  if (
      should_redirect(other_pe, shortcut_environment) != 0 ||
      should_redirect(non_pe, shortcut_environment) != 0 ||
      should_redirect(symlink_path, shortcut_environment) != 0 ||
      should_redirect(
          "/tmp/realsteamonmac-missing-shortcut.exe",
          shortcut_environment) != 0 ||
      should_redirect(
          "/tmp/realsteamonmac-stale-shortcut.app",
          shortcut_environment) != 0
  ) {
    fail("shortcut rejection path was redirected");
  }

  char *original_arguments[] = {
      registered, (char *)"--fixture-argument", NULL};
  int result = invoke_spawn(
      capture_spawn, registered, original_arguments,
      shortcut_environment);
  if (
      result != 73 ||
      strcmp(gSpawnPath, "/usr/bin/python3") != 0 ||
      gSpawnArgumentCount != 8 ||
      !captured_argument(0, "/usr/bin/python3") ||
      !captured_argument(1, "-I") ||
      !captured_argument(2, runtime) ||
      !captured_argument(3, "launch") ||
      !captured_argument(4, "--shortcut-id") ||
      !captured_argument(5, "4000") ||
      !captured_argument(6, registered) ||
      !captured_argument(7, "--fixture-argument") ||
      !captured_environment("SteamAppId=4000") ||
      !captured_environment("RSM_FIXTURE_ENV=preserved")
  ) {
    fail("shortcut wrapper argv or environment was not exact");
  }
  char trusted_home_environment[PATH_MAX];
  if (
      snprintf(
          trusted_home_environment, sizeof(trusted_home_environment),
          "HOME=%s", trusted_home) >= PATH_MAX ||
      !captured_environment(trusted_home_environment) ||
      captured_environment("HOME=/tmp/untrusted-home") ||
      captured_environment("PYTHONPATH=/tmp/untrusted-python") ||
      captured_environment("DYLD_INSERT_LIBRARIES=/tmp/untrusted.dylib") ||
      captured_environment(
          "REALSTEAMONMAC_RUNTIME_ROOT=/tmp/untrusted-runtime")
  ) {
    fail("shortcut wrapper environment was not sanitized");
  }

  if (unlink(runtime) != 0) {
    fail("could not remove runtime helper fixture");
  }
  result = invoke_spawn(
      capture_spawn, registered, original_arguments,
      shortcut_environment);
  if (
      result != 73 ||
      strcmp(gSpawnPath, registered) != 0 ||
      gSpawnArgumentCount != 2 ||
      !captured_argument(0, registered) ||
      !captured_argument(1, "--fixture-argument") ||
      !captured_environment("HOME=/tmp/untrusted-home") ||
      !captured_environment("PYTHONPATH=/tmp/untrusted-python") ||
      !captured_environment("DYLD_INSERT_LIBRARIES=/tmp/untrusted.dylib") ||
      !captured_environment(
          "REALSTEAMONMAC_RUNTIME_ROOT=/tmp/untrusted-runtime")
  ) {
    fail("missing runtime helper did not preserve original spawn");
  }

  char replacement_template[PATH_MAX];
  if (
      snprintf(
          replacement_template, sizeof(replacement_template),
          "%s.replacement.XXXXXX", registered) >= PATH_MAX
  ) {
    fail("replacement fixture path is too long");
  }
  descriptor = mkstemp(replacement_template);
  if (
      descriptor < 0 ||
      write(descriptor, "MZreplacement", 13) != 13 ||
      close(descriptor) != 0 ||
      rename(replacement_template, registered) != 0
  ) {
    fail("could not atomically replace shortcut fixture");
  }
  if (
      should_redirect(registered, shortcut_environment) != 0 ||
      should_redirect(registered, store_environment) != 1
  ) {
    fail("registered shortcut file replacement was not isolated");
  }

  (void)dlclose(engine);
  (void)unlink(symlink_path);
  (void)unlink(non_pe);
  (void)unlink(other_pe);
  (void)unlink(registered);
  puts("spawn redirect harness: PASS");
  return 0;
}
