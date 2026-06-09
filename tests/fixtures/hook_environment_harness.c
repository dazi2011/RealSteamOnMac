#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: %s HOOK_DYLIB\n", argv[0]);
    return 2;
  }

  if (setenv("DYLD_INSERT_LIBRARIES", "inherited-hook", 1) != 0 ||
      setenv("REALSTEAMONMAC_FORCE_COMPAT", "1", 1) != 0 ||
      setenv("STEAM_EXTRA_COMPAT_TOOLS_PATHS", "compat-tools", 1) != 0) {
    perror("setenv");
    return 2;
  }

  void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (handle == NULL) {
    fprintf(stderr, "dlopen failed: %s\n", dlerror());
    return 2;
  }

  usleep(100000);
  if (getenv("DYLD_INSERT_LIBRARIES") != NULL) {
    fputs("DYLD_INSERT_LIBRARIES remained set\n", stderr);
    return 1;
  }
  if (getenv("REALSTEAMONMAC_FORCE_COMPAT") != NULL) {
    fputs("REALSTEAMONMAC_FORCE_COMPAT remained set\n", stderr);
    return 1;
  }

  const char *tools = getenv("STEAM_EXTRA_COMPAT_TOOLS_PATHS");
  if (tools == NULL || strcmp(tools, "compat-tools") != 0) {
    fputs("compatibility tools path was not preserved\n", stderr);
    return 1;
  }

  (void)handle;
  return 0;
}
