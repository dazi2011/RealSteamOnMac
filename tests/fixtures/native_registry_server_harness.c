#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#define TEST_TOKEN "0123456789abcdef0123456789abcdef"

typedef void (*start_server_function)(void);
typedef bool (*is_managed_function)(uint32_t);

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

static bool expect_status(
    uint16_t port, const char *token, const char *payload, int expected) {
  int actual = post_registry(port, token, payload);
  if (actual != expected) {
    fprintf(
        stderr, "registry status mismatch: expected %d, got %d\n",
        expected, actual);
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

int main(int argc, char **argv) {
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
  if (start_server == NULL || is_managed == NULL) {
    fputs("registry server exports are missing\n", stderr);
    return 2;
  }
  start_server();

  if (
      !expect_status(
          port, TEST_TOKEN, "1118200,990080,1118200", 204) ||
      !is_managed(1118200) ||
      !is_managed(990080)
  ) {
    fputs("authorized registry publish failed\n", stderr);
    return 1;
  }

  char response[4096];
  int status = request_config(
      port, "GET", TEST_TOKEN, 1118200,
      NULL, response, sizeof(response));
  const char *body = response_body(response);
  if (
      status != 200 || body == NULL ||
      strstr(body, "\"compat_tool\": \"\"") == NULL ||
      strstr(body, "\"renderer\": \"dxmt\"") == NULL ||
      strstr(body, "\"msync\": true") == NULL
  ) {
    fputs("default runtime config response failed\n", stderr);
    return 1;
  }

  const char *action_payload =
      "action=run-command&target=Fixture.exe&"
      "arguments=&environment=";
  status = request_action(
      port, TEST_TOKEN, 1118200,
      action_payload, response, sizeof(response));
  body = response_body(response);
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
    fputs("authorized action did not return a job ID\n", stderr);
    return 1;
  }
  int job_status = 404;
  for (int attempt = 0; attempt < 200 && job_status == 404; ++attempt) {
    job_status = request_job(
        port, TEST_TOKEN, 1118200, job_id,
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
    fputs("action job status did not complete\n", stderr);
    return 1;
  }
  if (
      request_action(
          port, TEST_TOKEN, 42,
          action_payload, response, sizeof(response)) != 403 ||
      request_action(
          port, "ffffffffffffffffffffffffffffffff",
          1118200, action_payload, response, sizeof(response)) != 403 ||
      request_job(
          port, TEST_TOKEN, 1118200, "../escape",
          response, sizeof(response)) != 403
  ) {
    fputs("action job authorization or path validation failed\n", stderr);
    return 1;
  }

  const char *valid_config =
      "compat_tool=realsteamonmac-dxvk&"
      "renderer=dxvk&msync=1&retina=1&metal_hud=1&"
      "metalfx=0&dxr=0&avx=1";
  if (
      request_config(
          port, "POST", TEST_TOKEN, 1118200,
          valid_config, response, sizeof(response)) != 204
  ) {
    fputs("authorized runtime config update failed\n", stderr);
    return 1;
  }
  char config_path[1024];
  snprintf(
      config_path, sizeof(config_path),
      "%s/1118200.json", config_root);
  struct stat config_stat;
  if (
      stat(config_path, &config_stat) != 0 ||
      (config_stat.st_mode & 0777) != 0600
  ) {
    fputs("runtime config permissions are invalid\n", stderr);
    return 1;
  }
  status = request_config(
      port, "GET", TEST_TOKEN, 1118200,
      NULL, response, sizeof(response));
  body = response_body(response);
  if (
      status != 200 || body == NULL ||
      strstr(
          body,
          "\"compat_tool\": \"realsteamonmac-dxvk\""
      ) == NULL ||
      strstr(body, "\"renderer\": \"dxvk\"") == NULL ||
      strstr(body, "\"retina\": true") == NULL ||
      strstr(body, "\"avx\": true") == NULL
  ) {
    fputs("saved runtime config response failed\n", stderr);
    return 1;
  }

  const char *invalid_config =
      "compat_tool=../escape&"
      "renderer=dxmt&msync=1&retina=0&metal_hud=0&"
      "metalfx=0&dxr=0&avx=0";
  if (
      request_config(
          port, "POST", TEST_TOKEN, 1118200,
          invalid_config, response, sizeof(response)) != 400 ||
      request_config(
          port, "GET", TEST_TOKEN, 42,
          NULL, response, sizeof(response)) != 403 ||
      request_config(
          port, "GET",
          "ffffffffffffffffffffffffffffffff",
          1118200, NULL, response, sizeof(response)) != 403
  ) {
    fputs("runtime config authorization or validation failed\n", stderr);
    return 1;
  }

  if (
      !expect_status(
          port, "ffffffffffffffffffffffffffffffff", "42", 403) ||
      is_managed(42) ||
      !is_managed(1118200)
  ) {
    fputs("unauthorized registry publish changed state\n", stderr);
    return 1;
  }

  if (
      !expect_status(port, TEST_TOKEN, "1118200,broken", 400) ||
      !is_managed(1118200) ||
      !is_managed(990080)
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
      !is_managed(1118200) ||
      !is_managed(990080)
  ) {
    fputs("malformed content length changed registry state\n", stderr);
    return 1;
  }

  if (
      !expect_status(port, TEST_TOKEN, "", 204) ||
      is_managed(1118200) ||
      is_managed(990080) ||
      request_config(
          port, "GET", TEST_TOKEN, 1118200,
          NULL, response, sizeof(response)) != 403
  ) {
    fputs("authorized empty registry did not remove managed apps\n", stderr);
    return 1;
  }

  (void)unlink(config_path);
  (void)rmdir(config_root);
  (void)handle;
  puts("native registry server harness: PASS");
  return 0;
}
