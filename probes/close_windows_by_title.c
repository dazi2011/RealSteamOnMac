#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <stdio.h>
#include <string.h>

struct close_context {
  const char *needle;
  unsigned int closed;
};

static BOOL CALLBACK close_matching_window(HWND window, LPARAM parameter) {
  struct close_context *context = (struct close_context *)parameter;
  char title[512];
  int length = GetWindowTextA(window, title, (int)sizeof(title));

  if (length <= 0 || strstr(title, context->needle) == NULL) {
    return TRUE;
  }
  if (!PostMessageA(window, WM_CLOSE, 0, 0)) {
    fprintf(stderr, "failed to post WM_CLOSE to %s\n", title);
    return TRUE;
  }
  context->closed += 1;
  printf("posted WM_CLOSE to %s\n", title);
  return TRUE;
}

int main(int argc, char **argv) {
  struct close_context context;

  if (argc != 2 || argv[1][0] == '\0') {
    fprintf(stderr, "usage: close-windows-by-title TITLE_SUBSTRING\n");
    return 64;
  }
  context.needle = argv[1];
  context.closed = 0;
  if (!EnumWindows(close_matching_window, (LPARAM)&context)) {
    fprintf(stderr, "EnumWindows failed: %lu\n", GetLastError());
    return 1;
  }
  if (context.closed == 0) {
    fprintf(stderr, "no matching window found: %s\n", context.needle);
    return 2;
  }
  return 0;
}
