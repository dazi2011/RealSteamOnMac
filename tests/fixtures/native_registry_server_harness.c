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

static int send_request(
    uint16_t port, const char *request, size_t request_length) {
  int connection = connect_with_retry(port);
  if (connection < 0) {
    fputs("could not connect to registry server\n", stderr);
    return -1;
  }
  if (!send_all(connection, request, request_length)) {
    close(connection);
    return -1;
  }

  char response[512];
  ssize_t received = recv(connection, response, sizeof(response) - 1, 0);
  close(connection);
  if (received <= 0) {
    return -1;
  }
  response[received] = '\0';

  int status = 0;
  if (sscanf(response, "HTTP/1.1 %d", &status) != 1) {
    return -1;
  }
  return status;
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
  if (
      setenv("REALSTEAMONMAC_REGISTRY_TOKEN", TEST_TOKEN, 1) != 0 ||
      setenv("REALSTEAMONMAC_REGISTRY_PORT", port_text, 1) != 0
  ) {
    perror("setenv");
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
      is_managed(990080)
  ) {
    fputs("authorized empty registry did not remove managed apps\n", stderr);
    return 1;
  }

  (void)handle;
  puts("native registry server harness: PASS");
  return 0;
}
