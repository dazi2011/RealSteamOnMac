#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <libkern/OSCacheControl.h>
#include <limits.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <netinet/in.h>
#include <pthread.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

// GetAppForInstallation uses `tbnz w8, #4` to select the "Invalid platform"
// (error 29) branch when the app's platform-flags word has bit 4 set. Each
// UUID-gated profile records that instruction and its two branch destinations.
// We redirect only that instruction through an allowlist-gated trampoline.
#if defined(__x86_64__)
#define STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET ((uintptr_t)0x01945548)
#define STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET_REFRESH ((uintptr_t)0x01945548)
#else
#define STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET ((uintptr_t)0x018F9500)
#define STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET_REFRESH ((uintptr_t)0x018FD500)
#endif
#define PLATFORM_INVALID_BIT ((uint32_t)0x10)
#define MAX_ALLOWLIST_APPIDS ((size_t)256)
#define MAX_MANAGED_SHORTCUTS ((size_t)64)
#define MAX_TRACKED_APP_OBJECTS ((size_t)64)
#define TRACKED_OBJECT_REFRESH_DELAY_US 250000
#define EMPTY_RESCAN_INTERVAL_TICKS 8
#define FULL_RESCAN_INTERVAL_TICKS 60
#define REGISTRY_SERVER_PORT 57344
#define REGISTRY_REQUEST_CAPACITY 16384
#define REGISTRY_TOKEN_CAPACITY 128
#define RUNTIME_CONFIG_CAPACITY 1024
#define RUNTIME_CONFIG_RENDERER_CAPACITY 16
#define RUNTIME_CONFIG_TOOL_CAPACITY 65
#define ACTION_PAYLOAD_CAPACITY 8192
#define ACTION_JOB_ID_BYTES 16
#define ACTION_JOB_ID_CAPACITY ((ACTION_JOB_ID_BYTES * 2) + 1)
#define ACTION_JOB_STATUS_CAPACITY 8192

extern char **environ;

typedef struct {
  char compat_tool[RUNTIME_CONFIG_TOOL_CAPACITY];
  char renderer[RUNTIME_CONFIG_RENDERER_CAPACITY];
  bool msync;
  bool retina;
  bool metal_hud;
  bool metalfx;
  bool dxr;
  bool avx;
} runtime_config;

typedef struct {
  dev_t device;
  ino_t inode;
  off_t size;
  struct timespec modification_time;
  struct timespec change_time;
} shortcut_file_identity;

typedef struct {
  uint32_t id;
  char target[PATH_MAX];
  shortcut_file_identity identity;
} managed_shortcut;

typedef struct {
  uint32_t appids[MAX_ALLOWLIST_APPIDS];
  size_t appid_count;
  managed_shortcut shortcuts[MAX_MANAGED_SHORTCUTS];
  size_t shortcut_count;
} managed_registry;

typedef struct {
  const char *build;
  uint8_t uuid[16];
  uintptr_t compat_gate_offset;
  uintptr_t install_gate_offset;
  uintptr_t install_gate_fallthrough_offset;
  uintptr_t install_gate_invalid_offset;
  uintptr_t posix_spawn_pointer_offset;
} steamclient_profile;

typedef struct {
  const char *build;
  uint8_t uuid[16];
  uintptr_t platform_flags_getter_offset;
} steamui_profile;

#if defined(__x86_64__)
// The native engine is intentionally disabled in a Rosetta Steam process.
// The release targets native arm64 Steam and must fail closed elsewhere.
static const steamclient_profile kSteamClientProfiles[1] = {{0}};
static const steamui_profile kSteamUIProfiles[1] = {{0}};
static const size_t kSteamClientProfileCount = 0;
static const size_t kSteamUIProfileCount = 0;
#else
static const steamclient_profile kSteamClientProfiles[] = {
    {
        "1780705203",
        {
            0xB2, 0x95, 0x06, 0x28, 0x80, 0x3A, 0x3E, 0xFD,
            0x99, 0xEF, 0x3A, 0xD6, 0xB7, 0xB6, 0x5D, 0x1C,
        },
        0x00A012D0,
        0x0062505C,
        0x00625060,
        0x0062508C,
        STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET,
    },
    {
        "1780965181",
        {
            0x04, 0xB5, 0x0E, 0xCB, 0x07, 0xFF, 0x30, 0xDF,
            0xA0, 0x3B, 0x1E, 0xB9, 0x29, 0x2B, 0x85, 0x6B,
        },
        0x00A00874,
        0x00624600,
        0x00624604,
        0x00624630,
        STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET,
    },
    {
        "1780965181",
        {
            0x46, 0x78, 0xFB, 0x72, 0xBA, 0xE9, 0x3D, 0x1B,
            0x83, 0x13, 0xD9, 0xA5, 0x66, 0x7E, 0xA8, 0x14,
        },
        0x00A03DA4,
        0x00627884,
        0x00627888,
        0x006278B4,
        STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET_REFRESH,
    },
    {
        "1781212412",
        {
            0xBA, 0xF0, 0xA6, 0x03, 0x23, 0xF9, 0x3F, 0x14,
            0xA0, 0x19, 0x73, 0x82, 0x57, 0x32, 0xE8, 0x2F,
        },
        0x00A03EF8,
        0x006279D8,
        0x006279DC,
        0x00627A08,
        STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET_REFRESH,
    },
};
static const steamui_profile kSteamUIProfiles[] = {
    {
        "1780705203",
        {
            0xBF, 0x95, 0x20, 0x3F, 0x38, 0x5E, 0x3A, 0xF0,
            0x82, 0xB6, 0xAC, 0x50, 0x9A, 0xE1, 0x22, 0x4D,
        },
        0x005EAC3C,
    },
    {
        "1780965181",
        {
            0x87, 0xB9, 0x14, 0xEC, 0xF2, 0x67, 0x35, 0x59,
            0x80, 0x63, 0xF2, 0x1D, 0x85, 0xD8, 0x96, 0xDE,
        },
        0x005EAC24,
    },
    {
        "1780965181",
        {
            0x60, 0x9E, 0xA3, 0xD9, 0xE3, 0x44, 0x34, 0x0E,
            0xAE, 0xBC, 0xFD, 0x6F, 0x38, 0x6F, 0x9A, 0x28,
        },
        0x005EDF44,
    },
    {
        "1781212412",
        {
            0x68, 0xD2, 0xAA, 0xA9, 0x22, 0x89, 0x34, 0xEA,
            0xAC, 0xFC, 0x94, 0xC4, 0xF1, 0x22, 0x1E, 0xE5,
        },
        0x005EDF44,
    },
};
static const size_t kSteamClientProfileCount =
    sizeof(kSteamClientProfiles) / sizeof(kSteamClientProfiles[0]);
static const size_t kSteamUIProfileCount =
    sizeof(kSteamUIProfiles) / sizeof(kSteamUIProfiles[0]);
#endif
static const uint32_t kSteamClientExpected[2] = {
    0xD101C3FF,
    0xA9054FF4,
};
static const uint32_t kSteamClientForcedTrue[2] = {
    0x52800020,  // mov w0, #1
    0xD65F03C0,  // ret
};
static const uint32_t kSteamClientInstallGateExpected =
    0x37200188;  // tbnz w8, #4, 0x62508c
static uint32_t gAllowlist[MAX_ALLOWLIST_APPIDS];
static size_t gAllowlistCount = 0;
static managed_shortcut gManagedShortcuts[MAX_MANAGED_SHORTCUTS];
static size_t gManagedShortcutCount = 0;
static pthread_mutex_t gAllowlistLock = PTHREAD_MUTEX_INITIALIZER;
static mach_vm_address_t gTrackedObjects[MAX_TRACKED_APP_OBJECTS];
static size_t gTrackedObjectCount = 0;
static _Atomic bool gAllowlistLoaded = false;
static _Atomic uint64_t gAllowlistGeneration = 0;
static bool gRegistered = false;
static bool gSteamClientPatched = false;
static bool gSteamClientSpawnPatched = false;
static _Atomic bool gSteamClientInstallGatePatched = false;
static _Atomic bool gInstallGateRefreshRequested = false;
static bool gDataScanStartedLogged = false;
static bool gDataScanSummaryLogged = false;
static bool gWorkerStarted = false;
static bool gRegistryServerStarted = false;
static pthread_mutex_t gRegistryServerLock = PTHREAD_MUTEX_INITIALIZER;

typedef int (*posix_spawn_function)(
    pid_t *restrict pid,
    const char *restrict path,
    const posix_spawn_file_actions_t *file_actions,
    const posix_spawnattr_t *restrict attributes,
    char *const argv[restrict],
    char *const envp[restrict]);

static posix_spawn_function gOriginalPosixSpawn = NULL;

static void ensure_allowlist_loaded(void);
static bool write_all(int descriptor, const char *bytes, size_t length);
static bool parse_registry_payload(
    const char *text,
    bool drop_invalid_shortcuts,
    managed_registry *registry_out);
static bool persist_managed_registry(
    const managed_registry *registry);
static bool load_managed_registry_cache(
    managed_registry *registry_out);
static bool shortcut_in_registry(
    uint32_t shortcut_id,
    const managed_shortcut *shortcuts,
    size_t count,
    const managed_shortcut **shortcut_out);

static void log_line(const char *message) {
  const char *home = getenv("HOME");
  if (home == NULL) {
    return;
  }

  char directory[1024];
  char path[1200];
  if (snprintf(directory, sizeof(directory),
               "%s/Library/Logs/RealSteamOnMac", home) >=
      (int)sizeof(directory)) {
    return;
  }
  (void)mkdir(directory, 0700);
  if (snprintf(path, sizeof(path), "%s/platform-hook.log", directory) >=
      (int)sizeof(path)) {
    return;
  }

  FILE *stream = fopen(path, "a");
  if (stream == NULL) {
    return;
  }
  fprintf(stream, "%s\n", message);
  fclose(stream);
}

static bool get_executable_path(char **path_out) {
  uint32_t size = 0;
  (void)_NSGetExecutablePath(NULL, &size);
  if (size == 0) {
    return false;
  }

  char *path = malloc(size);
  if (path == NULL) {
    return false;
  }
  if (_NSGetExecutablePath(path, &size) != 0) {
    free(path);
    return false;
  }
  *path_out = path;
  return true;
}

static bool is_steam_runtime_process(void) {
  char *path = NULL;
  if (!get_executable_path(&path)) {
    return false;
  }
  bool matches =
      strstr(path, "/Steam.AppBundle/Steam/Contents/MacOS/steam_osx") != NULL;
  free(path);
  return matches;
}

static void clear_injection_environment(void) {
  unsetenv("DYLD_INSERT_LIBRARIES");
  unsetenv("REALSTEAMONMAC_FORCE_COMPAT");
}

static bool image_uuid_matches(const struct mach_header *header,
                               const uint8_t expected[16]) {
  if (header == NULL || header->magic != MH_MAGIC_64) {
    return false;
  }

  const struct mach_header_64 *header64 =
      (const struct mach_header_64 *)header;
  const uint8_t *cursor = (const uint8_t *)(header64 + 1);
  for (uint32_t index = 0; index < header64->ncmds; ++index) {
    const struct load_command *command =
        (const struct load_command *)cursor;
    if (command->cmdsize < sizeof(*command)) {
      return false;
    }
    if (command->cmd == LC_UUID &&
        command->cmdsize >= sizeof(struct uuid_command)) {
      const struct uuid_command *uuid = (const struct uuid_command *)command;
      return memcmp(uuid->uuid, expected, 16) == 0;
    }
    cursor += command->cmdsize;
  }
  return false;
}

static const steamclient_profile *steamclient_profile_for_header(
    const struct mach_header *header) {
  for (size_t index = 0; index < kSteamClientProfileCount; ++index) {
    if (image_uuid_matches(header, kSteamClientProfiles[index].uuid)) {
      return &kSteamClientProfiles[index];
    }
  }
  return NULL;
}

static void log_steamui_image_diagnostic(void) {
  uint32_t count = _dyld_image_count();
  for (uint32_t index = 0; index < count; ++index) {
    const char *name = _dyld_get_image_name(index);
    if (name == NULL || strstr(name, "steamui.dylib") == NULL) {
      continue;
    }

    const struct mach_header *header = _dyld_get_image_header(index);
    const struct mach_header_64 *header64 =
        (const struct mach_header_64 *)header;
    const uint8_t *cursor =
        header != NULL && header->magic == MH_MAGIC_64
            ? (const uint8_t *)(header64 + 1)
            : NULL;
    const uint8_t *uuid = NULL;
    if (cursor != NULL) {
      for (uint32_t command_index = 0;
           command_index < header64->ncmds;
           ++command_index) {
        const struct load_command *command =
            (const struct load_command *)cursor;
        if (command->cmdsize < sizeof(*command)) {
          break;
        }
        if (command->cmd == LC_UUID &&
            command->cmdsize >= sizeof(struct uuid_command)) {
          uuid = ((const struct uuid_command *)command)->uuid;
          break;
        }
        cursor += command->cmdsize;
      }
    }

    char message[512];
    if (uuid != NULL) {
      snprintf(
          message, sizeof(message),
          "dyld diagnostic: steamui index=%u magic=0x%08x "
          "uuid=%02X%02X%02X%02X%02X%02X%02X%02X"
          "%02X%02X%02X%02X%02X%02X%02X%02X path=%s",
          index, header->magic,
          uuid[0], uuid[1], uuid[2], uuid[3],
          uuid[4], uuid[5], uuid[6], uuid[7],
          uuid[8], uuid[9], uuid[10], uuid[11],
          uuid[12], uuid[13], uuid[14], uuid[15], name);
    } else {
      snprintf(message, sizeof(message),
               "dyld diagnostic: steamui index=%u magic=0x%08x "
               "uuid=unavailable path=%s",
               index, header != NULL ? header->magic : 0, name);
    }
    log_line(message);
  }
}

