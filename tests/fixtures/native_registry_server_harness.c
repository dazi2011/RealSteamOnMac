#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define TEST_TOKEN "0123456789abcdef0123456789abcdef"
#define TYPED_REGISTRY_HEADER "RSMREG\t1\n"
#define TYPED_REGISTRY_BODY_CAPACITY 16384

typedef void (*start_server_function)(void);
typedef bool (*is_managed_function)(uint32_t);
typedef int (*spawn_decision_function)(const char *, char *const []);

static uint16_t reserve_test_port(void) {
  int socket_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (socket_fd < 0) {
    return 0;
  }

  struct sockaddr_in address;
  memset(&address, 0, sizeof(address));
  address.sin_family = AF_INET;
  address.sin_port = 0;
  address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  if (bind(
          socket_fd, (const struct sockaddr *)&address,
          sizeof(address)) != 0) {
    close(socket_fd);
    return 0;
  }

  socklen_t length = sizeof(address);
  if (getsockname(
          socket_fd, (struct sockaddr *)&address, &length) != 0) {
    close(socket_fd);
    return 0;
  }
  uint16_t port = ntohs(address.sin_port);
  close(socket_fd);
  return port;
}

static int connect_with_retry(uint16_t port) {
  for (int attempt = 0; attempt < 200; ++attempt) {
    int connection = socket(AF_INET, SOCK_STREAM, 0);
    if (connection < 0) {
      return -1;
    }

    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(port);
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (connect(
            connection, (const struct sockaddr *)&address,
            sizeof(address)) == 0) {
      return connection;
    }
    close(connection);
    usleep(10000);
  }
  return -1;
}

static bool send_all(int connection, const char *bytes, size_t length) {
  size_t sent = 0;
  while (sent < length) {
    ssize_t result = send(connection, bytes + sent, length - sent, 0);
    if (result <= 0) {
      return false;
    }
    sent += (size_t)result;
  }
  return true;
}

static int send_request_capture(
    uint16_t port,
    const char *request,
    size_t request_length,
    char *response,
    size_t response_capacity) {
  int connection = connect_with_retry(port);
  if (connection < 0) {
    fputs("could not connect to registry server\n", stderr);
    return -1;
  }
  if (!send_all(connection, request, request_length)) {
    close(connection);
    return -1;
  }

  size_t total = 0;
  while (total + 1 < response_capacity) {
    ssize_t received = recv(
        connection, response + total,
        response_capacity - total - 1, 0);
    if (received < 0) {
      close(connection);
      return -1;
    }
    if (received == 0) {
      break;
    }
    total += (size_t)received;
  }
  close(connection);
  if (total == 0) {
    return -1;
  }
  response[total] = '\0';

  int status = 0;
  if (sscanf(response, "HTTP/1.1 %d", &status) != 1) {
    return -1;
  }
  return status;
}

static int send_request(
    uint16_t port, const char *request, size_t request_length) {
  char response[2048];
  return send_request_capture(
      port, request, request_length, response, sizeof(response));
}

static int post_registry(
    uint16_t port, const char *token, const char *payload) {
  char request[2048];
  size_t payload_length = strlen(payload);
  int request_length = snprintf(
      request, sizeof(request),
      "POST /registry?token=%s HTTP/1.1\r\n"
      "Host: 127.0.0.1:%u\r\n"
      "Content-Type: text/plain\r\n"
      "Content-Length: %zu\r\n"
      "Connection: close\r\n\r\n"
      "%s",
      token, (unsigned int)port, payload_length, payload);
  if (
      request_length <= 0 ||
      request_length >= (int)sizeof(request)
  ) {
    return -1;
  }
  return send_request(port, request, (size_t)request_length);
}

static int request_registry_options(
    uint16_t port,
    const char *token,
    char *response,
    size_t response_capacity) {
  char request[2048];
  int request_length = snprintf(
      request, sizeof(request),
      "OPTIONS /registry?token=%s HTTP/1.1\r\n"
      "Host: 127.0.0.1:%u\r\n"
      "Connection: close\r\n\r\n",
      token, (unsigned int)port);
  if (
      request_length <= 0 ||
      request_length >= (int)sizeof(request)
  ) {
    return -1;
  }
  return send_request_capture(
      port, request, (size_t)request_length,
      response, response_capacity);
}

static bool expect_status_named(
    uint16_t port,
    const char *token,
    const char *payload,
    int expected,
    const char *label) {
  int actual = post_registry(port, token, payload);
  if (actual != expected) {
    fprintf(
        stderr, "%s: expected %d, got %d\n",
        label, expected, actual);
    return false;
  }
  return true;
}

