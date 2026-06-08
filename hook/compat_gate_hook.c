#include <libkern/OSCacheControl.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#define STEAMCLIENT_COMPAT_GATE_OFFSET ((uintptr_t)0x00A012D0)
#define STEAMUI_PLATFORM_FLAGS_GETTER_OFFSET ((uintptr_t)0x005EAC3C)
#define PLATFORM_INVALID_BIT ((uint32_t)0x10)
#define MAX_ALLOWLIST_APPIDS ((size_t)256)
#define DATA_OVERRIDE_ATTEMPTS 30
#define DATA_OVERRIDE_DELAY_US 1000000

static const uint8_t kSteamClientUUID[16] = {
    0xB2, 0x95, 0x06, 0x28, 0x80, 0x3A, 0x3E, 0xFD,
    0x99, 0xEF, 0x3A, 0xD6, 0xB7, 0xB6, 0x5D, 0x1C,
};
static const uint8_t kSteamUIUUID[16] = {
    0xBF, 0x95, 0x20, 0x3F, 0x38, 0x5E, 0x3A, 0xF0,
    0x82, 0xB6, 0xAC, 0x50, 0x9A, 0xE1, 0x22, 0x4D,
};
static const uint32_t kSteamClientExpected[2] = {
    0xD101C3FF,
    0xA9054FF4,
};
static const uint32_t kSteamClientForcedTrue[2] = {
    0x52800020,  // mov w0, #1
    0xD65F03C0,  // ret
};
static const uint32_t kSteamUIExpected[2] = {
    0xB9401C00,  // ldr w0, [x0, #0x1c]
    0xD65F03C0,  // ret
};

static uint32_t gAllowlist[MAX_ALLOWLIST_APPIDS];
static size_t gAllowlistCount = 0;
static bool gRegistered = false;
static bool gSteamClientPatched = false;
static bool gSteamUIPatched = false;

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

