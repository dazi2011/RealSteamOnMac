#include <stdlib.h>

__attribute__((constructor)) static void initialize_injection_guard(void) {
  unsetenv("DYLD_INSERT_LIBRARIES");
  unsetenv("REALSTEAMONMAC_FORCE_COMPAT");
}
