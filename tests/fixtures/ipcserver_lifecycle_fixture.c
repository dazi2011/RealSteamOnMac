#include <signal.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t gTerminate = 0;

static void handle_signal(int signal_number) {
  (void)signal_number;
  gTerminate = 1;
}

int main(int argc, char **argv) {
  bool stale = argc > 1 && strcmp(argv[1], "stale") == 0;
  if (!stale) {
    sleep(30);
    return 0;
  }

  signal(SIGTERM, handle_signal);
  while (!gTerminate) {
    pause();
  }
  usleep(500000);
  return 0;
}
