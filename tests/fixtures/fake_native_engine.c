#include <stdio.h>
#include <stdlib.h>

__attribute__((visibility("default")))
void realsteamonmac_start_native_worker(void) {
  const char *marker = getenv("REALSTEAMONMAC_ACTIVATION_MARKER");
  if (marker == NULL) {
    return;
  }
  FILE *stream = fopen(marker, "w");
  if (stream == NULL) {
    return;
  }
  fputs("activated\n", stream);
  fclose(stream);
}