static int request_config(
    uint16_t port,
    const char *method,
    const char *token,
    uint32_t appid,
    const char *payload,
    char *response,
    size_t response_capacity) {
  char request[4096];
  size_t payload_length = payload != NULL ? strlen(payload) : 0;
  int request_length;
  if (strcmp(method, "POST") == 0) {
    request_length = snprintf(
        request, sizeof(request),
        "POST /config?token=%s&appid=%u HTTP/1.1\r\n"
        "Host: 127.0.0.1:%u\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n\r\n"
        "%s",
        token, (unsigned int)appid, (unsigned int)port,
        payload_length, payload != NULL ? payload : "");
  } else {
    request_length = snprintf(
        request, sizeof(request),
        "%s /config?token=%s&appid=%u HTTP/1.1\r\n"
        "Host: 127.0.0.1:%u\r\n"
        "Connection: close\r\n\r\n",
        method, token, (unsigned int)appid, (unsigned int)port);
  }
  if (
      request_length <= 0 ||
      request_length >= (int)sizeof(request)
  ) {
    return -1;
  }
  return send_request_capture(
      port, request, (size_t)request_length,
      response, response_capacity);
}

static int request_shortcut_config(
    uint16_t port,
    const char *method,
    const char *token,
    uint32_t shortcut_id,
    const char *payload,
    char *response,
    size_t response_capacity) {
  char request[4096];
  size_t payload_length = payload != NULL ? strlen(payload) : 0;
  int request_length;
  if (strcmp(method, "POST") == 0) {
    request_length = snprintf(
        request, sizeof(request),
        "POST /config?token=%s&kind=shortcut&id=%u HTTP/1.1\r\n"
        "Host: 127.0.0.1:%u\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n\r\n"
        "%s",
        token, (unsigned int)shortcut_id, (unsigned int)port,
        payload_length, payload != NULL ? payload : "");
  } else {
    request_length = snprintf(
        request, sizeof(request),
        "%s /config?token=%s&kind=shortcut&id=%u HTTP/1.1\r\n"
        "Host: 127.0.0.1:%u\r\n"
        "Connection: close\r\n\r\n",
        method, token, (unsigned int)shortcut_id, (unsigned int)port);
  }
  if (
      request_length <= 0 ||
      request_length >= (int)sizeof(request)
  ) {
    return -1;
  }
  return send_request_capture(
      port, request, (size_t)request_length,
      response, response_capacity);
}

static int request_action(
    uint16_t port,
    const char *token,
    uint32_t appid,
    const char *payload,
    char *response,
    size_t response_capacity) {
  char request[4096];
  size_t payload_length = strlen(payload);
  int request_length = snprintf(
      request, sizeof(request),
      "POST /action?token=%s&appid=%u HTTP/1.1\r\n"
      "Host: 127.0.0.1:%u\r\n"
      "Content-Type: text/plain\r\n"
      "Content-Length: %zu\r\n"
      "Connection: close\r\n\r\n"
      "%s",
      token, (unsigned int)appid, (unsigned int)port,
      payload_length, payload);
  if (
      request_length <= 0 ||
      request_length >= (int)sizeof(request)
  ) {
    return -1;
  }
  return send_request_capture(
      port, request, (size_t)request_length,
      response, response_capacity);
}

static int request_job(
    uint16_t port,
    const char *token,
    uint32_t appid,
    const char *job_id,
    char *response,
    size_t response_capacity) {
  char request[2048];
  int request_length = snprintf(
      request, sizeof(request),
      "GET /job?token=%s&appid=%u&job=%s HTTP/1.1\r\n"
      "Host: 127.0.0.1:%u\r\n"
      "Connection: close\r\n\r\n",
      token, (unsigned int)appid, job_id, (unsigned int)port);
  if (
      request_length <= 0 ||
      request_length >= (int)sizeof(request)
  ) {
    return -1;
  }
  return send_request_capture(
      port, request, (size_t)request_length,
      response, response_capacity);
}

static bool make_directory(const char *path) {
  return mkdir(path, 0700) == 0 || errno == EEXIST;
}

static bool write_text_file(
    const char *path, const char *contents, mode_t mode) {
  FILE *stream = fopen(path, "w");
  if (stream == NULL) {
    return false;
  }
  bool success = fputs(contents, stream) >= 0;
  success = success && fclose(stream) == 0;
  success = success && chmod(path, mode) == 0;
  return success;
}

static bool write_binary_file(
    const char *path, const unsigned char *contents, size_t length,
    mode_t mode) {
  int descriptor = open(path, O_WRONLY | O_CREAT | O_TRUNC, mode);
  if (descriptor < 0) {
    return false;
  }

  size_t written = 0;
  bool success = true;
  while (written < length) {
    ssize_t result = write(
        descriptor, contents + written, length - written);
    if (result <= 0) {
      success = false;
      break;
    }
    written += (size_t)result;
  }
  success = success && close(descriptor) == 0;
  success = success && chmod(path, mode) == 0;
  return success;
}

static bool percent_encode_path(
    const char *path, char *encoded, size_t encoded_capacity) {
  size_t written = 0;
  for (size_t index = 0; path[index] != '\0'; ++index) {
    if (written + 3 >= encoded_capacity) {
      return false;
    }
    int length = snprintf(
        encoded + written, encoded_capacity - written,
        "%%%02X", (unsigned char)path[index]);
    if (length != 3) {
      return false;
    }
    written += 3;
  }
  if (written >= encoded_capacity) {
    return false;
  }
  encoded[written] = '\0';
  return true;
}