static const struct mach_header *find_image_by_uuid(
    const uint8_t expected[16]) {
  uint32_t count = _dyld_image_count();
  for (uint32_t index = 0; index < count; ++index) {
    const struct mach_header *header = _dyld_get_image_header(index);
    if (image_uuid_matches(header, expected)) {
      return header;
    }
  }
  return NULL;
}

static const struct mach_header *find_steamclient_image(
    const steamclient_profile **profile_out) {
  for (size_t index = 0; index < kSteamClientProfileCount; ++index) {
    const struct mach_header *header =
        find_image_by_uuid(kSteamClientProfiles[index].uuid);
    if (header != NULL) {
      if (profile_out != NULL) {
        *profile_out = &kSteamClientProfiles[index];
      }
      return header;
    }
  }
  if (profile_out != NULL) {
    *profile_out = NULL;
  }
  return NULL;
}

static const struct mach_header *find_steamui_image(
    const steamui_profile **profile_out) {
  for (size_t index = 0; index < kSteamUIProfileCount; ++index) {
    const struct mach_header *header =
        find_image_by_uuid(kSteamUIProfiles[index].uuid);
    if (header != NULL) {
      if (profile_out != NULL) {
        *profile_out = &kSteamUIProfiles[index];
      }
      return header;
    }
  }
  if (profile_out != NULL) {
    *profile_out = NULL;
  }
  return NULL;
}

static bool make_text_writable(void *target, size_t length,
                               uintptr_t *page_out, size_t *size_out) {
  long raw_page_size = sysconf(_SC_PAGESIZE);
  if (raw_page_size <= 0) {
    return false;
  }

  uintptr_t page_size = (uintptr_t)raw_page_size;
  uintptr_t start = (uintptr_t)target & ~(page_size - 1);
  uintptr_t end =
      ((uintptr_t)target + length + page_size - 1) & ~(page_size - 1);
  kern_return_t result =
      mach_vm_protect(mach_task_self(), (mach_vm_address_t)start,
                      (mach_vm_size_t)(end - start), false,
                      VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY);
  if (result != KERN_SUCCESS) {
    return false;
  }

  *page_out = start;
  *size_out = end - start;
  return true;
}

static void restore_text_protection(uintptr_t page, size_t length) {
  (void)mach_vm_protect(mach_task_self(), (mach_vm_address_t)page,
                        (mach_vm_size_t)length, false,
                        VM_PROT_READ | VM_PROT_EXECUTE);
}

static bool appid_in_list(
    uint32_t appid, const uint32_t *appids, size_t count) {
  for (size_t index = 0; index < count; ++index) {
    if (appids[index] == appid) {
      return true;
    }
  }
  return false;
}

static bool is_allowlisted_unlocked(uint32_t appid) {
  return appid_in_list(appid, gAllowlist, gAllowlistCount);
}

static bool is_allowlisted(uint32_t appid) {
  (void)pthread_mutex_lock(&gAllowlistLock);
  bool found = is_allowlisted_unlocked(appid);
  (void)pthread_mutex_unlock(&gAllowlistLock);
  return found;
}

static bool is_store_managed(uint32_t appid) {
  return is_allowlisted(appid);
}

static bool is_managed_shortcut(uint32_t shortcut_id) {
  bool found;
  (void)pthread_mutex_lock(&gAllowlistLock);
  found = shortcut_in_registry(
      shortcut_id,
      gManagedShortcuts,
      gManagedShortcutCount,
      NULL);
  (void)pthread_mutex_unlock(&gAllowlistLock);
  return found;
}

static bool shortcut_in_registry(
    uint32_t shortcut_id,
    const managed_shortcut *shortcuts,
    size_t count,
    const managed_shortcut **shortcut_out) {
  for (size_t index = 0; index < count; ++index) {
    if (shortcuts[index].id == shortcut_id) {
      if (shortcut_out != NULL) {
        *shortcut_out = &shortcuts[index];
      }
      return true;
    }
  }
  return false;
}

static bool lookup_managed_shortcut(
    uint32_t shortcut_id, managed_shortcut *shortcut_out) {
  bool found = false;
  (void)pthread_mutex_lock(&gAllowlistLock);
  const managed_shortcut *value = NULL;
  if (shortcut_in_registry(
          shortcut_id, gManagedShortcuts,
          gManagedShortcutCount, &value)) {
    *shortcut_out = *value;
    found = true;
  }
  (void)pthread_mutex_unlock(&gAllowlistLock);
  return found;
}

static const char *environment_value(
    char *const environment[], const char *name) {
  if (environment == NULL || name == NULL) {
    return NULL;
  }
  size_t name_length = strlen(name);
  for (size_t index = 0; environment[index] != NULL; ++index) {
    if (
        strncmp(environment[index], name, name_length) == 0 &&
        environment[index][name_length] == '='
    ) {
      return environment[index] + name_length + 1;
    }
  }
  return NULL;
}

static uint32_t spawn_appid(char *const environment[]) {
  static const char *const names[] = {
      "STEAM_COMPAT_APP_ID",
      "SteamAppId",
      "SteamGameId",
  };
  for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
    const char *value = environment_value(environment, names[index]);
    if (value == NULL || *value == '\0') {
      continue;
    }
    errno = 0;
    char *end = NULL;
    unsigned long parsed = strtoul(value, &end, 10);
    if (
        errno == 0 && end != value && *end == '\0' &&
        parsed > 0 && parsed <= UINT32_MAX
    ) {
      return (uint32_t)parsed;
    }
  }
  return 0;
}

static bool blocked_redirect_environment(const char *entry) {
  return
      entry == NULL ||
      strncmp(entry, "HOME=", 5) == 0 ||
      strncmp(entry, "PYTHON", 6) == 0 ||
      strncmp(entry, "DYLD_", 5) == 0 ||
      strncmp(entry, "REALSTEAMONMAC_", 15) == 0;
}

static bool build_redirect_environment(
    char *const source[],
    const char *trusted_home,
    char ***environment_out,
    char **home_entry_out) {
  if (
      trusted_home == NULL || *trusted_home == '\0' ||
      environment_out == NULL || home_entry_out == NULL
  ) {
    return false;
  }
  size_t source_count = 0;
  if (source != NULL) {
    while (
        source_count < 4096 &&
        source[source_count] != NULL
    ) {
      ++source_count;
    }
    if (source_count == 4096) {
      return false;
    }
  }

  char **environment =
      calloc(source_count + 2, sizeof(*environment));
  size_t home_length = strlen(trusted_home);
  char *home_entry = malloc(home_length + 6);
  if (environment == NULL || home_entry == NULL) {
    free(environment);
    free(home_entry);
    return false;
  }
  memcpy(home_entry, "HOME=", 5);
  memcpy(home_entry + 5, trusted_home, home_length + 1);

  size_t output_count = 0;
  for (size_t index = 0; index < source_count; ++index) {
    if (!blocked_redirect_environment(source[index])) {
      environment[output_count++] = source[index];
    }
  }
  environment[output_count++] = home_entry;
  environment[output_count] = NULL;
  *environment_out = environment;
  *home_entry_out = home_entry;
  return true;
}

static bool has_exe_suffix(const char *path) {
  if (path == NULL) {
    return false;
  }
  size_t length = strlen(path);
  return length >= 4 && strcasecmp(path + length - 4, ".exe") == 0;
}

static bool has_app_suffix(const char *path) {
  if (path == NULL) {
    return false;
  }
  size_t length = strlen(path);
  return length >= 4 && strcasecmp(path + length - 4, ".app") == 0;
}

static bool is_pe_executable(const char *path) {
  if (!has_exe_suffix(path)) {
    return false;
  }
  FILE *stream = fopen(path, "rb");
  if (stream == NULL) {
    return false;
  }
  unsigned char magic[2] = {0, 0};
  bool matches =
      fread(magic, sizeof(magic), 1, stream) == 1 &&
      magic[0] == 'M' && magic[1] == 'Z';
  fclose(stream);
  return matches;
}

static bool path_contains_control_byte(const char *path) {
  if (path == NULL) {
    return true;
  }
  for (const unsigned char *cursor =
           (const unsigned char *)path;
       *cursor != '\0'; ++cursor) {
    if (*cursor < 0x20 || *cursor == 0x7f) {
      return true;
    }
  }
  return false;
}

static bool path_has_symlink_component(const char *path) {
  if (
      path == NULL || path[0] != '/' ||
      strlen(path) >= PATH_MAX
  ) {
    return true;
  }
  char candidate[PATH_MAX];
  strcpy(candidate, path);
  for (char *cursor = candidate + 1;; ++cursor) {
    if (*cursor != '/' && *cursor != '\0') {
      continue;
    }
    char saved = *cursor;
    *cursor = '\0';
    struct stat item;
    bool invalid =
        lstat(candidate, &item) != 0 ||
        S_ISLNK(item.st_mode);
    *cursor = saved;
    if (invalid) {
      return true;
    }
    if (saved == '\0') {
      break;
    }
  }
  return false;
}

static bool shortcut_file_identity_matches(
    const shortcut_file_identity *left,
    const shortcut_file_identity *right) {
  return
      left->device == right->device &&
      left->inode == right->inode &&
      left->size == right->size &&
      left->modification_time.tv_sec == right->modification_time.tv_sec &&
      left->modification_time.tv_nsec == right->modification_time.tv_nsec &&
      left->change_time.tv_sec == right->change_time.tv_sec &&
      left->change_time.tv_nsec == right->change_time.tv_nsec;
}

static bool validate_shortcut_target(
    const char *candidate,
    char canonical[PATH_MAX],
    shortcut_file_identity *identity_out) {
  if (
      candidate == NULL || candidate[0] != '/' ||
      path_contains_control_byte(candidate) ||
      !has_exe_suffix(candidate) ||
      path_has_symlink_component(candidate)
  ) {
    return false;
  }
  char resolved[PATH_MAX];
  if (realpath(candidate, resolved) == NULL) {
    return false;
  }
  if (
      path_has_symlink_component(resolved) ||
      !has_exe_suffix(resolved)
  ) {
    return false;
  }

  int descriptor = open(resolved, O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    return false;
  }
  struct stat file_stat;
  unsigned char magic[2] = {0, 0};
  bool valid =
      fstat(descriptor, &file_stat) == 0 &&
      S_ISREG(file_stat.st_mode) &&
      pread(descriptor, magic, sizeof(magic), 0) == (ssize_t)sizeof(magic) &&
      magic[0] == 'M' && magic[1] == 'Z';
  if (close(descriptor) != 0) {
    valid = false;
  }
  if (!valid) {
    return false;
  }
  strcpy(canonical, resolved);
  if (identity_out != NULL) {
    identity_out->device = file_stat.st_dev;
    identity_out->inode = file_stat.st_ino;
    identity_out->size = file_stat.st_size;
    identity_out->modification_time = file_stat.st_mtimespec;
    identity_out->change_time = file_stat.st_ctimespec;
  }
  return true;
}

static bool validate_registered_shortcut(
    uint32_t shortcut_id,
    const char *candidate,
    char registered_target[PATH_MAX]) {
  managed_shortcut registered;
  shortcut_file_identity current_identity;
  char canonical[PATH_MAX];
  if (
      !lookup_managed_shortcut(shortcut_id, &registered) ||
      !validate_shortcut_target(
          candidate, canonical, &current_identity) ||
      strcmp(registered.target, canonical) != 0 ||
      !shortcut_file_identity_matches(
          &registered.identity, &current_identity)
  ) {
    return false;
  }
  if (registered_target != NULL) {
    strcpy(registered_target, registered.target);
  }
  return true;
}

static bool validate_runtime_script(
    const char *path, uid_t expected_owner) {
  if (
      path == NULL ||
      path_has_symlink_component(path)
  ) {
    return false;
  }
  int descriptor = open(path, O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    return false;
  }
  struct stat file_stat;
  bool valid =
      fstat(descriptor, &file_stat) == 0 &&
      S_ISREG(file_stat.st_mode) &&
      file_stat.st_uid == expected_owner &&
      (file_stat.st_mode & 022) == 0;
  if (close(descriptor) != 0) {
    valid = false;
  }
  return valid;
}

static bool is_missing_launch_target(const char *path) {
  if (
      path == NULL ||
      (!has_exe_suffix(path) && !has_app_suffix(path))
  ) {
    return false;
  }
  struct stat file_stat;
  if (lstat(path, &file_stat) == 0) {
    return false;
  }
  return errno == ENOENT || errno == ENOTDIR;
}

__attribute__((visibility("default")))
int realsteamonmac_should_redirect_spawn(
    const char *path, char *const environment[]) {
  ensure_allowlist_loaded();
  uint32_t appid = spawn_appid(environment);
  if (appid == 0) {
    return 0;
  }
  if (is_store_managed(appid)) {
    return
        is_pe_executable(path) ||
        is_missing_launch_target(path) ||
        has_app_suffix(path);
  }
  return validate_registered_shortcut(appid, path, NULL);
}

