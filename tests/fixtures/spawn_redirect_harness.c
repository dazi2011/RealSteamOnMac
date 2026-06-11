#include <dlfcn.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef int (*decision_function)(const char *, char *const []);

static void fail(const char *message) {
  fprintf(stderr, "%s\n", message);
  exit(1);
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fail("usage: spawn_redirect_harness ENGINE");
  }

  char template[] = "/tmp/realsteamonmac-spawn.XXXXXX";
  int descriptor = mkstemp(template);
  if (descriptor < 0) {
    fail("could not create PE fixture");
  }
  if (write(descriptor, "MZfixture", 9) != 9) {
    close(descriptor);
    unlink(template);
    fail("could not write PE fixture");
  }
  close(descriptor);

  char executable[1024];
  if (snprintf(executable, sizeof(executable), "%s.exe", template) >=
      (int)sizeof(executable)) {
    unlink(template);
    fail("fixture path is too long");
  }
  if (rename(template, executable) != 0) {
    unlink(template);
    fail("could not rename PE fixture");
  }

  char non_pe[1024];
  if (snprintf(non_pe, sizeof(non_pe), "%s-non-pe.exe", executable) >=
      (int)sizeof(non_pe)) {
    unlink(executable);
    fail("non-PE fixture path is too long");
  }
  FILE *non_pe_stream = fopen(non_pe, "wb");
  bool non_pe_written = false;
  if (non_pe_stream != NULL) {
    non_pe_written =
        fwrite("plain", 5, 1, non_pe_stream) == 1;
    if (fclose(non_pe_stream) != 0) {
      non_pe_written = false;
    }
    non_pe_stream = NULL;
  }
  if (!non_pe_written) {
    if (non_pe_stream != NULL) {
      fclose(non_pe_stream);
    }
    unlink(executable);
    unlink(non_pe);
    fail("could not write non-PE fixture");
  }

  void *engine = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (engine == NULL) {
    unlink(executable);
    unlink(non_pe);
    fail(dlerror());
  }
  decision_function should_redirect =
      (decision_function)dlsym(
          engine, "realsteamonmac_should_redirect_spawn");
  if (should_redirect == NULL) {
    unlink(executable);
    unlink(non_pe);
    fail("spawn decision export was not found");
  }

  setenv("REALSTEAMONMAC_APPIDS", "1118200", 1);
  char managed[] = "SteamAppId=1118200";
  char unmanaged[] = "SteamAppId=4000";
  char *managed_environment[] = {managed, NULL};
  char *unmanaged_environment[] = {unmanaged, NULL};

  if (should_redirect(executable, managed_environment) != 1) {
    unlink(executable);
    unlink(non_pe);
    fail("managed PE target was not redirected");
  }
  if (should_redirect(
          "/tmp/realsteamonmac-missing-target.exe",
          managed_environment) != 1) {
    unlink(executable);
    unlink(non_pe);
    fail("managed missing EXE target was not redirected");
  }
  if (should_redirect(
          "/tmp/realsteamonmac-wrong-platform.app",
          managed_environment) != 1) {
    unlink(executable);
    unlink(non_pe);
    fail("managed macOS app target was not redirected");
  }
  if (should_redirect(executable, unmanaged_environment) != 0) {
    unlink(executable);
    unlink(non_pe);
    fail("unmanaged PE target was redirected");
  }
  if (should_redirect(
          "/tmp/realsteamonmac-unmanaged-missing.exe",
          unmanaged_environment) != 0) {
    unlink(executable);
    unlink(non_pe);
    fail("unmanaged missing target was redirected");
  }
  if (should_redirect(non_pe, managed_environment) != 0) {
    unlink(executable);
    unlink(non_pe);
    fail("existing non-PE target was redirected");
  }
  if (should_redirect("/bin/echo", managed_environment) != 0) {
    unlink(executable);
    unlink(non_pe);
    fail("native executable was redirected");
  }

  dlclose(engine);
  unlink(executable);
  unlink(non_pe);
  return 0;
}