static bool create_legacy_registry_cache(
    const char *home,
    const uint32_t *appids,
    size_t count) {
  char library[1024];
  char application_support[1024];
  char support[1024];
  char path[1200];
  if (
      snprintf(
          library, sizeof(library),
          "%s/Library", home) >= (int)sizeof(library) ||
      snprintf(
          application_support, sizeof(application_support),
          "%s/Application Support", library) >=
          (int)sizeof(application_support) ||
      snprintf(
          support, sizeof(support),
          "%s/Library/Application Support/RealSteamOnMac",
          home) >= (int)sizeof(support) ||
      snprintf(
          path, sizeof(path),
          "%s/managed-appids-cache.txt",
          support) >= (int)sizeof(path)
  ) {
    return false;
  }
  if (
      !make_directory(library) ||
      !make_directory(application_support) ||
      !make_directory(support)
  ) {
    return false;
  }

  char buffer[256];
  size_t offset = 0;
  for (size_t index = 0; index < count; ++index) {
    int length = snprintf(
        buffer + offset, sizeof(buffer) - offset,
        "%u\n", (unsigned int)appids[index]);
    if (
        length <= 0 ||
        offset + (size_t)length >= sizeof(buffer)
    ) {
      return false;
    }
    offset += (size_t)length;
  }
  buffer[offset] = '\0';
  return write_text_file(path, buffer, 0600);
}

static bool make_shortcut_fixtures(
    const char *root,
    char valid_path[PATH_MAX],
    char valid_symlink[PATH_MAX],
    char symlink_parent_path[PATH_MAX],
    char missing_path[PATH_MAX],
    char nonmz_path[PATH_MAX],
    char app_path[PATH_MAX]) {
  char shortcuts[1024];
  char real_parent[1024];
  char linked_parent[1024];
  char valid_target[1024];
  char real_parent_target[1024];
  if (
      snprintf(shortcuts, sizeof(shortcuts), "%s/Shortcuts", root) >=
          (int)sizeof(shortcuts) ||
      snprintf(real_parent, sizeof(real_parent), "%s/Real Parent", root) >=
          (int)sizeof(real_parent) ||
      snprintf(linked_parent, sizeof(linked_parent), "%s/Linked Parent", root) >=
          (int)sizeof(linked_parent) ||
      snprintf(
          valid_target, sizeof(valid_target),
          "%s/Fixture Game.exe", shortcuts) >=
          (int)sizeof(valid_target) ||
      snprintf(
          real_parent_target, sizeof(real_parent_target),
          "%s/Parent Target.exe", real_parent) >=
          (int)sizeof(real_parent_target) ||
      snprintf(
          symlink_parent_path, PATH_MAX,
          "%s/Parent Target.exe", linked_parent) >= PATH_MAX ||
      !make_directory(shortcuts) ||
      !make_directory(real_parent)
  ) {
    return false;
  }

  unsigned char mz_bytes[] = {'M', 'Z', 'f', 'i', 'x', 't', 'u', 'r', 'e'};
  if (
      !write_binary_file(valid_target, mz_bytes, sizeof(mz_bytes), 0600) ||
      realpath(valid_target, valid_path) == NULL
  ) {
    return false;
  }

  if (
      snprintf(
          valid_symlink, PATH_MAX, "%s/Linked Fixture.exe",
          shortcuts) >= PATH_MAX ||
      (unlink(valid_symlink) != 0 && errno != ENOENT) ||
      symlink(valid_path, valid_symlink) != 0
  ) {
    return false;
  }

  if (
      !write_binary_file(
          real_parent_target, mz_bytes, sizeof(mz_bytes), 0600) ||
      (unlink(linked_parent) != 0 && errno != ENOENT) ||
      symlink(real_parent, linked_parent) != 0
  ) {
    return false;
  }

  if (
      snprintf(missing_path, PATH_MAX, "%s/Missing Shortcut.exe", shortcuts) >=
          PATH_MAX ||
      snprintf(nonmz_path, PATH_MAX, "%s/Not PE.exe", shortcuts) >=
          PATH_MAX ||
      snprintf(app_path, PATH_MAX, "%s/Fixture.app", shortcuts) >=
          PATH_MAX ||
      !write_text_file(nonmz_path, "not PE", 0600) ||
      !write_binary_file(app_path, mz_bytes, sizeof(mz_bytes), 0600)
  ) {
    return false;
  }

  return true;
}