static int redirect_spawn_with(
    posix_spawn_function original,
    pid_t *restrict pid,
    const char *restrict path,
    const posix_spawn_file_actions_t *file_actions,
    const posix_spawnattr_t *restrict attributes,
    char *const argv[restrict],
    char *const envp[restrict]) {
  if (
      original == NULL ||
      !realsteamonmac_should_redirect_spawn(path, envp)
  ) {
    return original != NULL
               ? original(
                     pid, path, file_actions, attributes, argv, envp)
               : ENOSYS;
  }

  const char *home = getenv("HOME");
  if (home == NULL || *home == '\0') {
    return original(
        pid, path, file_actions, attributes, argv, envp);
  }
  char runtime[1200];
  if (
      snprintf(
          runtime, sizeof(runtime),
          "%s/Library/Application Support/RealSteamOnMac/"
          "runtimes/bin/realsteamonmac-runtime",
          home) >= (int)sizeof(runtime) ||
      !validate_runtime_script(runtime, geteuid())
  ) {
    log_line("spawn: runtime entrypoint is unavailable");
    return original(
        pid, path, file_actions, attributes, argv, envp);
  }

  uint32_t appid = spawn_appid(envp);
  bool store_app = is_store_managed(appid);
  char registered_target[PATH_MAX];
  const char *launch_target = path;
  const char *identity_flag = "--appid";
  if (!store_app) {
    if (!validate_registered_shortcut(
            appid, path, registered_target)) {
      return original(
          pid, path, file_actions, attributes, argv, envp);
    }
    launch_target = registered_target;
    identity_flag = "--shortcut-id";
  }
  char appid_text[16];
  snprintf(appid_text, sizeof(appid_text), "%u", appid);

  size_t original_count = 0;
  if (argv != NULL) {
    while (original_count < 1024 && argv[original_count] != NULL) {
      ++original_count;
    }
    if (original_count == 1024) {
      log_line("spawn: refused oversized argument vector");
      return E2BIG;
    }
  }

  // python3, -I, runtime, launch, identity, value, executable, args...
  size_t redirected_count = 7 + (original_count > 0 ? original_count - 1 : 0);
  char **redirected = calloc(redirected_count + 1, sizeof(*redirected));
  if (redirected == NULL) {
    return ENOMEM;
  }
  redirected[0] = "/usr/bin/python3";
  redirected[1] = "-I";
  redirected[2] = runtime;
  redirected[3] = "launch";
  redirected[4] = (char *)identity_flag;
  redirected[5] = appid_text;
  redirected[6] = (char *)launch_target;
  for (size_t index = 1; index < original_count; ++index) {
    redirected[6 + index] = argv[index];
  }

  char **redirect_environment = NULL;
  char *redirect_home = NULL;
  if (!build_redirect_environment(
          envp, home, &redirect_environment, &redirect_home)) {
    free(redirected);
    return E2BIG;
  }

  char message[256];
  if (store_app) {
    snprintf(
        message, sizeof(message),
        "spawn: redirecting store AppID %u through runtime", appid);
  } else {
    snprintf(
        message, sizeof(message),
        "spawn: redirecting shortcut ID %u through runtime", appid);
  }
  log_line(message);
  int result = original(
      pid, "/usr/bin/python3", file_actions, attributes,
      redirected, redirect_environment);
  free(redirect_home);
  free(redirect_environment);
  free(redirected);
  return result;
}

static int realsteamonmac_posix_spawn(
    pid_t *restrict pid,
    const char *restrict path,
    const posix_spawn_file_actions_t *file_actions,
    const posix_spawnattr_t *restrict attributes,
    char *const argv[restrict],
    char *const envp[restrict]) {
  return redirect_spawn_with(
      gOriginalPosixSpawn,
      pid,
      path,
      file_actions,
      attributes,
      argv,
      envp);
}

#if defined(REALSTEAMONMAC_TESTING)
__attribute__((visibility("default")))
int realsteamonmac_test_spawn_redirect(
    posix_spawn_function original,
    const char *path,
    char *const argv[],
    char *const envp[]) {
  return redirect_spawn_with(
      original, NULL, path, NULL, NULL, argv, envp);
}
#endif

static void patch_steamclient_spawn_redirect(
    const struct mach_header *header) {
  const steamclient_profile *profile =
      steamclient_profile_for_header(header);
  if (gSteamClientSpawnPatched || profile == NULL) {
    return;
  }

  void **slot = (void **)(
      (uintptr_t)header + profile->posix_spawn_pointer_offset);
  void *current = NULL;
  memcpy(&current, slot, sizeof(current));
  void *expected = dlsym(RTLD_DEFAULT, "posix_spawn");
  if (current == (void *)&realsteamonmac_posix_spawn) {
    gSteamClientSpawnPatched = true;
    return;
  }
  if (current == NULL || expected == NULL || current != expected) {
    log_line("spawn: refused unexpected steamclient posix_spawn pointer");
    return;
  }

  Dl_info information;
  memset(&information, 0, sizeof(information));
  if (
      dladdr(current, &information) == 0 ||
      information.dli_fname == NULL ||
      (
          strstr(information.dli_fname, "libsystem_kernel.dylib") == NULL &&
          strstr(information.dli_fname, "libSystem.B.dylib") == NULL
      )
  ) {
    log_line("spawn: refused non-system posix_spawn implementation");
    return;
  }

  long raw_page_size = sysconf(_SC_PAGESIZE);
  if (raw_page_size <= 0) {
    return;
  }
  uintptr_t page_size = (uintptr_t)raw_page_size;
  uintptr_t page = (uintptr_t)slot & ~(page_size - 1);
  if (
      mach_vm_protect(
          mach_task_self(), (mach_vm_address_t)page,
          (mach_vm_size_t)page_size, false,
          VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) != KERN_SUCCESS
  ) {
    log_line("spawn: could not make symbol pointer writable");
    return;
  }

  gOriginalPosixSpawn = (posix_spawn_function)current;
  void *replacement = (void *)&realsteamonmac_posix_spawn;
  memcpy(slot, &replacement, sizeof(replacement));
  (void)mach_vm_protect(
      mach_task_self(), (mach_vm_address_t)page,
      (mach_vm_size_t)page_size, false,
      VM_PROT_READ | VM_PROT_WRITE);
  gSteamClientSpawnPatched = true;
  log_line("spawn: installed allowlist-scoped launch redirect");
}

static void add_allowlist_appid(uint32_t appid) {
  if (appid == 0 || is_allowlisted_unlocked(appid) ||
      gAllowlistCount >= MAX_ALLOWLIST_APPIDS) {
    return;
  }
  gAllowlist[gAllowlistCount++] = appid;
}

static size_t copy_allowlist(uint32_t destination[MAX_ALLOWLIST_APPIDS]) {
  (void)pthread_mutex_lock(&gAllowlistLock);
  size_t count = gAllowlistCount;
  memcpy(destination, gAllowlist, count * sizeof(*destination));
  (void)pthread_mutex_unlock(&gAllowlistLock);
  return count;
}

static void parse_allowlist_text(char *text) {
  char *cursor = text;
  while (cursor != NULL && *cursor != '\0') {
    char *end = cursor;
    while (*end != '\0' && *end != ',' && *end != '\n' &&
           *end != '\r' && *end != ' ' && *end != '\t') {
      ++end;
    }
    char saved = *end;
    *end = '\0';

    if (*cursor != '\0' && *cursor != '#') {
      char *number_end = NULL;
      unsigned long value = strtoul(cursor, &number_end, 10);
      if (number_end != cursor && *number_end == '\0' &&
          value > 0 && value <= UINT32_MAX) {
        add_allowlist_appid((uint32_t)value);
      }
    }

    if (saved == '\0') {
      break;
    }
    cursor = end + 1;
    while (*cursor == ',' || *cursor == '\n' || *cursor == '\r' ||
           *cursor == ' ' || *cursor == '\t') {
      ++cursor;
    }
  }
}

static bool support_file_path(
    const char *filename, char path[1200]) {
  const char *home = getenv("HOME");
  if (home == NULL) {
    return false;
  }
  return snprintf(
             path, 1200,
             "%s/Library/Application Support/RealSteamOnMac/%s",
             home, filename) < 1200;
}

static void parse_allowlist_file(const char *path) {
  FILE *stream = fopen(path, "r");
  if (stream == NULL) {
    return;
  }
  char line[256];
  while (fgets(line, sizeof(line), stream) != NULL) {
    parse_allowlist_text(line);
  }
  fclose(stream);
}

static void load_allowlist(void) {
  (void)pthread_mutex_lock(&gAllowlistLock);
  if (atomic_load_explicit(&gAllowlistLoaded, memory_order_acquire)) {
    (void)pthread_mutex_unlock(&gAllowlistLock);
    return;
  }
  gAllowlistCount = 0;
  gManagedShortcutCount = 0;

  const char *environment = getenv("REALSTEAMONMAC_APPIDS");
  if (environment != NULL && *environment != '\0') {
    char *copy = strdup(environment);
    if (copy != NULL) {
      parse_allowlist_text(copy);
      free(copy);
    }
  }

  char path[1200];
  if (support_file_path("allowlist.txt", path)) {
    parse_allowlist_file(path);
  }

  bool loaded_typed_cache = false;
  managed_registry cached;
  if (load_managed_registry_cache(&cached)) {
    bool collision = false;
    size_t combined_count = gAllowlistCount;
    for (size_t index = 0; index < cached.shortcut_count; ++index) {
      if (is_allowlisted_unlocked(cached.shortcuts[index].id)) {
        collision = true;
        break;
      }
    }
    for (
        size_t index = 0;
        !collision && index < cached.appid_count;
        ++index
    ) {
      if (!is_allowlisted_unlocked(cached.appids[index])) {
        ++combined_count;
      }
    }
    if (
        combined_count + cached.shortcut_count >
        MAX_ALLOWLIST_APPIDS
    ) {
      collision = true;
    }
    if (
        !collision &&
        cached.shortcut_count > 0 &&
        !persist_managed_registry(&cached)
    ) {
      collision = true;
    }
    if (!collision) {
      for (size_t index = 0; index < cached.appid_count; ++index) {
        add_allowlist_appid(cached.appids[index]);
      }
      memcpy(
          gManagedShortcuts,
          cached.shortcuts,
          cached.shortcut_count * sizeof(*gManagedShortcuts));
      gManagedShortcutCount = cached.shortcut_count;
      loaded_typed_cache = true;
    }
  }
  if (
      !loaded_typed_cache &&
      support_file_path("managed-appids-cache.txt", path)
  ) {
    parse_allowlist_file(path);
  }

  managed_registry loaded;
  memset(&loaded, 0, sizeof(loaded));
  loaded.appid_count = gAllowlistCount;
  memcpy(
      loaded.appids,
      gAllowlist,
      gAllowlistCount * sizeof(*gAllowlist));
  loaded.shortcut_count = gManagedShortcutCount;
  memcpy(
      loaded.shortcuts,
      gManagedShortcuts,
      gManagedShortcutCount * sizeof(*gManagedShortcuts));
  bool migration_persisted = true;
  if (!loaded_typed_cache && loaded.appid_count > 0) {
    migration_persisted = persist_managed_registry(&loaded);
  }
  atomic_store_explicit(
      &gAllowlistLoaded, true, memory_order_release);
  (void)pthread_mutex_unlock(&gAllowlistLock);

  char message[160];
  snprintf(
      message, sizeof(message),
      "allowlist: loaded %zu store app(s) and %zu shortcut(s)",
      loaded.appid_count, loaded.shortcut_count);
  log_line(message);
  if (!migration_persisted) {
    log_line("allowlist: failed to migrate legacy registry cache");
  }
}

static void ensure_allowlist_loaded(void) {
  if (!atomic_load_explicit(&gAllowlistLoaded, memory_order_acquire)) {
    load_allowlist();
  }
}

static bool encode_branch(void *source, void *destination,
                          uint32_t *instruction_out) {
  intptr_t delta = (uint8_t *)destination - (uint8_t *)source;
  if ((delta & 3) != 0 ||
      delta < -(intptr_t)(1U << 27) ||
      delta >= (intptr_t)(1U << 27)) {
    return false;
  }
  uint32_t immediate = (uint32_t)((delta >> 2) & 0x03FFFFFF);
  *instruction_out = 0x14000000 | immediate;
  return true;
}

static void *allocate_near_page(void *target, size_t *page_size_out) {
  long raw_page_size = sysconf(_SC_PAGESIZE);
  if (raw_page_size <= 0) {
    return NULL;
  }
  size_t page_size = (size_t)raw_page_size;
  uintptr_t target_page =
      (uintptr_t)target & ~((uintptr_t)page_size - (uintptr_t)1);

  for (uintptr_t distance = page_size; distance <= 0x07000000;
       distance += page_size) {
    for (int direction = 0; direction < 2; ++direction) {
      if (
          (direction == 0 && target_page > UINTPTR_MAX - distance) ||
          (direction == 1 && target_page < distance)
      ) {
        continue;
      }
      mach_vm_address_t candidate =
          direction == 0
              ? (mach_vm_address_t)(target_page + distance)
              : (mach_vm_address_t)(target_page - distance);
      kern_return_t result =
          mach_vm_allocate(
              mach_task_self(), &candidate,
              (mach_vm_size_t)page_size, VM_FLAGS_FIXED);
      if (result != KERN_SUCCESS) {
        continue;
      }
      void *memory = (void *)(uintptr_t)candidate;

      uint32_t branch = 0;
      if (!encode_branch(target, memory, &branch)) {
        (void)mach_vm_deallocate(
            mach_task_self(), candidate, (mach_vm_size_t)page_size);
        continue;
      }
      *page_size_out = page_size;
      return memory;
    }
  }
  return NULL;
}

static void release_allocated_page(void *memory, size_t page_size) {
  (void)mach_vm_deallocate(
      mach_task_self(), (mach_vm_address_t)(uintptr_t)memory,
      (mach_vm_size_t)page_size);
}