static bool is_steam_bootstrap_process(void) {
  char *path = NULL;
  if (!get_executable_path(&path)) {
    return false;
  }
  bool matches =
      strstr(path, "/Applications/Steam.app/Contents/MacOS/steam_osx") != NULL;
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

static bool is_allowlisted(uint32_t appid) {
  for (size_t index = 0; index < gAllowlistCount; ++index) {
    if (gAllowlist[index] == appid) {
      return true;
    }
  }
  return false;
}

static void add_allowlist_appid(uint32_t appid) {
  if (appid == 0 || is_allowlisted(appid) ||
      gAllowlistCount >= MAX_ALLOWLIST_APPIDS) {
    return;
  }
  gAllowlist[gAllowlistCount++] = appid;
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

static void load_allowlist(void) {
  gAllowlistCount = 0;

  const char *environment = getenv("REALSTEAMONMAC_APPIDS");
  if (environment != NULL && *environment != '\0') {
    char *copy = strdup(environment);
    if (copy != NULL) {
      parse_allowlist_text(copy);
      free(copy);
    }
  }

  const char *home = getenv("HOME");
  if (home != NULL) {
    char path[1200];
    if (snprintf(path, sizeof(path),
                 "%s/Library/Application Support/RealSteamOnMac/allowlist.txt",
                 home) < (int)sizeof(path)) {
      FILE *stream = fopen(path, "r");
      if (stream != NULL) {
        char line[256];
        while (fgets(line, sizeof(line), stream) != NULL) {
          parse_allowlist_text(line);
        }
        fclose(stream);
      }
    }
  }

  char message[128];
  snprintf(message, sizeof(message), "allowlist: loaded %zu AppID(s)",
           gAllowlistCount);
  log_line(message);
}

__attribute__((noinline, visibility("default")))
uint32_t realsteamonmac_platform_flags(void *app) {
  if (app == NULL) {
    return 0;
  }

  uint8_t *bytes = (uint8_t *)app;
  uint32_t appid = 0;
  uint32_t flags = 0;
  memcpy(&appid, bytes + 0x08, sizeof(appid));
  memcpy(&flags, bytes + 0x1C, sizeof(flags));
  if (is_allowlisted(appid)) {
    flags &= ~PLATFORM_INVALID_BIT;
    memcpy(bytes + 0x1C, &flags, sizeof(flags));
  }
  return flags;
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

  for (uintptr_t distance = 0; distance <= 0x07000000;
       distance += 0x01000000) {
    for (int direction = 0; direction < 2; ++direction) {
      uintptr_t hint = direction == 0
                           ? target_page + distance
                           : target_page - distance;
      void *memory = mmap((void *)hint, page_size,
                          PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANON, -1, 0);
      if (memory == MAP_FAILED) {
        continue;
      }

      uint32_t branch = 0;
      if (!encode_branch(target, memory, &branch)) {
        (void)munmap(memory, page_size);
        continue;
      }
      *page_size_out = page_size;
      return memory;
    }
  }
  return NULL;
}

static void *build_platform_filter_trampoline(void *target) {
  size_t page_size = 0;
  void *memory = allocate_near_page(target, &page_size);
  if (memory == NULL) {
    return NULL;
  }

  size_t required_words = 2 + (gAllowlistCount * 4) + 2 + 4;
  if (required_words > page_size / sizeof(uint32_t)) {
    (void)munmap(memory, page_size);
    return NULL;
  }

  uint32_t *instructions = (uint32_t *)memory;
  size_t branch_indices[MAX_ALLOWLIST_APPIDS];
  size_t cursor = 0;
  instructions[cursor++] = 0xB9400808;  // ldr w8, [x0, #0x08]
  instructions[cursor++] = 0xB9401C09;  // ldr w9, [x0, #0x1c]

  for (size_t index = 0; index < gAllowlistCount; ++index) {
    uint32_t appid = gAllowlist[index];
    uint32_t low = appid & 0xFFFF;
    uint32_t high = appid >> 16;
    instructions[cursor++] = 0x5280000A | (low << 5);
    instructions[cursor++] = 0x72A0000A | (high << 5);
    instructions[cursor++] = 0x6B0A011F;  // cmp w8, w10
    branch_indices[index] = cursor;
    instructions[cursor++] = 0;
  }

  instructions[cursor++] = 0x2A0903E0;  // mov w0, w9
  instructions[cursor++] = 0xD65F03C0;  // ret
  size_t clear_index = cursor;
  instructions[cursor++] = 0x121B7929;  // and w9, w9, #0xffffffef
  instructions[cursor++] = 0xB9001C09;  // str w9, [x0, #0x1c]
  instructions[cursor++] = 0x2A0903E0;  // mov w0, w9
  instructions[cursor++] = 0xD65F03C0;  // ret

  for (size_t index = 0; index < gAllowlistCount; ++index) {
    intptr_t delta =
        (intptr_t)clear_index - (intptr_t)branch_indices[index];
    if (delta < -(1 << 18) || delta >= (1 << 18)) {
      (void)munmap(memory, page_size);
      return NULL;
    }
    uint32_t immediate = (uint32_t)delta & 0x7FFFF;
    instructions[branch_indices[index]] =
        0x54000000 | (immediate << 5);  // b.eq clear
  }

  size_t code_size = cursor * sizeof(uint32_t);
  sys_icache_invalidate(memory, code_size);
  if (mprotect(memory, page_size, PROT_READ | PROT_EXEC) != 0) {
    (void)munmap(memory, page_size);
    return NULL;
  }
  return memory;
}

static void patch_steamclient(const struct mach_header *header,
                              intptr_t slide) {
  if (gSteamClientPatched ||
      !image_uuid_matches(header, kSteamClientUUID)) {
    return;
  }

  uint8_t *target =
      (uint8_t *)((uintptr_t)header + STEAMCLIENT_COMPAT_GATE_OFFSET);
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
           "steamclient: patched slide=%p target=%p",
           (void *)slide, (void *)target);
  log_line(message);
}

static void patch_steamui(const struct mach_header *header,
                          intptr_t slide) {
  if (gSteamUIPatched || !image_uuid_matches(header, kSteamUIUUID)) {
    return;
  }

  uint8_t *target =
      (uint8_t *)((uintptr_t)header + STEAMUI_PLATFORM_FLAGS_GETTER_OFFSET);
  uint32_t current[2];
  memcpy(current, target, sizeof(current));
  if (memcmp(current, kSteamUIExpected, sizeof(current)) != 0) {
    log_line("steamui: refused unexpected platform getter bytes");
    return;
  }

  void *branch_target = build_platform_filter_trampoline(target);
  if (branch_target == NULL) {
    log_line("steamui: could not build a reachable platform filter");
    return;
  }

  uint32_t branch = 0;
  if (!encode_branch(target, branch_target, &branch)) {
    log_line("steamui: generated platform filter is not reachable");
    return;
  }

  uintptr_t page = 0;
  size_t protected_size = 0;
  if (!make_text_writable(target, sizeof(branch),
                          &page, &protected_size)) {
    log_line("steamui: could not make platform getter writable");
    return;
  }
  memcpy(target, &branch, sizeof(branch));
  sys_icache_invalidate(target, sizeof(branch));
  restore_text_protection(page, protected_size);
  gSteamUIPatched = true;

  char message[224];
  snprintf(message, sizeof(message),
           "steamui: patched slide=%p target=%p branch_target=%p",
           (void *)slide, (void *)target, branch_target);
  log_line(message);
}

static void image_added(const struct mach_header *header, intptr_t slide) {
  patch_steamclient(header, slide);
  patch_steamui(header, slide);
}

__attribute__((visibility("default")))
void realsteamonmac_apply_text_hooks(void) {
  load_allowlist();
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

__attribute__((visibility("default")))
size_t realsteamonmac_apply_data_overrides(void) {
  load_allowlist();
  const struct mach_header *steamui = find_image_by_uuid(kSteamUIUUID);
  if (steamui == NULL) {
    log_line("data override: matching steamui image was not found");
    return 0;
  }

  mach_vm_address_t getter =
      (mach_vm_address_t)((uintptr_t)steamui +
                          STEAMUI_PLATFORM_FLAGS_GETTER_OFFSET);
  const size_t chunk_capacity = 1024 * 1024;
  uint8_t *chunk = malloc(chunk_capacity);
  if (chunk == NULL) {
    log_line("data override: could not allocate scan buffer");
    return 0;
  }

  size_t patched = 0;
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
          if (!is_allowlisted(appid) ||
              (flags & PLATFORM_INVALID_BIT) == 0 ||
              vtable == 0) {
            continue;
          }

          uintptr_t method = 0;
          if (!read_process_memory(
                  (mach_vm_address_t)(vtable + 0x68),
                  &method, sizeof(method)) ||
              method != getter) {
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
  char message[160];
  snprintf(message, sizeof(message),
           "data override: patched %zu object(s)", patched);
  log_line(message);
  return patched;
}

__attribute__((visibility("default")))
size_t realsteamonmac_apply_hooks(void) {
  return realsteamonmac_apply_data_overrides();
}

static void *data_override_worker(void *context) {
  (void)context;
  for (unsigned int attempt = 0; attempt < DATA_OVERRIDE_ATTEMPTS; ++attempt) {
    if (find_image_by_uuid(kSteamUIUUID) != NULL &&
        realsteamonmac_apply_data_overrides() > 0) {
      clear_injection_environment();
      log_line("data override: startup worker completed");
      return NULL;
    }
    usleep(DATA_OVERRIDE_DELAY_US);
  }
  clear_injection_environment();
  log_line("data override: startup worker timed out");
  return NULL;
}

__attribute__((constructor)) static void initialize_platform_hook(void) {
  const char *enabled = getenv("REALSTEAMONMAC_FORCE_COMPAT");
  bool should_enable = enabled != NULL && strcmp(enabled, "1") == 0;
  if (!should_enable) {
    return;
  }
  if (is_steam_bootstrap_process()) {
    log_line("data override: waiting for Steam runtime exec");
    return;
  }
  if (!is_steam_runtime_process()) {
    clear_injection_environment();
    return;
  }

  pthread_t worker;
  if (pthread_create(&worker, NULL, data_override_worker, NULL) != 0) {
    clear_injection_environment();
    log_line("data override: could not start startup worker");
    return;
  }
  (void)pthread_detach(worker);
  log_line("data override: startup worker started");
}