static bool prepare_fake_runtime(
    const char *home, const char *job_root) {
  char library[1024];
  char application_support[1024];
  char support[1024];
  char runtimes[1024];
  char bin[1024];
  char runtime[1200];
  if (
      snprintf(library, sizeof(library), "%s/Library", home) >=
          (int)sizeof(library) ||
      snprintf(
          application_support, sizeof(application_support),
          "%s/Application Support", library) >=
          (int)sizeof(application_support) ||
      snprintf(
          support, sizeof(support),
          "%s/RealSteamOnMac", application_support) >=
          (int)sizeof(support) ||
      snprintf(runtimes, sizeof(runtimes), "%s/runtimes", support) >=
          (int)sizeof(runtimes) ||
      snprintf(bin, sizeof(bin), "%s/bin", runtimes) >=
          (int)sizeof(bin) ||
      snprintf(
          runtime, sizeof(runtime),
          "%s/realsteamonmac-runtime", bin) >= (int)sizeof(runtime) ||
      !make_directory(library) ||
      !make_directory(application_support) ||
      !make_directory(support) ||
      !make_directory(runtimes) ||
      !make_directory(bin) ||
      !make_directory(job_root)
  ) {
    return false;
  }
  FILE *stream = fopen(runtime, "w");
  if (stream == NULL) {
    return false;
  }
  fputs(
      "import json, os, pathlib, sys\n"
      "def value(name): return sys.argv[sys.argv.index(name) + 1]\n"
      "appid = value('--appid')\n"
      "job = value('--job-id')\n"
      "root = pathlib.Path(os.environ['REALSTEAMONMAC_JOB_ROOT']) / appid\n"
      "root.mkdir(parents=True, exist_ok=True)\n"
      "path = root / (job + '.json')\n"
      "path.write_text(json.dumps({'schema': 1, 'appid': int(appid), "
      "'job_id': job, 'action': 'fixture', 'state': 'completed'}) + '\\n')\n"
      "os.chmod(path, 0o600)\n",
      stream);
  bool success = fclose(stream) == 0 && chmod(runtime, 0600) == 0;
  return success;
}

static const char *response_body(const char *response) {
  const char *separator = strstr(response, "\r\n\r\n");
  return separator != NULL ? separator + 4 : NULL;
}

static bool expect_mixed_registry_publish(
    uint16_t port,
    const char *token,
    uint32_t store_appid,
    const char *shortcut_target) {
  char encoded_target[PATH_MAX * 3 + 1];
  char payload[TYPED_REGISTRY_BODY_CAPACITY];
  if (!percent_encode_path(shortcut_target, encoded_target,
                           sizeof(encoded_target))) {
    fputs("could not encode shortcut target\n", stderr);
    return false;
  }
  if (
      snprintf(
          payload, sizeof(payload),
          TYPED_REGISTRY_HEADER
          "A\t1118200\n"
          "A\t990080\n"
          "A\t%u\n"
          "S\t7\t%s\n",
          (unsigned int)store_appid, encoded_target) >=
      (int)sizeof(payload)
  ) {
    fputs("mixed registry payload is too large\n", stderr);
    return false;
  }
  return expect_status_named(
      port, token, payload, 204, "mixed typed registry publish");
}

static bool expect_atomic_registry_rejection(
    uint16_t port,
    const char *token,
    uint32_t store_appid,
    const char *invalid_shortcut_target) {
  char encoded_target[PATH_MAX * 3 + 1];
  char payload[TYPED_REGISTRY_BODY_CAPACITY];
  if (!percent_encode_path(invalid_shortcut_target, encoded_target,
                           sizeof(encoded_target))) {
    fputs("could not encode invalid shortcut target\n", stderr);
    return false;
  }
  if (
      snprintf(
          payload, sizeof(payload),
          TYPED_REGISTRY_HEADER
          "A\t%u\n"
          "S\t8\t%s\n",
          (unsigned int)store_appid, encoded_target) >=
      (int)sizeof(payload)
  ) {
    fputs("atomic rejection payload is too large\n", stderr);
    return false;
  }
  return expect_status_named(
      port, token, payload, 400, "atomic registry rejection");
}

static bool expect_collision_rejection(
    uint16_t port,
    const char *token,
    uint32_t store_appid,
    const char *valid_shortcut_target) {
  char encoded_target[PATH_MAX * 3 + 1];
  char payload[TYPED_REGISTRY_BODY_CAPACITY];
  if (!percent_encode_path(valid_shortcut_target, encoded_target,
                           sizeof(encoded_target))) {
    fputs("could not encode collision shortcut target\n", stderr);
    return false;
  }
  if (
      snprintf(
          payload, sizeof(payload),
          TYPED_REGISTRY_HEADER
          "A\t%u\n"
          "S\t%u\t%s\n",
          (unsigned int)store_appid, (unsigned int)store_appid,
          encoded_target) >=
      (int)sizeof(payload)
  ) {
    fputs("collision payload is too large\n", stderr);
    return false;
  }
  return expect_status_named(
      port, token, payload, 400, "cross-type collision rejection");
}