// Builds a near branch island that reproduces `tbnz w8, #4, <invalid>` for
// non-allowlisted AppIDs while forcing allowlisted AppIDs straight to the
// gate's fall-through (the real ownership/depot path). The AppID being
// validated lives in w21 throughout GetAppForInstallation (confirmed via the
// runtime breakpoint diagnostics), so we compare against it directly.
//
// Trampoline layout (per allowlisted AppID, then a shared tail):
//   movz w10, #<appid_lo>
//   movk w10, #<appid_hi>, lsl #16
//   cmp  w21, w10
//   b.eq skip                ; allowlisted -> behave as if bit 4 were clear
//   ... (repeat per AppID) ...
//   tbnz w8, #4, invalid     ; original veto for everyone else
// skip:
//   b    <profile fall-through> ; continue installing
// invalid:
//   b    <profile invalid target> ; original "Invalid platform" branch
static void *build_install_gate_trampoline(void *target,
                                           uintptr_t module_base,
                                           const steamclient_profile *profile) {
  uint32_t allowlist[MAX_ALLOWLIST_APPIDS];
  size_t allowlist_count = copy_allowlist(allowlist);
  if (allowlist_count == 0) {
    return NULL;
  }

  size_t page_size = 0;
  void *memory = allocate_near_page(target, &page_size);
  if (memory == NULL) {
    return NULL;
  }

  size_t required_words = (allowlist_count * 4) + 3;
  if (required_words > page_size / sizeof(uint32_t)) {
    release_allocated_page(memory, page_size);
    return NULL;
  }

  uint32_t *instructions = (uint32_t *)memory;
  size_t branch_indices[MAX_ALLOWLIST_APPIDS];
  size_t cursor = 0;
  for (size_t index = 0; index < allowlist_count; ++index) {
    uint32_t appid = allowlist[index];
    uint32_t low = appid & 0xFFFF;
    uint32_t high = appid >> 16;
    instructions[cursor++] = 0x5280000A | (low << 5);   // movz w10, #low
    instructions[cursor++] = 0x72A0000A | (high << 5);  // movk w10, #high, lsl 16
    instructions[cursor++] = 0x6B0A02BF;                // cmp w21, w10
    branch_indices[index] = cursor;
    instructions[cursor++] = 0;  // b.eq skip (patched below)
  }

  size_t tbnz_index = cursor;
  instructions[cursor++] = 0;  // tbnz w8, #4, invalid (patched below)
  size_t skip_index = cursor;
  instructions[cursor++] = 0;  // b <module + fall-through> (patched below)
  size_t invalid_index = cursor;
  instructions[cursor++] = 0;  // b <module + invalid> (patched below)

  for (size_t index = 0; index < allowlist_count; ++index) {
    intptr_t delta = (intptr_t)skip_index - (intptr_t)branch_indices[index];
    if (delta < -(1 << 18) || delta >= (1 << 18)) {
      release_allocated_page(memory, page_size);
      return NULL;
    }
    uint32_t immediate = (uint32_t)delta & 0x7FFFF;
    instructions[branch_indices[index]] =
        0x54000000 | (immediate << 5);  // b.eq skip
  }

  {
    intptr_t delta = (intptr_t)invalid_index - (intptr_t)tbnz_index;
    uint32_t imm14 = (uint32_t)delta & 0x3FFF;
    instructions[tbnz_index] =
        0x37200008 | (imm14 << 5);  // tbnz w8, #4, invalid
  }

  uint32_t branch = 0;
  if (!encode_branch(
          &instructions[skip_index],
          (void *)(module_base +
                   profile->install_gate_fallthrough_offset),
          &branch)) {
    release_allocated_page(memory, page_size);
    return NULL;
  }
  instructions[skip_index] = branch;

  if (!encode_branch(
          &instructions[invalid_index],
          (void *)(module_base + profile->install_gate_invalid_offset),
          &branch)) {
    release_allocated_page(memory, page_size);
    return NULL;
  }
  instructions[invalid_index] = branch;

  size_t code_size = cursor * sizeof(uint32_t);
  sys_icache_invalidate(memory, code_size);
  if (mprotect(memory, page_size, PROT_READ | PROT_EXEC) != 0) {
    release_allocated_page(memory, page_size);
    return NULL;
  }
  return memory;
}

static void finish_install_gate_update(
    uint64_t generation, bool patched) {
  atomic_store_explicit(
      &gSteamClientInstallGatePatched, patched, memory_order_release);
  atomic_store_explicit(
      &gInstallGateRefreshRequested, false, memory_order_release);
  if (
      atomic_load_explicit(
          &gAllowlistGeneration, memory_order_acquire) != generation
  ) {
    atomic_store_explicit(
        &gSteamClientInstallGatePatched, false, memory_order_release);
    atomic_store_explicit(
        &gInstallGateRefreshRequested, true, memory_order_release);
  }
}

static void patch_steamclient_install_gate(const struct mach_header *header,
                                           intptr_t slide) {
  const steamclient_profile *profile =
      steamclient_profile_for_header(header);
  bool refresh_requested =
      atomic_load_explicit(
          &gInstallGateRefreshRequested, memory_order_acquire);
  if (
      (atomic_load_explicit(
           &gSteamClientInstallGatePatched, memory_order_acquire) &&
       !refresh_requested) ||
      profile == NULL
  ) {
    return;
  }

  ensure_allowlist_loaded();
  uint64_t generation =
      atomic_load_explicit(
          &gAllowlistGeneration, memory_order_acquire);
  uint32_t allowlist[MAX_ALLOWLIST_APPIDS];
  size_t allowlist_count = copy_allowlist(allowlist);

  uint8_t *target =
      (uint8_t *)((uintptr_t)header + profile->install_gate_offset);
  uint32_t current = 0;
  memcpy(&current, target, sizeof(current));
  if (current != kSteamClientInstallGateExpected) {
    if (
        (current & 0xFC000000) == 0x14000000 &&
        !refresh_requested
    ) {
      atomic_store_explicit(
          &gSteamClientInstallGatePatched, true, memory_order_release);
      log_line("steamclient: install gate already redirected");
      return;
    }
    if ((current & 0xFC000000) != 0x14000000) {
      log_line("steamclient: refused unexpected install gate bytes");
      return;
    }
  }

  if (allowlist_count == 0) {
    if (current != kSteamClientInstallGateExpected) {
      uintptr_t page = 0;
      size_t protected_size = 0;
      if (!make_text_writable(
              target, sizeof(kSteamClientInstallGateExpected),
              &page, &protected_size)) {
        log_line("steamclient: could not restore empty install gate");
        return;
      }
      memcpy(
          target, &kSteamClientInstallGateExpected,
          sizeof(kSteamClientInstallGateExpected));
      sys_icache_invalidate(
          target, sizeof(kSteamClientInstallGateExpected));
      restore_text_protection(page, protected_size);
    }
    finish_install_gate_update(generation, false);
    log_line("steamclient: install gate restored (empty allowlist)");
    return;
  }

  void *branch_target =
      build_install_gate_trampoline(target, (uintptr_t)header, profile);
  if (branch_target == NULL) {
    log_line("steamclient: could not build install gate filter");
    return;
  }

  uint32_t branch = 0;
  if (!encode_branch(target, branch_target, &branch)) {
    log_line("steamclient: generated install gate filter is not reachable");
    return;
  }

  uintptr_t page = 0;
  size_t protected_size = 0;
  if (!make_text_writable(target, sizeof(branch), &page, &protected_size)) {
    log_line("steamclient: could not make install gate writable");
    return;
  }
  memcpy(target, &branch, sizeof(branch));
  sys_icache_invalidate(target, sizeof(branch));
  restore_text_protection(page, protected_size);
  finish_install_gate_update(generation, true);

  char message[224];
  snprintf(message, sizeof(message),
           "steamclient: install gate patched build=%s slide=%p target=%p "
           "trampoline=%p appids=%zu",
           profile->build,
           (void *)slide, (void *)target, branch_target, allowlist_count);
  log_line(message);
}

static void patch_steamclient(const struct mach_header *header,
                              intptr_t slide) {
  const steamclient_profile *profile =
      steamclient_profile_for_header(header);
  if (gSteamClientPatched || profile == NULL) {
    return;
  }

  uint8_t *target =
      (uint8_t *)((uintptr_t)header + profile->compat_gate_offset);
  uint32_t current[2];
  memcpy(current, target, sizeof(current));
  if (memcmp(current, kSteamClientForcedTrue, sizeof(current)) == 0) {
    gSteamClientPatched = true;
    log_line("steamclient: compatibility gate already patched");
    return;
  }
  if (memcmp(current, kSteamClientExpected, sizeof(current)) != 0) {
    log_line("steamclient: refused unexpected compatibility gate bytes");
    return;
  }

  uintptr_t page = 0;
  size_t protected_size = 0;
  if (!make_text_writable(target, sizeof(kSteamClientForcedTrue),
                          &page, &protected_size)) {
    log_line("steamclient: could not make compatibility gate writable");
    return;
  }
  memcpy(target, kSteamClientForcedTrue, sizeof(kSteamClientForcedTrue));
  sys_icache_invalidate(target, sizeof(kSteamClientForcedTrue));
  restore_text_protection(page, protected_size);
  gSteamClientPatched = true;

  char message[160];
  snprintf(message, sizeof(message),
           "steamclient: patched build=%s slide=%p target=%p",
           profile->build, (void *)slide, (void *)target);
  log_line(message);
}

static void image_added(const struct mach_header *header, intptr_t slide) {
  patch_steamclient(header, slide);
  patch_steamclient_install_gate(header, slide);
  patch_steamclient_spawn_redirect(header);
}

__attribute__((visibility("default")))
void realsteamonmac_apply_text_hooks(void) {
  ensure_allowlist_loaded();
  if (!gRegistered) {
    gRegistered = true;
    _dyld_register_func_for_add_image(image_added);
  }
}

static bool read_process_memory(mach_vm_address_t address,
                                void *destination, size_t length) {
  mach_vm_size_t bytes_read = 0;
  kern_return_t result =
      mach_vm_read_overwrite(mach_task_self(), address, length,
                             (mach_vm_address_t)destination, &bytes_read);
  return result == KERN_SUCCESS && bytes_read == length;
}

static void track_object(mach_vm_address_t address) {
  for (size_t index = 0; index < gTrackedObjectCount; ++index) {
    if (gTrackedObjects[index] == address) {
      return;
    }
  }
  if (gTrackedObjectCount < MAX_TRACKED_APP_OBJECTS) {
    gTrackedObjects[gTrackedObjectCount++] = address;
  }
}

typedef struct {
  size_t valid;
  size_t patched;
} tracked_refresh_result;

static tracked_refresh_result refresh_tracked_objects(void) {
  tracked_refresh_result result = {0, 0};
  const steamui_profile *profile = NULL;
  const struct mach_header *steamui = find_steamui_image(&profile);
  if (steamui == NULL || profile == NULL) {
    gTrackedObjectCount = 0;
    return result;
  }

  uintptr_t getter =
      (uintptr_t)steamui + profile->platform_flags_getter_offset;
  size_t index = 0;
  while (index < gTrackedObjectCount) {
    mach_vm_address_t address = gTrackedObjects[index];
    uint8_t bytes[0x20];
    uintptr_t vtable = 0;
    uintptr_t method = 0;
    uint32_t appid = 0;
    uint32_t flags = 0;
    bool valid =
        read_process_memory(address, bytes, sizeof(bytes));
    if (valid) {
      memcpy(&vtable, bytes, sizeof(vtable));
      memcpy(&appid, bytes + 0x08, sizeof(appid));
      memcpy(&flags, bytes + 0x1C, sizeof(flags));
      valid =
          vtable != 0 &&
          is_allowlisted(appid) &&
          read_process_memory(
              (mach_vm_address_t)(vtable + 0x68),
              &method, sizeof(method)) &&
          method == getter;
    }

    if (!valid) {
      gTrackedObjects[index] =
          gTrackedObjects[gTrackedObjectCount - 1];
      --gTrackedObjectCount;
      continue;
    }

    ++result.valid;
    if ((flags & PLATFORM_INVALID_BIT) != 0) {
      uint32_t filtered = flags & ~PLATFORM_INVALID_BIT;
      if (mach_vm_write(
              mach_task_self(),
              address + 0x1C,
              (vm_offset_t)&filtered,
              (mach_msg_type_number_t)sizeof(filtered)) ==
          KERN_SUCCESS) {
        ++result.patched;
      }
    }
    ++index;
  }
  return result;
}

