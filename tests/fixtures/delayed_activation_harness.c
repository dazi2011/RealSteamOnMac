#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s HOOK ENGINE MARKER\n", argv[0]);
    return 2;
  }
  if (setenv("DYLD_INSERT_LIBRARIES", argv[1], 1) != 0 ||
      setenv("REALSTEAMONMAC_FORCE_COMPAT", "1", 1) != 0 ||
      setenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH", argv[2], 1) != 0 ||
      setenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS", "25", 1) != 0 ||
      setenv("REALSTEAMONMAC_ACTIVATION_MARKER", argv[3], 1) != 0) {
    perror("setenv");
    return 2;
  }

  void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (handle == NULL) {
    fprintf(stderr, "dlopen failed: %s\n", dlerror());
    return 2;
  }
  if (getenv("DYLD_INSERT_LIBRARIES") != NULL ||
      getenv("REALSTEAMONMAC_FORCE_COMPAT") != NULL ||
      getenv("REALSTEAMONMAC_DELAYED_ENGINE_PATH") != NULL ||
      getenv("REALSTEAMONMAC_ACTIVATION_DELAY_MS") != NULL) {
    fputs("guard did not clear inherited activation environment\n", stderr);
    return 1;
  }

  for (int attempt = 0; attempt < 200; ++attempt) {
    if (access(argv[3], F_OK) == 0) {
      (void)handle;
      return 0;
    }
    usleep(10000);
  }
  fputs("delayed engine activation did not fire\n", stderr);
  return 1;
}