static bool expect_invalid_shortcut_payloads(
    uint16_t port,
    const char *token,
    const char *missing_path,
    const char *nonmz_path,
    const char *symlink_path,
    const char *symlink_parent_path,
    const char *app_path) {
  char encoded_missing[PATH_MAX * 3 + 1];
  char encoded_nonmz[PATH_MAX * 3 + 1];
  char encoded_symlink[PATH_MAX * 3 + 1];
  char encoded_symlink_parent[PATH_MAX * 3 + 1];
  char encoded_app[PATH_MAX * 3 + 1];
  char payload[TYPED_REGISTRY_BODY_CAPACITY];
  if (
      !percent_encode_path(missing_path, encoded_missing,
                           sizeof(encoded_missing)) ||
      !percent_encode_path(nonmz_path, encoded_nonmz,
                           sizeof(encoded_nonmz)) ||
      !percent_encode_path(symlink_path, encoded_symlink,
                           sizeof(encoded_symlink)) ||
      !percent_encode_path(symlink_parent_path, encoded_symlink_parent,
                           sizeof(encoded_symlink_parent)) ||
      !percent_encode_path(app_path, encoded_app, sizeof(encoded_app))
  ) {
    fputs("could not encode shortcut validation paths\n", stderr);
    return false;
  }

  const struct {
    const char *label;
    const char *record;
    const char *encoded_path;
  } cases[] = {
      {"missing shortcut file", "S\t9\t%s\n", encoded_missing},
      {"non-MZ shortcut file", "S\t10\t%s\n", encoded_nonmz},
      {"leaf symlink shortcut file", "S\t11\t%s\n", encoded_symlink},
      {"parent symlink shortcut file", "S\t12\t%s\n", encoded_symlink_parent},
      {".app shortcut file", "S\t13\t%s\n", encoded_app},
  };

  for (size_t index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
    int header_length = snprintf(
        payload, sizeof(payload), TYPED_REGISTRY_HEADER);
    if (
        header_length <= 0 ||
        header_length >= (int)sizeof(payload)
    ) {
      fprintf(stderr, "%s payload is too large\n", cases[index].label);
      return false;
    }
    if (
        snprintf(
            payload + header_length, sizeof(payload) - (size_t)header_length,
            cases[index].record, cases[index].encoded_path) < 0 ||
        strlen(payload) >= sizeof(payload) ||
        strlen(payload) < (size_t)header_length
    ) {
      fprintf(stderr, "%s payload is too large\n", cases[index].label);
      return false;
    }
    if (
        (size_t)header_length +
        strlen(payload + header_length) >=
        (int)sizeof(payload)
    ) {
      fprintf(stderr, "%s payload is too large\n", cases[index].label);
      return false;
    }
    if (!expect_status_named(
            port, token, payload, 400, cases[index].label)) {
      return false;
    }
  }
  return true;
}

static bool expect_registry_cache_permissions_and_legacy_migration(
    const char *home) {
  char legacy_path[1200];
  char typed_path[1200];
  char binding_path[1200];
  if (
      snprintf(
          legacy_path, sizeof(legacy_path),
          "%s/Library/Application Support/RealSteamOnMac/"
          "managed-appids-cache.txt",
          home) >= (int)sizeof(legacy_path) ||
      snprintf(
          typed_path, sizeof(typed_path),
          "%s/Library/Application Support/RealSteamOnMac/"
          "managed-registry-v1.txt",
          home) >= (int)sizeof(typed_path) ||
      snprintf(
          binding_path, sizeof(binding_path),
          "%s/Library/Application Support/RealSteamOnMac/"
          "shortcut-binding-7.txt",
          home) >= (int)sizeof(binding_path)
  ) {
    return false;
  }

  struct stat file_stat;
  if (
      stat(legacy_path, &file_stat) != 0 ||
      !S_ISREG(file_stat.st_mode) ||
      (file_stat.st_mode & 0777) != 0600
  ) {
    fputs("legacy cache permissions are invalid\n", stderr);
    return false;
  }
  if (
      stat(typed_path, &file_stat) != 0 ||
      !S_ISREG(file_stat.st_mode) ||
      (file_stat.st_mode & 0777) != 0600
  ) {
    fputs("typed registry cache permissions are invalid\n", stderr);
    return false;
  }
  if (
      stat(binding_path, &file_stat) != 0 ||
      !S_ISREG(file_stat.st_mode) ||
      (file_stat.st_mode & 0777) != 0600
  ) {
    fputs("shortcut binding permissions are invalid\n", stderr);
    return false;
  }
  return true;
}

static bool expect_shortcut_action_forbidden(
    uint16_t port,
    const char *token,
    uint32_t shortcut_appid,
    const char *payload,
    char *response,
    size_t response_capacity) {
  if (
      request_action(
          port, token, shortcut_appid, payload,
          response, response_capacity) != 403
  ) {
    fprintf(
        stderr,
        "shortcut action authorization unexpectedly succeeded for %u\n",
        (unsigned int)shortcut_appid);
    return false;
  }
  return true;
}

static bool expect_restart_cache_restore(
    const char *harness,
    const char *engine,
    const char *shortcut_target) {
  pid_t child = fork();
  if (child < 0) {
    return false;
  }
  if (child == 0) {
    execl(
        harness, harness, engine,
        "--cache-probe", shortcut_target, (char *)NULL);
    _exit(127);
  }
  int status = 0;
  return
      waitpid(child, &status, 0) == child &&
      WIFEXITED(status) &&
      WEXITSTATUS(status) == 0;
}

static bool expect_persistence_failure_is_atomic(
    uint16_t port,
    is_managed_function is_managed) {
  const char *home = getenv("HOME");
  char saved_home[PATH_MAX];
  if (
      home == NULL ||
      strlen(home) >= sizeof(saved_home)
  ) {
    return false;
  }
  strcpy(saved_home, home);
  bool success =
      setenv("HOME", "/dev/null", 1) == 0 &&
      expect_status_named(
          port, TEST_TOKEN,
          TYPED_REGISTRY_HEADER "A\t7777777\n",
          500, "registry persistence failure") &&
      is_managed(3333333) &&
      !is_managed(7777777);
  if (setenv("HOME", saved_home, 1) != 0) {
    return false;
  }
  return success;
}