__attribute__((visibility("default")))
size_t realsteamonmac_apply_data_overrides(void) {
  ensure_allowlist_loaded();
  uint32_t allowlist[MAX_ALLOWLIST_APPIDS];
  size_t allowlist_count = copy_allowlist(allowlist);
  const steamui_profile *profile = NULL;
  const struct mach_header *steamui = find_steamui_image(&profile);
  if (steamui == NULL || profile == NULL) {
    log_line("data override: matching steamui image was not found");
    return 0;
  }
  if (!gDataScanStartedLogged) {
    gDataScanStartedLogged = true;
    log_line("data override: first reconciliation scan started");
  }

  mach_vm_address_t getter =
      (mach_vm_address_t)((uintptr_t)steamui +
                          profile->platform_flags_getter_offset);
  const size_t chunk_capacity = 1024 * 1024;
  uint8_t *chunk = malloc(chunk_capacity);
  if (chunk == NULL) {
    log_line("data override: could not allocate scan buffer");
    return 0;
  }

  size_t patched = 0;
  size_t allowlisted_candidates = 0;
  size_t invalid_candidates = 0;
  size_t getter_matches = 0;
  mach_vm_address_t region = 0;
  for (;;) {
    mach_vm_size_t region_size = 0;
    vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t info_count = VM_REGION_BASIC_INFO_COUNT_64;
    mach_port_t object_name = MACH_PORT_NULL;
    kern_return_t result =
        mach_vm_region(mach_task_self(), &region, &region_size,
                       VM_REGION_BASIC_INFO_64,
                       (vm_region_info_t)&info, &info_count, &object_name);
    if (result != KERN_SUCCESS) {
      break;
    }

    mach_vm_address_t next_region = region + region_size;
    bool readable = (info.protection & VM_PROT_READ) != 0;
    bool writable = (info.protection & VM_PROT_WRITE) != 0;
    if (readable && writable && region_size >= 0x20) {
      mach_vm_address_t cursor = region;
      while (cursor < next_region) {
        size_t requested = (size_t)(next_region - cursor);
        if (requested > chunk_capacity) {
          requested = chunk_capacity;
        }
        mach_vm_size_t bytes_read = 0;
        result = mach_vm_read_overwrite(
            mach_task_self(), cursor, requested,
            (mach_vm_address_t)chunk, &bytes_read);
        if (result != KERN_SUCCESS || bytes_read < 0x20) {
          break;
        }

        for (size_t offset = 0; offset + 0x20 <= bytes_read; offset += 4) {
          uint32_t appid = 0;
          uint32_t flags = 0;
          uintptr_t vtable = 0;
          memcpy(&vtable, chunk + offset, sizeof(vtable));
          memcpy(&appid, chunk + offset + 0x08, sizeof(appid));
          memcpy(&flags, chunk + offset + 0x1C, sizeof(flags));
          if (!appid_in_list(appid, allowlist, allowlist_count)) {
            continue;
          }
          ++allowlisted_candidates;
          if (vtable == 0) {
            continue;
          }
          if ((flags & PLATFORM_INVALID_BIT) != 0) {
            ++invalid_candidates;
          }

          uintptr_t method = 0;
          if (!read_process_memory(
                  (mach_vm_address_t)(vtable + 0x68),
                  &method, sizeof(method)) ||
              method != getter) {
            continue;
          }
          ++getter_matches;
          track_object(cursor + offset);
          if ((flags & PLATFORM_INVALID_BIT) == 0) {
            continue;
          }

          uint32_t filtered = flags & ~PLATFORM_INVALID_BIT;
          mach_vm_address_t field = cursor + offset + 0x1C;
          if (mach_vm_write(mach_task_self(), field,
                            (vm_offset_t)&filtered,
                            (mach_msg_type_number_t)sizeof(filtered)) ==
              KERN_SUCCESS) {
            ++patched;
          }
        }

        if (cursor + bytes_read >= next_region) {
          break;
        }
        cursor += bytes_read - 0x20;
      }
    }

    if (next_region <= region) {
      break;
    }
    region = next_region;
  }

  free(chunk);
  if (!gDataScanSummaryLogged) {
    char message[256];
    snprintf(message, sizeof(message),
             "data override: first scan allowlisted=%zu invalid=%zu "
             "getter_matches=%zu tracked=%zu patched=%zu",
             allowlisted_candidates, invalid_candidates, getter_matches,
             gTrackedObjectCount, patched);
    log_line(message);
    gDataScanSummaryLogged = true;
  }
  if (patched > 0) {
    char message[160];
    snprintf(message, sizeof(message),
             "data override: patched %zu object(s)", patched);
    log_line(message);
  }
  return patched;
}

__attribute__((visibility("default")))
size_t realsteamonmac_apply_hooks(void) {
  return realsteamonmac_apply_data_overrides();
}

static bool load_registry_token(char token[REGISTRY_TOKEN_CAPACITY]) {
  const char *environment = getenv("REALSTEAMONMAC_REGISTRY_TOKEN");
  if (environment != NULL && *environment != '\0') {
    if (strlen(environment) >= REGISTRY_TOKEN_CAPACITY) {
      return false;
    }
    strcpy(token, environment);
  } else {
    const char *home = getenv("HOME");
    if (home == NULL) {
      return false;
    }
    char path[1200];
    if (snprintf(
            path, sizeof(path),
            "%s/Library/Application Support/RealSteamOnMac/registry-token",
            home) >= (int)sizeof(path)) {
      return false;
    }
    if (path_has_symlink_component(path)) {
      return false;
    }
    int descriptor = open(path, O_RDONLY | O_NOFOLLOW);
    if (descriptor < 0) {
      return false;
    }
    struct stat file_stat;
    if (
        fstat(descriptor, &file_stat) != 0 ||
        !S_ISREG(file_stat.st_mode) ||
        file_stat.st_uid != geteuid() ||
        (file_stat.st_mode & 077) != 0
    ) {
      close(descriptor);
      return false;
    }
    FILE *stream = fdopen(descriptor, "r");
    if (stream == NULL) {
      close(descriptor);
      return false;
    }
    if (fgets(token, REGISTRY_TOKEN_CAPACITY, stream) == NULL) {
      fclose(stream);
      return false;
    }
    fclose(stream);
    token[strcspn(token, "\r\n")] = '\0';
  }

  size_t length = strlen(token);
  if (length < 32 || length > 64) {
    return false;
  }
  for (size_t index = 0; index < length; ++index) {
    char character = token[index];
    bool hexadecimal =
        (character >= '0' && character <= '9') ||
        (character >= 'a' && character <= 'f') ||
        (character >= 'A' && character <= 'F');
    if (!hexadecimal) {
      return false;
    }
  }
  return true;
}

static uint16_t registry_server_port(void) {
  const char *raw = getenv("REALSTEAMONMAC_REGISTRY_PORT");
  if (raw == NULL || *raw == '\0') {
    return REGISTRY_SERVER_PORT;
  }
  char *end = NULL;
  unsigned long value = strtoul(raw, &end, 10);
  if (end == raw || *end != '\0' || value < 1024 || value > 65535) {
    return REGISTRY_SERVER_PORT;
  }
  return (uint16_t)value;
}

static bool parse_canonical_uint32(
    const char *text, size_t length, uint32_t *value_out) {
  if (
      text == NULL || value_out == NULL ||
      length == 0 || length > 10 ||
      (length > 1 && text[0] == '0')
  ) {
    return false;
  }
  uint64_t value = 0;
  for (size_t index = 0; index < length; ++index) {
    if (text[index] < '0' || text[index] > '9') {
      return false;
    }
    value = (value * 10) + (uint64_t)(text[index] - '0');
    if (value > UINT32_MAX) {
      return false;
    }
  }
  if (value == 0) {
    return false;
  }
  *value_out = (uint32_t)value;
  return true;
}

static int uppercase_hexadecimal_value(char character) {
  if (character >= '0' && character <= '9') {
    return character - '0';
  }
  if (character >= 'A' && character <= 'F') {
    return 10 + character - 'A';
  }
  return -1;
}

static bool valid_utf8_bytes(
    const unsigned char *bytes, size_t length) {
  size_t index = 0;
  while (index < length) {
    unsigned char lead = bytes[index++];
    if (lead <= 0x7f) {
      continue;
    }
    size_t continuation_count = 0;
    uint32_t value = 0;
    uint32_t minimum = 0;
    if ((lead & 0xe0) == 0xc0) {
      continuation_count = 1;
      value = lead & 0x1f;
      minimum = 0x80;
    } else if ((lead & 0xf0) == 0xe0) {
      continuation_count = 2;
      value = lead & 0x0f;
      minimum = 0x800;
    } else if ((lead & 0xf8) == 0xf0) {
      continuation_count = 3;
      value = lead & 0x07;
      minimum = 0x10000;
    } else {
      return false;
    }
    if (index + continuation_count > length) {
      return false;
    }
    for (size_t offset = 0; offset < continuation_count; ++offset) {
      unsigned char continuation = bytes[index++];
      if ((continuation & 0xc0) != 0x80) {
        return false;
      }
      value = (value << 6) | (continuation & 0x3f);
    }
    if (
        value < minimum || value > 0x10ffff ||
        (value >= 0xd800 && value <= 0xdfff)
    ) {
      return false;
    }
  }
  return true;
}

static bool decode_shortcut_candidate(
    const char *encoded,
    size_t encoded_length,
    char decoded[PATH_MAX]) {
  if (
      encoded == NULL || encoded_length == 0 ||
      encoded_length % 3 != 0 ||
      encoded_length / 3 >= PATH_MAX
  ) {
    return false;
  }
  size_t count = encoded_length / 3;
  for (size_t index = 0; index < count; ++index) {
    size_t offset = index * 3;
    int high = uppercase_hexadecimal_value(encoded[offset + 1]);
    int low = uppercase_hexadecimal_value(encoded[offset + 2]);
    if (encoded[offset] != '%' || high < 0 || low < 0) {
      return false;
    }
    unsigned char value = (unsigned char)((high << 4) | low);
    if (value == 0 || value < 0x20 || value == 0x7f) {
      return false;
    }
    decoded[index] = (char)value;
  }
  decoded[count] = '\0';
  return valid_utf8_bytes(
      (const unsigned char *)decoded, count);
}

static bool parse_registry_payload(
    const char *text,
    bool drop_invalid_shortcuts,
    managed_registry *registry_out) {
  static const char header[] = "RSMREG\t1\n";
  if (
      text == NULL || registry_out == NULL ||
      strlen(text) >= REGISTRY_REQUEST_CAPACITY ||
      strncmp(text, header, sizeof(header) - 1) != 0
  ) {
    return false;
  }
  managed_registry registry;
  memset(&registry, 0, sizeof(registry));
  const char *cursor = text + sizeof(header) - 1;
  while (*cursor != '\0') {
    const char *line_end = strchr(cursor, '\n');
    if (line_end == NULL || line_end == cursor) {
      return false;
    }
    if (
        registry.appid_count + registry.shortcut_count >=
        MAX_ALLOWLIST_APPIDS
    ) {
      return false;
    }
    if (cursor[0] == 'A' && cursor[1] == '\t') {
      uint32_t appid = 0;
      if (
          !parse_canonical_uint32(
              cursor + 2,
              (size_t)(line_end - (cursor + 2)),
              &appid) ||
          appid_in_list(
              appid, registry.appids, registry.appid_count) ||
          shortcut_in_registry(
              appid, registry.shortcuts,
              registry.shortcut_count, NULL)
      ) {
        return false;
      }
      registry.appids[registry.appid_count++] = appid;
    } else if (cursor[0] == 'S' && cursor[1] == '\t') {
      const char *identifier = cursor + 2;
      const char *separator =
          memchr(identifier, '\t', (size_t)(line_end - identifier));
      if (
          separator == NULL ||
          registry.shortcut_count >= MAX_MANAGED_SHORTCUTS
      ) {
        return false;
      }
      uint32_t shortcut_id = 0;
      managed_shortcut *shortcut =
          &registry.shortcuts[registry.shortcut_count];
      char candidate[PATH_MAX];
      if (
          !parse_canonical_uint32(
              identifier,
              (size_t)(separator - identifier),
              &shortcut_id) ||
          appid_in_list(
              shortcut_id,
              registry.appids,
              registry.appid_count) ||
          shortcut_in_registry(
              shortcut_id,
              registry.shortcuts,
              registry.shortcut_count, NULL) ||
          !decode_shortcut_candidate(
              separator + 1,
              (size_t)(line_end - (separator + 1)),
              candidate)
      ) {
        return false;
      }
      if (!validate_shortcut_target(
              candidate, shortcut->target, &shortcut->identity)) {
        if (drop_invalid_shortcuts) {
          cursor = line_end + 1;
          continue;
        }
        return false;
      }
      shortcut->id = shortcut_id;
      ++registry.shortcut_count;
    } else {
      return false;
    }
    cursor = line_end + 1;
  }
  *registry_out = registry;
  return true;
}

static bool write_managed_registry(
    int descriptor, const managed_registry *registry) {
  static const char hexadecimal[] = "0123456789ABCDEF";
  if (!write_all(descriptor, "RSMREG\t1\n", 9)) {
    return false;
  }
  for (size_t index = 0; index < registry->appid_count; ++index) {
    char line[32];
    int length = snprintf(
        line, sizeof(line), "A\t%u\n",
        (unsigned int)registry->appids[index]);
    if (
        length <= 0 || length >= (int)sizeof(line) ||
        !write_all(descriptor, line, (size_t)length)
    ) {
      return false;
    }
  }
  for (size_t index = 0; index < registry->shortcut_count; ++index) {
    const managed_shortcut *shortcut = &registry->shortcuts[index];
    char prefix[32];
    int prefix_length = snprintf(
        prefix, sizeof(prefix), "S\t%u\t",
        (unsigned int)shortcut->id);
    if (
        prefix_length <= 0 ||
        prefix_length >= (int)sizeof(prefix) ||
        !write_all(descriptor, prefix, (size_t)prefix_length)
    ) {
      return false;
    }
    for (const unsigned char *cursor =
             (const unsigned char *)shortcut->target;
         *cursor != '\0'; ++cursor) {
      char encoded[3] = {
          '%', hexadecimal[*cursor >> 4],
          hexadecimal[*cursor & 0x0f],
      };
      if (!write_all(descriptor, encoded, sizeof(encoded))) {
        return false;
      }
    }
    if (!write_all(descriptor, "\n", 1)) {
      return false;
    }
  }
  return true;
}

static bool shortcut_binding_matches(
    int directory, const managed_shortcut *shortcut) {
  char filename[64];
  if (
      snprintf(
          filename, sizeof(filename),
          "shortcut-binding-%u.txt",
          (unsigned int)shortcut->id) >= (int)sizeof(filename)
  ) {
    return false;
  }
  int descriptor = openat(
      directory, filename, O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    return false;
  }
  struct stat file_stat;
  bool valid =
      fstat(descriptor, &file_stat) == 0 &&
      S_ISREG(file_stat.st_mode) &&
      file_stat.st_uid == geteuid() &&
      (file_stat.st_mode & 077) == 0 &&
      file_stat.st_size > 0 &&
      file_stat.st_size < PATH_MAX;
  char target[PATH_MAX];
  size_t total = 0;
  while (valid && total < (size_t)file_stat.st_size) {
    ssize_t count = read(
        descriptor, target + total,
        (size_t)file_stat.st_size - total);
    if (count <= 0) {
      valid = false;
      break;
    }
    total += (size_t)count;
  }
  char extra = '\0';
  if (valid && read(descriptor, &extra, 1) != 0) {
    valid = false;
  }
  if (close(descriptor) != 0) {
    valid = false;
  }
  if (!valid) {
    return false;
  }
  target[total] = '\0';
  return strcmp(target, shortcut->target) == 0;
}

static bool prepare_shortcut_binding(
    int directory, const managed_shortcut *shortcut) {
  char filename[64];
  char temporary[96] = {0};
  if (
      snprintf(
          filename, sizeof(filename),
          "shortcut-binding-%u.txt",
          (unsigned int)shortcut->id) >= (int)sizeof(filename)
  ) {
    return false;
  }
  if (faccessat(directory, filename, F_OK, AT_SYMLINK_NOFOLLOW) == 0) {
    return shortcut_binding_matches(directory, shortcut);
  }
  if (errno != ENOENT) {
    return false;
  }

  int descriptor = -1;
  for (unsigned int attempt = 0; attempt < 32; ++attempt) {
    if (
        snprintf(
            temporary, sizeof(temporary),
            ".shortcut-binding-%u.%ld.%08x.tmp",
            (unsigned int)shortcut->id,
            (long)getpid(), arc4random()) >= (int)sizeof(temporary)
    ) {
      return false;
    }
    descriptor = openat(
        directory, temporary,
        O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW,
        0600);
    if (descriptor >= 0) {
      break;
    }
    if (errno != EEXIST) {
      return false;
    }
  }
  if (descriptor < 0) {
    return false;
  }
  bool success =
      fchmod(descriptor, 0600) == 0 &&
      write_all(
          descriptor, shortcut->target,
          strlen(shortcut->target)) &&
      fsync(descriptor) == 0 &&
      close(descriptor) == 0;
  if (!success) {
    (void)close(descriptor);
    (void)unlinkat(directory, temporary, 0);
    return false;
  }
  if (
      linkat(directory, temporary, directory, filename, 0) != 0
  ) {
    int link_error = errno;
    (void)unlinkat(directory, temporary, 0);
    if (link_error == EEXIST) {
      return shortcut_binding_matches(directory, shortcut);
    }
    return false;
  }
  success =
      unlinkat(directory, temporary, 0) == 0 &&
      fsync(directory) == 0;
  if (!success) {
    return false;
  }
  return shortcut_binding_matches(directory, shortcut);
}