int main(int argc, char **argv) {
  if (
      argc == 4 &&
      strcmp(argv[2], "--cache-probe") == 0
  ) {
    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
      return 2;
    }
    is_managed_function is_managed =
        (is_managed_function)dlsym(
            handle, "realsteamonmac_is_managed_app");
    spawn_decision_function should_redirect =
        (spawn_decision_function)dlsym(
            handle, "realsteamonmac_should_redirect_spawn");
    char shortcut_id[] = "SteamAppId=7";
    char *environment[] = {shortcut_id, NULL};
    if (
        is_managed == NULL ||
        should_redirect == NULL ||
        !is_managed(3333333) ||
        is_managed(7) ||
        should_redirect(argv[3], environment) != 1
    ) {
      return 1;
    }
    return 0;
  }
  if (argc != 2) {
    fprintf(stderr, "usage: %s NATIVE_ENGINE\n", argv[0]);
    return 2;
  }

  uint16_t port = reserve_test_port();
  if (port == 0) {
    fputs("could not reserve a registry test port\n", stderr);
    return 2;
  }
  char port_text[16];
  snprintf(port_text, sizeof(port_text), "%u", (unsigned int)port);
  char config_root[] =
      "/tmp/realsteamonmac-config-harness.XXXXXX";
  if (mkdtemp(config_root) == NULL) {
    perror("mkdtemp");
    return 2;
  }
  if (
      setenv("REALSTEAMONMAC_REGISTRY_TOKEN", TEST_TOKEN, 1) != 0 ||
      setenv("REALSTEAMONMAC_REGISTRY_PORT", port_text, 1) != 0 ||
      setenv(
          "REALSTEAMONMAC_APP_CONFIG_ROOT",
          config_root, 1) != 0
  ) {
    perror("setenv");
    return 2;
  }
  char job_root[1024];
  if (
      snprintf(
          job_root, sizeof(job_root),
          "%s/jobs", config_root) >= (int)sizeof(job_root) ||
      setenv("HOME", config_root, 1) != 0 ||
      setenv("REALSTEAMONMAC_JOB_ROOT", job_root, 1) != 0 ||
      !prepare_fake_runtime(config_root, job_root)
  ) {
    fputs("could not prepare fake action runtime\n", stderr);
    return 2;
  }

  uint32_t legacy_registry_ids[] = {1118200, 990080};
  if (
      !create_legacy_registry_cache(
          config_root, legacy_registry_ids,
          sizeof(legacy_registry_ids) / sizeof(legacy_registry_ids[0]))
  ) {
    fputs("could not prepare legacy registry cache\n", stderr);
    return 2;
  }

  char valid_shortcut_path[PATH_MAX];
  char symlink_shortcut_path[PATH_MAX];
  char symlink_parent_path[PATH_MAX];
  char missing_shortcut_path[PATH_MAX];
  char nonmz_shortcut_path[PATH_MAX];
  char app_shortcut_path[PATH_MAX];
  char replacement_shortcut_candidate[PATH_MAX];
  char replacement_shortcut_path[PATH_MAX];
  if (
      !make_shortcut_fixtures(
          config_root, valid_shortcut_path, symlink_shortcut_path,
          symlink_parent_path, missing_shortcut_path,
      nonmz_shortcut_path, app_shortcut_path)
  ) {
    fputs("could not prepare shortcut fixtures\n", stderr);
    return 2;
  }
  if (
      snprintf(
          replacement_shortcut_candidate,
          sizeof(replacement_shortcut_candidate),
          "%s/Shortcuts/Replacement Game.exe",
          config_root) >= PATH_MAX
  ) {
    fputs("replacement shortcut path is too long\n", stderr);
    return 2;
  }
  const unsigned char replacement_mz[] = {
      'M', 'Z', 'r', 'e', 'p', 'l', 'a', 'c', 'e',
  };
  if (
      !write_binary_file(
          replacement_shortcut_candidate,
          replacement_mz, sizeof(replacement_mz), 0600) ||
      realpath(
          replacement_shortcut_candidate,
          replacement_shortcut_path) == NULL
  ) {
    fputs("could not prepare replacement shortcut fixture\n", stderr);
    return 2;
  }

  void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (handle == NULL) {
    fprintf(stderr, "dlopen failed: %s\n", dlerror());
    return 2;
  }
  start_server_function start_server =
      (start_server_function)dlsym(
          handle, "realsteamonmac_start_registry_server");
  is_managed_function is_managed =
      (is_managed_function)dlsym(
          handle, "realsteamonmac_is_managed_app");
  spawn_decision_function should_redirect =
      (spawn_decision_function)dlsym(
          handle, "realsteamonmac_should_redirect_spawn");
  if (
      start_server == NULL ||
      is_managed == NULL ||
      should_redirect == NULL
  ) {
    fputs("registry server exports are missing\n", stderr);
    return 2;
  }
  start_server();

  if (
      !is_managed(1118200) ||
      !is_managed(990080) ||
      is_managed(7)
  ) {
    fputs("legacy registry migration failed\n", stderr);
    return 1;
  }

  char response[4096];
  if (
      !expect_mixed_registry_publish(
          port, TEST_TOKEN, 3333333, valid_shortcut_path) ||
      request_registry_options(
          port, TEST_TOKEN, response, sizeof(response)) != 204
  ) {
    fputs("mixed typed registry publish or OPTIONS failed\n", stderr);
    return 1;
  }

  if (
      !is_managed(3333333) ||
      is_managed(7)
  ) {
    fputs("typed registry state isolation failed\n", stderr);
    return 1;
  }

  if (
      !expect_restart_cache_restore(
          argv[0], argv[1], valid_shortcut_path)
  ) {
    fputs("typed registry restart recovery failed\n", stderr);
    return 1;
  }

  if (!expect_persistence_failure_is_atomic(port, is_managed)) {
    fputs("registry persistence failure was not atomic\n", stderr);
    return 1;
  }

  char encoded_replacement[PATH_MAX * 3 + 1];
  char rebound_payload[TYPED_REGISTRY_BODY_CAPACITY];
  char shortcut_id[] = "SteamAppId=7";
  char *shortcut_environment[] = {shortcut_id, NULL};
  if (
      !percent_encode_path(
          replacement_shortcut_path,
          encoded_replacement, sizeof(encoded_replacement)) ||
      snprintf(
          rebound_payload, sizeof(rebound_payload),
          TYPED_REGISTRY_HEADER
          "A\t3333333\n"
          "S\t7\t%s\n",
          encoded_replacement) >= (int)sizeof(rebound_payload) ||
      !expect_status_named(
          port, TEST_TOKEN, rebound_payload, 500,
          "active shortcut target rebinding") ||
      should_redirect(
          valid_shortcut_path, shortcut_environment) != 1 ||
      should_redirect(
          replacement_shortcut_path, shortcut_environment) != 0
  ) {
    fputs("active shortcut target rebinding was not rejected\n", stderr);
    return 1;
  }

  if (
      !expect_collision_rejection(
          port, TEST_TOKEN, 4444444, valid_shortcut_path) ||
      !is_managed(3333333) ||
      is_managed(4444444)
  ) {
    fputs("collision rejection failed\n", stderr);
    return 1;
  }

  if (
      !expect_atomic_registry_rejection(
          port, TEST_TOKEN, 5555555, missing_shortcut_path) ||
      !is_managed(3333333) ||
      is_managed(5555555)
  ) {
    fputs("atomic rejection failed\n", stderr);
    return 1;
  }

  if (
      !expect_invalid_shortcut_payloads(
          port, TEST_TOKEN,
          missing_shortcut_path, nonmz_shortcut_path,
          symlink_shortcut_path, symlink_parent_path,
          app_shortcut_path) ||
      !is_managed(3333333)
  ) {
    fputs("invalid shortcut validation failed\n", stderr);
    return 1;
  }

  const char *action_payload =
      "action=run-command&target=Fixture.exe&"
      "arguments=&environment=";
  if (
      !expect_shortcut_action_forbidden(
          port, TEST_TOKEN, 7, action_payload,
          response, sizeof(response))
  ) {
    fputs("shortcut action permission regression failed\n", stderr);
    return 1;
  }

  int status = request_action(
      port, TEST_TOKEN, 3333333,
      action_payload, response, sizeof(response));
  const char *body = response_body(response);
  char job_id[33];
  memset(job_id, 0, sizeof(job_id));
  if (status == 202 && body != NULL) {
    const char *start = strstr(body, "\"job_id\":\"");
    if (start != NULL) {
      start += strlen("\"job_id\":\"");
      const char *end = strchr(start, '"');
      if (end != NULL && end - start == 32) {
        memcpy(job_id, start, 32);
      }
    }
  }
  if (job_id[0] == '\0') {
    fputs("authorized typed store action did not return a job ID\n", stderr);
    return 1;
  }
  int job_status = 404;
  for (int attempt = 0; attempt < 200 && job_status == 404; ++attempt) {
    job_status = request_job(
        port, TEST_TOKEN, 3333333, job_id,
        response, sizeof(response));
    if (job_status == 404) {
      usleep(10000);
    }
  }
  body = response_body(response);
  if (
      job_status != 200 || body == NULL ||
      strstr(body, "\"state\": \"completed\"") == NULL
  ) {
    fputs("typed store action job status did not complete\n", stderr);
    return 1;
  }

  if (!expect_registry_cache_permissions_and_legacy_migration(config_root)) {
    return 1;
  }

  const char *valid_config =
      "compat_tool=realsteamonmac-dxvk&"
      "renderer=dxvk&msync=1&retina=1&metal_hud=1&"
      "metalfx=0&dxr=0&avx=1";
  if (
      request_config(
          port, "POST", TEST_TOKEN, 3333333,
          valid_config, response, sizeof(response)) != 204
  ) {
    fputs("authorized runtime config update failed\n", stderr);
    return 1;
  }
  char config_path[1024];
  snprintf(
      config_path, sizeof(config_path),
      "%s/3333333.json", config_root);
  struct stat config_stat;
  if (
      stat(config_path, &config_stat) != 0 ||
      (config_stat.st_mode & 0777) != 0600
  ) {
    fputs("runtime config permissions are invalid\n", stderr);
    return 1;
  }
  status = request_config(
      port, "GET", TEST_TOKEN, 3333333,
      NULL, response, sizeof(response));
  body = response_body(response);
  if (
      status != 200 || body == NULL ||
      strstr(body, "\"compat_tool\": \"realsteamonmac-dxvk\"") == NULL ||
      strstr(body, "\"renderer\": \"dxvk\"") == NULL ||
      strstr(body, "\"retina\": true") == NULL ||
      strstr(body, "\"avx\": true") == NULL
  ) {
    fputs("saved runtime config response failed\n", stderr);
    return 1;
  }

  if (
      request_shortcut_config(
          port, "POST", TEST_TOKEN, 7,
          valid_config, response, sizeof(response)) != 204
  ) {
    fputs("authorized shortcut config update failed\n", stderr);
    return 1;
  }
  char shortcut_config_path[1024];
  snprintf(
      shortcut_config_path, sizeof(shortcut_config_path),
      "%s/shortcut-7.json", config_root);
  if (
      stat(shortcut_config_path, &config_stat) != 0 ||
      (config_stat.st_mode & 0777) != 0600
  ) {
    fputs("shortcut config permissions are invalid\n", stderr);
    return 1;
  }
  status = request_shortcut_config(
      port, "GET", TEST_TOKEN, 7,
      NULL, response, sizeof(response));
  body = response_body(response);
  if (
      status != 200 || body == NULL ||
      strstr(body, "\"compat_tool\": \"realsteamonmac-dxvk\"") == NULL ||
      strstr(body, valid_shortcut_path) != NULL ||
      request_shortcut_config(
          port, "GET", TEST_TOKEN, 99,
          NULL, response, sizeof(response)) != 403
  ) {
    fputs("shortcut config response or authorization failed\n", stderr);
    return 1;
  }

  const char *invalid_config =
      "compat_tool=../escape&"
      "renderer=dxmt&msync=1&retina=0&metal_hud=0&"
      "metalfx=0&dxr=0&avx=0";
  if (
      request_config(
          port, "POST", TEST_TOKEN, 3333333,
          invalid_config, response, sizeof(response)) != 400 ||
      request_config(
          port, "GET", TEST_TOKEN, 7,
          NULL, response, sizeof(response)) != 403 ||
      request_config(
          port, "GET",
          "ffffffffffffffffffffffffffffffff",
          3333333, NULL, response, sizeof(response)) != 403
  ) {
    fputs("runtime config authorization or validation failed\n", stderr);
    return 1;
  }

  if (
      !expect_status_named(
          port, "ffffffffffffffffffffffffffffffff",
          TYPED_REGISTRY_HEADER "A\t42\n",
          403, "unauthorized typed registry publish") ||
      is_managed(42) ||
      !is_managed(3333333)
  ) {
    fputs("unauthorized registry publish changed state\n", stderr);
    return 1;
  }

  if (
      !expect_status_named(
          port, TEST_TOKEN, rebound_payload, 500,
          "deleted shortcut ID rebinding") ||
      should_redirect(
          replacement_shortcut_path, shortcut_environment) != 0
  ) {
    fputs("deleted shortcut ID was rebound to a new target\n", stderr);
    return 1;
  }

  if (
      !expect_status_named(
          port, TEST_TOKEN,
          TYPED_REGISTRY_HEADER "A\t1118200\nS\t14\t%ZZ\n",
          400, "malformed percent encoding") ||
      !is_managed(3333333)
  ) {
    fputs("invalid registry payload changed state\n", stderr);
    return 1;
  }

  char malformed_length[1024];
  int malformed_length_size = snprintf(
      malformed_length, sizeof(malformed_length),
      "POST /registry?token=%s HTTP/1.1\r\n"
      "Host: 127.0.0.1:%u\r\n"
      "Content-Length: 1x\r\n"
      "Connection: close\r\n\r\n"
      "7",
      TEST_TOKEN, (unsigned int)port);
  if (
      malformed_length_size <= 0 ||
      malformed_length_size >= (int)sizeof(malformed_length) ||
      send_request(
          port, malformed_length, (size_t)malformed_length_size) != 400 ||
      !is_managed(3333333)
  ) {
    fputs("malformed content length changed registry state\n", stderr);
    return 1;
  }

  if (
      !expect_status_named(
          port, TEST_TOKEN, TYPED_REGISTRY_HEADER,
          204, "empty typed registry publish") ||
      is_managed(3333333) ||
      request_config(
          port, "GET", TEST_TOKEN, 3333333,
          NULL, response, sizeof(response)) != 403 ||
      request_shortcut_config(
          port, "GET", TEST_TOKEN, 7,
          NULL, response, sizeof(response)) != 403
  ) {
    fputs("empty typed registry did not clear typed identities\n", stderr);
    return 1;
  }

  (void)handle;
  puts("native registry server harness: PASS");
  return 0;
}