static bool persist_managed_registry(
    const managed_registry *registry) {
  if (
      registry == NULL ||
      registry->appid_count > MAX_ALLOWLIST_APPIDS ||
      registry->shortcut_count > MAX_MANAGED_SHORTCUTS ||
      registry->appid_count + registry->shortcut_count >
          MAX_ALLOWLIST_APPIDS
  ) {
    return false;
  }
  const char *home = getenv("HOME");
  if (home == NULL) {
    return false;
  }
  char root[1024];
  if (
      snprintf(
          root, sizeof(root),
          "%s/Library/Application Support/RealSteamOnMac",
          home) >= (int)sizeof(root)
  ) {
    return false;
  }
  if (mkdir(root, 0700) != 0 && errno != EEXIST) {
    return false;
  }
  struct stat root_stat;
  if (
      lstat(root, &root_stat) != 0 ||
      !S_ISDIR(root_stat.st_mode) ||
      S_ISLNK(root_stat.st_mode) ||
      chmod(root, 0700) != 0
  ) {
    return false;
  }
  int directory = open(root, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (directory < 0) {
    return false;
  }
  struct stat directory_stat;
  bool success =
      fstat(directory, &directory_stat) == 0 &&
      directory_stat.st_dev == root_stat.st_dev &&
      directory_stat.st_ino == root_stat.st_ino;
  for (
      size_t index = 0;
      success && index < registry->shortcut_count;
      ++index
  ) {
    success = prepare_shortcut_binding(
        directory, &registry->shortcuts[index]);
  }
  char temporary[96] = {0};
  int descriptor = -1;
  for (unsigned int attempt = 0; success && attempt < 32; ++attempt) {
    if (
        snprintf(
            temporary, sizeof(temporary),
            ".managed-registry-v1.%ld.%08x.tmp",
            (long)getpid(), arc4random()) >= (int)sizeof(temporary)
    ) {
      success = false;
      break;
    }
    descriptor = openat(
        directory, temporary,
        O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW,
        0600);
    if (descriptor >= 0) {
      break;
    }
    if (errno != EEXIST) {
      success = false;
      break;
    }
  }
  if (descriptor < 0) {
    success = false;
  }
  if (
      success &&
      (
          fchmod(descriptor, 0600) != 0 ||
          !write_managed_registry(descriptor, registry) ||
          fsync(descriptor) != 0
      )
  ) {
    success = false;
  }
  if (descriptor >= 0 && close(descriptor) != 0) {
    success = false;
  }
  if (success) {
    success =
        renameat(
            directory, temporary,
            directory, "managed-registry-v1.txt") == 0 &&
        fsync(directory) == 0;
  }
  if (!success && temporary[0] != '\0') {
    (void)unlinkat(directory, temporary, 0);
  }
  (void)close(directory);
  return success;
}

static bool load_managed_registry_cache(
    managed_registry *registry_out) {
  char path[1200];
  if (
      registry_out == NULL ||
      !support_file_path("managed-registry-v1.txt", path)
  ) {
    return false;
  }
  int descriptor = open(path, O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    return false;
  }
  struct stat file_stat;
  bool valid =
      fstat(descriptor, &file_stat) == 0 &&
      S_ISREG(file_stat.st_mode) &&
      (file_stat.st_mode & 077) == 0 &&
      file_stat.st_size > 0 &&
      file_stat.st_size < REGISTRY_REQUEST_CAPACITY;
  char payload[REGISTRY_REQUEST_CAPACITY];
  size_t total = 0;
  while (valid && total < (size_t)file_stat.st_size) {
    ssize_t count = read(
        descriptor,
        payload + total,
        (size_t)file_stat.st_size - total);
    if (count <= 0) {
      valid = false;
      break;
    }
    total += (size_t)count;
  }
  char extra = '\0';
  if (valid && read(descriptor, &extra, 1) != 0) {
    valid = false;
  }
  if (close(descriptor) != 0) {
    valid = false;
  }
  if (!valid) {
    return false;
  }
  payload[total] = '\0';
  if (strlen(payload) != total) {
    return false;
  }
  return parse_registry_payload(payload, true, registry_out);
}

static bool publish_registry(const managed_registry *registry) {
  (void)pthread_mutex_lock(&gAllowlistLock);
  if (!persist_managed_registry(registry)) {
    (void)pthread_mutex_unlock(&gAllowlistLock);
    return false;
  }
  memcpy(
      gAllowlist,
      registry->appids,
      registry->appid_count * sizeof(*gAllowlist));
  gAllowlistCount = registry->appid_count;
  memcpy(
      gManagedShortcuts,
      registry->shortcuts,
      registry->shortcut_count * sizeof(*gManagedShortcuts));
  gManagedShortcutCount = registry->shortcut_count;
  atomic_store_explicit(
      &gAllowlistLoaded, true, memory_order_release);
  (void)pthread_mutex_unlock(&gAllowlistLock);

  (void)atomic_fetch_add_explicit(
      &gAllowlistGeneration, 1, memory_order_acq_rel);
  atomic_store_explicit(
      &gInstallGateRefreshRequested, true, memory_order_release);
  atomic_store_explicit(
      &gSteamClientInstallGatePatched, false, memory_order_release);
  char message[128];
  snprintf(
      message, sizeof(message),
      "registry: accepted %zu store app(s) and %zu shortcut(s)",
      registry->appid_count, registry->shortcut_count);
  log_line(message);
  log_line("registry: persisted typed managed registry");
  return true;
}

__attribute__((visibility("default")))
bool realsteamonmac_is_managed_app(uint32_t appid) {
  ensure_allowlist_loaded();
  return is_store_managed(appid);
}

static bool parse_content_length(
    const char *headers, size_t *length_out, bool *found_out) {
  *length_out = 0;
  *found_out = false;
  const char *cursor = headers;
  while (*cursor != '\0') {
    const char *line_end = strstr(cursor, "\r\n");
    if (line_end == NULL || line_end == cursor) {
      break;
    }
    if (
        (size_t)(line_end - cursor) >= 15 &&
        strncasecmp(cursor, "Content-Length:", 15) == 0
    ) {
      const char *value = cursor + 15;
      while (*value == ' ' || *value == '\t') {
        ++value;
      }
      errno = 0;
      char *end = NULL;
      unsigned long parsed = strtoul(value, &end, 10);
      while (end < line_end && (*end == ' ' || *end == '\t')) {
        ++end;
      }
      if (
          errno != 0 || end == value || end != line_end ||
          parsed >= REGISTRY_REQUEST_CAPACITY
      ) {
        return false;
      }
      *length_out = (size_t)parsed;
      *found_out = true;
      return true;
    }
    cursor = line_end + 2;
  }
  return true;
}

static const char *http_reason(int status) {
  switch (status) {
    case 200:
      return "OK";
    case 202:
      return "Accepted";
    case 204:
      return "No Content";
    case 400:
      return "Bad Request";
    case 403:
      return "Forbidden";
    case 404:
      return "Not Found";
    case 500:
      return "Internal Server Error";
    default:
      return "Error";
  }
}

static void send_http_response(
    int connection,
    int status,
    const char *content_type,
    const char *body) {
  size_t body_length = body != NULL ? strlen(body) : 0;
  const char *type =
      content_type != NULL ? content_type : "text/plain";
  char response[1024];
  int length = snprintf(
      response, sizeof(response),
      "HTTP/1.1 %d %s\r\n"
      "Connection: close\r\n"
      "Content-Type: %s\r\n"
      "Content-Length: %zu\r\n"
      "Cache-Control: no-store\r\n"
      "Access-Control-Allow-Origin: *\r\n"
      "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
      "Access-Control-Allow-Headers: Content-Type\r\n"
      "Access-Control-Allow-Private-Network: true\r\n\r\n",
      status, http_reason(status), type, body_length);
  if (length <= 0 || length >= (int)sizeof(response)) {
    return;
  }
  size_t sent = 0;
  while (sent < (size_t)length) {
    ssize_t result = send(
        connection, response + sent,
        (size_t)length - sent, MSG_NOSIGNAL);
    if (result < 0 && errno == EINTR) {
      continue;
    }
    if (result <= 0) {
      return;
    }
    sent += (size_t)result;
  }
  sent = 0;
  while (sent < body_length) {
    ssize_t result = send(
        connection, body + sent,
        body_length - sent, MSG_NOSIGNAL);
    if (result < 0 && errno == EINTR) {
      continue;
    }
    if (result <= 0) {
      return;
    }
    sent += (size_t)result;
  }
}

static bool parse_positive_appid(
    const char *text, uint32_t *appid_out) {
  if (text == NULL || *text == '\0') {
    return false;
  }
  errno = 0;
  char *end = NULL;
  unsigned long value = strtoul(text, &end, 10);
  if (
      errno != 0 || end == text || *end != '\0' ||
      value == 0 || value > UINT32_MAX
  ) {
    return false;
  }
  *appid_out = (uint32_t)value;
  return true;
}

static bool parse_config_target(
    const char *target,
    const char *token,
    uint32_t *appid_out) {
  char prefix[256];
  int prefix_length = snprintf(
      prefix, sizeof(prefix), "/config?token=%s&appid=", token);
  if (
      prefix_length <= 0 ||
      prefix_length >= (int)sizeof(prefix) ||
      strncmp(target, prefix, (size_t)prefix_length) != 0
  ) {
    return false;
  }
  return parse_positive_appid(target + prefix_length, appid_out);
}

static bool parse_shortcut_config_target(
    const char *target,
    const char *token,
    uint32_t *shortcut_id_out) {
  char prefix[320];
  int prefix_length = snprintf(
      prefix, sizeof(prefix),
      "/config?token=%s&kind=shortcut&id=", token);
  if (
      prefix_length <= 0 ||
      prefix_length >= (int)sizeof(prefix) ||
      strncmp(target, prefix, (size_t)prefix_length) != 0
  ) {
    return false;
  }
  return parse_positive_appid(
      target + prefix_length, shortcut_id_out);
}

static bool parse_action_target(
    const char *target,
    const char *token,
    uint32_t *appid_out) {
  char prefix[256];
  int prefix_length = snprintf(
      prefix, sizeof(prefix), "/action?token=%s&appid=", token);
  if (
      prefix_length <= 0 ||
      prefix_length >= (int)sizeof(prefix) ||
      strncmp(target, prefix, (size_t)prefix_length) != 0
  ) {
    return false;
  }
  return parse_positive_appid(target + prefix_length, appid_out);
}

static bool valid_action_job_id(const char *job_id) {
  if (
      job_id == NULL ||
      strlen(job_id) != ACTION_JOB_ID_CAPACITY - 1
  ) {
    return false;
  }
  for (size_t index = 0; job_id[index] != '\0'; ++index) {
    char character = job_id[index];
    if (
        !(
            (character >= '0' && character <= '9') ||
            (character >= 'a' && character <= 'f')
        )
    ) {
      return false;
    }
  }
  return true;
}

static bool parse_job_target(
    const char *target,
    const char *token,
    uint32_t *appid_out,
    char job_id[ACTION_JOB_ID_CAPACITY]) {
  char prefix[256];
  int prefix_length = snprintf(
      prefix, sizeof(prefix), "/job?token=%s&appid=", token);
  if (
      prefix_length <= 0 ||
      prefix_length >= (int)sizeof(prefix) ||
      strncmp(target, prefix, (size_t)prefix_length) != 0
  ) {
    return false;
  }
  const char *appid_text = target + prefix_length;
  const char *separator = strstr(appid_text, "&job=");
  if (separator == NULL || separator == appid_text) {
    return false;
  }
  size_t appid_length = (size_t)(separator - appid_text);
  if (appid_length >= 16) {
    return false;
  }
  char appid_buffer[16];
  memcpy(appid_buffer, appid_text, appid_length);
  appid_buffer[appid_length] = '\0';
  const char *raw_job_id = separator + 5;
  if (
      !parse_positive_appid(appid_buffer, appid_out) ||
      !valid_action_job_id(raw_job_id)
  ) {
    return false;
  }
  strcpy(job_id, raw_job_id);
  return true;
}

static bool action_job_root(char path[1200]) {
  const char *configured = getenv("REALSTEAMONMAC_JOB_ROOT");
  if (configured != NULL && *configured != '\0') {
    if (strlen(configured) >= 1200) {
      return false;
    }
    strcpy(path, configured);
    return true;
  }
  const char *home = getenv("HOME");
  if (home == NULL) {
    return false;
  }
  return snprintf(
             path, 1200,
             "%s/Library/Application Support/RealSteamOnMac/jobs",
             home) < 1200;
}

static bool action_job_status_path(
    uint32_t appid,
    const char *job_id,
    char path[1500]) {
  char root[1200];
  if (
      !valid_action_job_id(job_id) ||
      !action_job_root(root)
  ) {
    return false;
  }
  return snprintf(
             path, 1500, "%s/%u/%s.json",
             root, (unsigned int)appid, job_id) < 1500;
}

static bool load_action_job_status(
    uint32_t appid,
    const char *job_id,
    char output[ACTION_JOB_STATUS_CAPACITY],
    bool *found_out) {
  *found_out = false;
  char path[1500];
  if (!action_job_status_path(appid, job_id, path)) {
    return false;
  }
  int descriptor = open(path, O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    return errno == ENOENT;
  }
  struct stat file_stat;
  if (
      fstat(descriptor, &file_stat) != 0 ||
      !S_ISREG(file_stat.st_mode) ||
      file_stat.st_size <= 0 ||
      file_stat.st_size >= ACTION_JOB_STATUS_CAPACITY
  ) {
    close(descriptor);
    return false;
  }
  size_t expected = (size_t)file_stat.st_size;
  size_t total = 0;
  while (total < expected) {
    ssize_t result = read(
        descriptor, output + total, expected - total);
    if (result <= 0) {
      close(descriptor);
      return false;
    }
    total += (size_t)result;
  }
  close(descriptor);
  output[total] = '\0';
  *found_out = true;
  return true;
}

static bool generate_action_job_id(
    char job_id[ACTION_JOB_ID_CAPACITY]) {
  unsigned char bytes[ACTION_JOB_ID_BYTES];
  arc4random_buf(bytes, sizeof(bytes));
  for (size_t index = 0; index < sizeof(bytes); ++index) {
    snprintf(
        job_id + (index * 2),
        ACTION_JOB_ID_CAPACITY - (index * 2),
        "%02x", bytes[index]);
  }
  return valid_action_job_id(job_id);
}

static bool runtime_entrypoint(char path[1400]) {
  const char *runtime_root = getenv("REALSTEAMONMAC_RUNTIME_ROOT");
  if (runtime_root != NULL && *runtime_root != '\0') {
    return snprintf(
               path, 1400, "%s/bin/realsteamonmac-runtime",
               runtime_root) < 1400;
  }
  const char *home = getenv("HOME");
  if (home == NULL) {
    return false;
  }
  return snprintf(
             path, 1400,
             "%s/Library/Application Support/RealSteamOnMac/"
             "runtimes/bin/realsteamonmac-runtime",
             home) < 1400;
}

static bool spawn_action_job(
    uint32_t appid,
    const char *payload,
    char job_id[ACTION_JOB_ID_CAPACITY]) {
  if (
      payload == NULL ||
      strlen(payload) == 0 ||
      strlen(payload) >= ACTION_PAYLOAD_CAPACITY ||
      !generate_action_job_id(job_id)
  ) {
    return false;
  }
  char runtime[1400];
  if (
      !runtime_entrypoint(runtime) ||
      access(runtime, R_OK) != 0
  ) {
    log_line("action: runtime entrypoint is unavailable");
    return false;
  }
  char appid_text[16];
  snprintf(
      appid_text, sizeof(appid_text), "%u",
      (unsigned int)appid);
  char *arguments[] = {
      "/usr/bin/python3",
      "-I",
      runtime,
      "action",
      "--appid",
      appid_text,
      "--job-id",
      job_id,
      "--payload",
      (char *)payload,
      NULL,
  };
  posix_spawn_file_actions_t actions;
  if (posix_spawn_file_actions_init(&actions) != 0) {
    return false;
  }
  bool actions_ready =
      posix_spawn_file_actions_addopen(
          &actions, STDOUT_FILENO, "/dev/null",
          O_WRONLY, 0) == 0 &&
      posix_spawn_file_actions_addopen(
          &actions, STDERR_FILENO, "/dev/null",
          O_WRONLY, 0) == 0;
  pid_t child = 0;
  int result =
      actions_ready
          ? posix_spawn(
                &child,
                "/usr/bin/python3",
                &actions,
                NULL,
                arguments,
                environ)
          : EINVAL;
  (void)posix_spawn_file_actions_destroy(&actions);
  if (result != 0) {
    log_line("action: could not spawn runtime job");
    return false;
  }
  char message[192];
  snprintf(
      message, sizeof(message),
      "action: started AppID %u job %s pid %d",
      (unsigned int)appid, job_id, child);
  log_line(message);
  return true;
}

static void default_runtime_config(runtime_config *config) {
  memset(config, 0, sizeof(*config));
  strcpy(config->renderer, "dxmt");
  config->msync = true;
}

static bool parse_boolean_value(
    const char *value, bool *result_out) {
  if (strcmp(value, "1") == 0) {
    *result_out = true;
    return true;
  }
  if (strcmp(value, "0") == 0) {
    *result_out = false;
    return true;
  }
  return false;
}

static bool is_supported_renderer(const char *renderer) {
  return
      strcmp(renderer, "gptk") == 0 ||
      strcmp(renderer, "dxmt") == 0 ||
      strcmp(renderer, "dxvk") == 0 ||
      strcmp(renderer, "wined3d") == 0;
}

static bool is_supported_tool_identifier(const char *tool) {
  size_t length = strlen(tool);
  if (length == 0) {
    return true;
  }
  if (
      length < 2 || length >= RUNTIME_CONFIG_TOOL_CAPACITY ||
      !(
          (tool[0] >= 'a' && tool[0] <= 'z') ||
          (tool[0] >= '0' && tool[0] <= '9')
      )
  ) {
    return false;
  }
  for (size_t index = 1; index < length; ++index) {
    char character = tool[index];
    if (
        !(
            (character >= 'a' && character <= 'z') ||
            (character >= '0' && character <= '9') ||
            character == '.' ||
            character == '_' ||
            character == '-'
        )
    ) {
      return false;
    }
  }
  return true;
}

static bool parse_runtime_config_payload(
    const char *payload, runtime_config *config_out) {
  if (payload == NULL || strlen(payload) >= RUNTIME_CONFIG_CAPACITY) {
    return false;
  }

  char copy[RUNTIME_CONFIG_CAPACITY];
  strcpy(copy, payload);
  runtime_config config;
  default_runtime_config(&config);
  unsigned int seen = 0;
  char *state = NULL;
  for (
      char *entry = strtok_r(copy, "&", &state);
      entry != NULL;
      entry = strtok_r(NULL, "&", &state)
  ) {
    char *separator = strchr(entry, '=');
    if (separator == NULL || separator == entry) {
      return false;
    }
    *separator = '\0';
    const char *key = entry;
    const char *value = separator + 1;
    unsigned int bit = 0;
    bool *boolean_target = NULL;
    if (strcmp(key, "compat_tool") == 0) {
      bit = 1u << 0;
      if (!is_supported_tool_identifier(value)) {
        return false;
      }
      strcpy(config.compat_tool, value);
    } else if (strcmp(key, "renderer") == 0) {
      bit = 1u << 1;
      if (
          !is_supported_renderer(value) ||
          strlen(value) >= sizeof(config.renderer)
      ) {
        return false;
      }
      strcpy(config.renderer, value);
    } else if (strcmp(key, "msync") == 0) {
      bit = 1u << 2;
      boolean_target = &config.msync;
    } else if (strcmp(key, "retina") == 0) {
      bit = 1u << 3;
      boolean_target = &config.retina;
    } else if (strcmp(key, "metal_hud") == 0) {
      bit = 1u << 4;
      boolean_target = &config.metal_hud;
    } else if (strcmp(key, "metalfx") == 0) {
      bit = 1u << 5;
      boolean_target = &config.metalfx;
    } else if (strcmp(key, "dxr") == 0) {
      bit = 1u << 6;
      boolean_target = &config.dxr;
    } else if (strcmp(key, "avx") == 0) {
      bit = 1u << 7;
      boolean_target = &config.avx;
    } else {
      return false;
    }
    if ((seen & bit) != 0) {
      return false;
    }
    seen |= bit;
    if (
        boolean_target != NULL &&
        !parse_boolean_value(value, boolean_target)
    ) {
      return false;
    }
  }

  if (
      seen != ((1u << 8) - 1)
  ) {
    return false;
  }
  *config_out = config;
  return true;
}

static bool runtime_config_root(char path[1200]) {
  const char *configured = getenv("REALSTEAMONMAC_APP_CONFIG_ROOT");
  if (configured != NULL && *configured != '\0') {
    if (strlen(configured) >= 1200) {
      return false;
    }
    strcpy(path, configured);
    return true;
  }
  const char *home = getenv("HOME");
  if (home == NULL) {
    return false;
  }
  return snprintf(
             path, 1200,
             "%s/Library/Application Support/RealSteamOnMac/apps",
             home) < 1200;
}

static bool runtime_config_path(
    uint32_t appid,
    bool shortcut,
    char path[1400]) {
  char root[1200];
  if (!runtime_config_root(root)) {
    return false;
  }
  return shortcut
             ? snprintf(
                   path, 1400, "%s/shortcut-%u.json",
                   root, (unsigned int)appid) < 1400
             : snprintf(
                   path, 1400, "%s/%u.json",
                   root, (unsigned int)appid) < 1400;
}

static bool format_runtime_config(
    const runtime_config *config,
    char output[RUNTIME_CONFIG_CAPACITY]) {
  int length = snprintf(
      output, RUNTIME_CONFIG_CAPACITY,
      "{\n"
      "  \"avx\": %s,\n"
      "  \"compat_tool\": \"%s\",\n"
      "  \"dxr\": %s,\n"
      "  \"metal_hud\": %s,\n"
      "  \"metalfx\": %s,\n"
      "  \"msync\": %s,\n"
      "  \"renderer\": \"%s\",\n"
      "  \"retina\": %s\n"
      "}\n",
      config->avx ? "true" : "false",
      config->compat_tool,
      config->dxr ? "true" : "false",
      config->metal_hud ? "true" : "false",
      config->metalfx ? "true" : "false",
      config->msync ? "true" : "false",
      config->renderer,
      config->retina ? "true" : "false");
  return length > 0 && length < RUNTIME_CONFIG_CAPACITY;
}

static bool write_all(int descriptor, const char *bytes, size_t length) {
  size_t written = 0;
  while (written < length) {
    ssize_t result = write(
        descriptor, bytes + written, length - written);
    if (result <= 0) {
      return false;
    }
    written += (size_t)result;
  }
  return true;
}

static bool save_runtime_config(
    uint32_t appid,
    bool shortcut,
    const runtime_config *config) {
  char root[1200];
  char path[1400];
  char temporary[1450];
  char output[RUNTIME_CONFIG_CAPACITY];
  if (
      !runtime_config_root(root) ||
      (mkdir(root, 0700) != 0 && errno != EEXIST) ||
      !runtime_config_path(appid, shortcut, path) ||
      snprintf(
          temporary, sizeof(temporary),
          shortcut
              ? "%s/.shortcut-%u.json.XXXXXX"
              : "%s/.%u.json.XXXXXX",
          root, (unsigned int)appid) >= (int)sizeof(temporary) ||
      !format_runtime_config(config, output)
  ) {
    return false;
  }
  struct stat root_stat;
  if (
      lstat(root, &root_stat) != 0 ||
      !S_ISDIR(root_stat.st_mode) ||
      S_ISLNK(root_stat.st_mode) ||
      chmod(root, 0700) != 0
  ) {
    return false;
  }

  int descriptor = mkstemp(temporary);
  if (descriptor < 0) {
    return false;
  }
  bool success =
      fchmod(descriptor, 0600) == 0 &&
      write_all(descriptor, output, strlen(output)) &&
      fsync(descriptor) == 0 &&
      close(descriptor) == 0 &&
      rename(temporary, path) == 0;
  if (!success) {
    (void)close(descriptor);
    (void)unlink(temporary);
  }
  return success;
}

static bool load_runtime_config_json(
    uint32_t appid,
    bool shortcut,
    char output[RUNTIME_CONFIG_CAPACITY]) {
  char path[1400];
  if (!runtime_config_path(appid, shortcut, path)) {
    return false;
  }
  int descriptor = open(path, O_RDONLY | O_NOFOLLOW);
  if (descriptor < 0) {
    if (errno != ENOENT) {
      return false;
    }
    runtime_config config;
    default_runtime_config(&config);
    return format_runtime_config(&config, output);
  }
  struct stat file_stat;
  if (
      fstat(descriptor, &file_stat) != 0 ||
      !S_ISREG(file_stat.st_mode)
  ) {
    close(descriptor);
    return false;
  }
  FILE *stream = fdopen(descriptor, "r");
  if (stream == NULL) {
    close(descriptor);
    return false;
  }
  size_t count = fread(
      output, 1, RUNTIME_CONFIG_CAPACITY - 1, stream);
  bool success =
      !ferror(stream) &&
      count > 0 &&
      (count < RUNTIME_CONFIG_CAPACITY - 1 || feof(stream));
  fclose(stream);
  if (!success) {
    return false;
  }
  output[count] = '\0';
  return true;
}

static bool parse_request_line(
    const char *request,
    char method[8],
    char target[512]) {
  char version[16];
  return
      sscanf(request, "%7s %511s %15s", method, target, version) == 3 &&
      strcmp(version, "HTTP/1.1") == 0;
}

static void handle_registry_connection(
    int connection, const char *token) {
  struct timeval timeout = {.tv_sec = 2, .tv_usec = 0};
  (void)setsockopt(
      connection, SOL_SOCKET, SO_RCVTIMEO,
      &timeout, sizeof(timeout));

  char request[REGISTRY_REQUEST_CAPACITY];
  size_t total = 0;
  size_t header_length = 0;
  size_t content_length = 0;
  bool headers_parsed = false;
  while (total + 1 < sizeof(request)) {
    ssize_t received = recv(
        connection, request + total,
        sizeof(request) - total - 1, 0);
    if (received <= 0) {
      break;
    }
    total += (size_t)received;
    request[total] = '\0';
    if (!headers_parsed) {
      char *header_end = strstr(request, "\r\n\r\n");
      if (header_end != NULL) {
        header_length = (size_t)(header_end - request) + 4;
        bool content_length_found = false;
        if (!parse_content_length(
                request, &content_length,
                &content_length_found)) {
          send_http_response(
              connection, 400, "text/plain", NULL);
          return;
        }
        if (
            !content_length_found &&
            strncmp(request, "GET ", 4) != 0 &&
            strncmp(request, "OPTIONS ", 8) != 0
        ) {
          send_http_response(
              connection, 400, "text/plain", NULL);
          return;
        }
        headers_parsed = true;
      }
    }
    if (
        headers_parsed &&
        total >= header_length + content_length
    ) {
      break;
    }
  }
  if (
      !headers_parsed ||
      total < header_length + content_length
  ) {
    send_http_response(connection, 400, "text/plain", NULL);
    return;
  }

  char method[8];
  char target[512];
  if (!parse_request_line(request, method, target)) {
    send_http_response(connection, 400, "text/plain", NULL);
    return;
  }

  char registry_target[256];
  if (snprintf(
          registry_target, sizeof(registry_target),
          "/registry?token=%s", token) >=
      (int)sizeof(registry_target)) {
    send_http_response(connection, 403, "text/plain", NULL);
    return;
  }

  char payload[REGISTRY_REQUEST_CAPACITY];
  memcpy(payload, request + header_length, content_length);
  payload[content_length] = '\0';
  if (strcmp(target, registry_target) == 0) {
    if (strcmp(method, "OPTIONS") == 0) {
      send_http_response(connection, 204, "text/plain", NULL);
      return;
    }
    if (strcmp(method, "POST") != 0 || content_length == 0) {
      send_http_response(connection, 403, "text/plain", NULL);
      return;
    }
    managed_registry registry;
    if (
        strlen(payload) != content_length ||
        !parse_registry_payload(payload, false, &registry)
    ) {
      send_http_response(connection, 400, "text/plain", NULL);
      return;
    }
    if (!publish_registry(&registry)) {
      send_http_response(connection, 500, "text/plain", NULL);
      return;
    }
    send_http_response(connection, 204, "text/plain", NULL);
    return;
  }

  uint32_t action_appid = 0;
  if (parse_action_target(target, token, &action_appid)) {
    if (!is_store_managed(action_appid)) {
      send_http_response(connection, 403, "text/plain", NULL);
      return;
    }
    if (strcmp(method, "OPTIONS") == 0) {
      send_http_response(connection, 204, "text/plain", NULL);
      return;
    }
    if (
        strcmp(method, "POST") != 0 ||
        content_length == 0 ||
        content_length >= ACTION_PAYLOAD_CAPACITY ||
        strlen(payload) != content_length
    ) {
      send_http_response(connection, 400, "text/plain", NULL);
      return;
    }
    char job_id[ACTION_JOB_ID_CAPACITY];
    if (!spawn_action_job(action_appid, payload, job_id)) {
      send_http_response(connection, 500, "text/plain", NULL);
      return;
    }
    char response[128];
    int response_length = snprintf(
        response, sizeof(response),
        "{\"job_id\":\"%s\"}\n", job_id);
    if (
        response_length <= 0 ||
        response_length >= (int)sizeof(response)
    ) {
      send_http_response(connection, 500, "text/plain", NULL);
      return;
    }
    send_http_response(
        connection, 202, "application/json", response);
    return;
  }

  uint32_t job_appid = 0;
  char job_id[ACTION_JOB_ID_CAPACITY];
  if (parse_job_target(
          target, token, &job_appid, job_id)) {
    if (!is_store_managed(job_appid)) {
      send_http_response(connection, 403, "text/plain", NULL);
      return;
    }
    if (strcmp(method, "OPTIONS") == 0) {
      send_http_response(connection, 204, "text/plain", NULL);
      return;
    }
    if (strcmp(method, "GET") != 0 || content_length != 0) {
      send_http_response(connection, 400, "text/plain", NULL);
      return;
    }
    char status[ACTION_JOB_STATUS_CAPACITY];
    bool found = false;
    if (!load_action_job_status(
            job_appid, job_id, status, &found)) {
      send_http_response(connection, 500, "text/plain", NULL);
      return;
    }
    if (!found) {
      send_http_response(connection, 404, "text/plain", NULL);
      return;
    }
    send_http_response(
        connection, 200, "application/json", status);
    return;
  }

  uint32_t appid = 0;
  bool shortcut_config = false;
  if (
      parse_config_target(target, token, &appid) &&
      is_store_managed(appid)
  ) {
    shortcut_config = false;
  } else if (
      parse_shortcut_config_target(target, token, &appid) &&
      is_managed_shortcut(appid)
  ) {
    shortcut_config = true;
  } else {
    send_http_response(connection, 403, "text/plain", NULL);
    return;
  }
  if (strcmp(method, "OPTIONS") == 0) {
    send_http_response(connection, 204, "text/plain", NULL);
    return;
  }
  if (strcmp(method, "GET") == 0) {
    if (content_length != 0) {
      send_http_response(connection, 400, "text/plain", NULL);
      return;
    }
    char json[RUNTIME_CONFIG_CAPACITY];
    if (!load_runtime_config_json(
            appid, shortcut_config, json)) {
      send_http_response(connection, 500, "text/plain", NULL);
      return;
    }
    send_http_response(connection, 200, "application/json", json);
    return;
  }
  if (strcmp(method, "POST") == 0) {
    runtime_config config;
    if (!parse_runtime_config_payload(payload, &config)) {
      send_http_response(connection, 400, "text/plain", NULL);
      return;
    }
    if (!save_runtime_config(
            appid, shortcut_config, &config)) {
      send_http_response(connection, 500, "text/plain", NULL);
      return;
    }
    send_http_response(connection, 204, "text/plain", NULL);
    return;
  }
  send_http_response(connection, 403, "text/plain", NULL);
}

static void *registry_server_worker(void *context) {
  (void)context;
  char token[REGISTRY_TOKEN_CAPACITY];
  if (!load_registry_token(token)) {
    log_line("registry: token is missing or invalid");
    goto stopped;
  }

  int server = socket(AF_INET, SOCK_STREAM, 0);
  if (server < 0) {
    log_line("registry: could not create loopback socket");
    goto stopped;
  }
  int enabled = 1;
  (void)setsockopt(
      server, SOL_SOCKET, SO_REUSEADDR, &enabled, sizeof(enabled));
  struct sockaddr_in address;
  memset(&address, 0, sizeof(address));
  address.sin_family = AF_INET;
  address.sin_port = htons(registry_server_port());
  address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  if (
      bind(server, (const struct sockaddr *)&address, sizeof(address)) != 0 ||
      listen(server, 8) != 0
  ) {
    close(server);
    log_line("registry: could not bind loopback endpoint");
    goto stopped;
  }
  char ready_message[128];
  snprintf(
      ready_message, sizeof(ready_message),
      "registry: loopback endpoint ready on 127.0.0.1:%u",
      (unsigned int)registry_server_port());
  log_line(ready_message);

  for (;;) {
    int connection = accept(server, NULL, NULL);
    if (connection < 0) {
      if (errno == EINTR) {
        continue;
      }
      break;
    }
    handle_registry_connection(connection, token);
    close(connection);
  }
  close(server);
  log_line("registry: loopback endpoint stopped");

stopped:
  (void)pthread_mutex_lock(&gRegistryServerLock);
  gRegistryServerStarted = false;
  (void)pthread_mutex_unlock(&gRegistryServerLock);
  return NULL;
}

__attribute__((visibility("default")))
void realsteamonmac_start_registry_server(void) {
  (void)pthread_mutex_lock(&gRegistryServerLock);
  if (gRegistryServerStarted) {
    (void)pthread_mutex_unlock(&gRegistryServerLock);
    return;
  }
  gRegistryServerStarted = true;
  (void)pthread_mutex_unlock(&gRegistryServerLock);

  pthread_t server;
  if (pthread_create(
          &server, NULL, registry_server_worker, NULL) != 0) {
    (void)pthread_mutex_lock(&gRegistryServerLock);
    gRegistryServerStarted = false;
    (void)pthread_mutex_unlock(&gRegistryServerLock);
    log_line("registry: could not start loopback worker");
    return;
  }
  (void)pthread_detach(server);
}

static void *data_override_worker(void *context) {
  (void)context;
  unsigned int missing_image_checks = 0;
  unsigned int ticks_since_full_scan = EMPTY_RESCAN_INTERVAL_TICKS;
  bool environment_cleared = false;
  while (is_steam_runtime_process()) {
    // Redirect the steamclient GetAppForInstallation platform gate as soon as
    // the dylib is mapped. This is the install-time counterpart to the data
    // overrides below: the data layer makes the Install button appear, while
    // this text patch lets the click reach the real download path instead of
    // failing with error 29 ("Invalid platform"). One-shot; the guard makes
    // every later tick a no-op.
    if (!atomic_load_explicit(
            &gSteamClientInstallGatePatched, memory_order_acquire)) {
      const struct mach_header *steamclient =
          find_steamclient_image(NULL);
      if (steamclient != NULL) {
        patch_steamclient_install_gate(steamclient, 0);
      }
    }
    if (!gSteamClientSpawnPatched) {
      const struct mach_header *steamclient =
          find_steamclient_image(NULL);
      if (steamclient != NULL) {
        patch_steamclient_spawn_redirect(steamclient);
      }
    }
    const struct mach_header *steamui = find_steamui_image(NULL);
    if (steamui != NULL) {
      tracked_refresh_result refresh = refresh_tracked_objects();
      if (refresh.patched > 0) {
        char message[160];
        snprintf(message, sizeof(message),
                 "data override: refreshed %zu tracked object(s)",
                 refresh.patched);
        log_line(message);
      }

      unsigned int interval =
          gTrackedObjectCount == 0
              ? EMPTY_RESCAN_INTERVAL_TICKS
              : FULL_RESCAN_INTERVAL_TICKS;
      if (ticks_since_full_scan >= interval) {
        (void)realsteamonmac_apply_data_overrides();
        ticks_since_full_scan = 0;
        if (!environment_cleared) {
          clear_injection_environment();
          environment_cleared = true;
          log_line("data override: initial reconciliation completed");
        }
      } else {
        ++ticks_since_full_scan;
      }
    } else if (++missing_image_checks == 5) {
      log_steamui_image_diagnostic();
    }
    usleep(TRACKED_OBJECT_REFRESH_DELAY_US);
  }
  clear_injection_environment();
  log_line("data override: reconciliation worker stopped");
  return NULL;
}

__attribute__((visibility("default")))
void realsteamonmac_start_native_worker(void) {
  realsteamonmac_start_registry_server();
  if (gWorkerStarted || !is_steam_runtime_process()) {
    return;
  }

  gWorkerStarted = true;
  pthread_t worker;
  if (pthread_create(&worker, NULL, data_override_worker, NULL) != 0) {
    gWorkerStarted = false;
    log_line("data override: could not start reconciliation worker");
    return;
  }
  (void)pthread_detach(worker);
  log_line("data override: reconciliation worker started");
}
