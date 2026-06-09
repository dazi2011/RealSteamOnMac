#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct macdrv_functions
{
    void (*init_display_devices)(int force);
    void *(*get_win_data)(void *hwnd);
    void (*release_win_data)(void *data);
    void *(*get_cocoa_window)(void *hwnd, int require_on_screen);
    void *(*create_metal_device)(void);
    void (*release_metal_device)(void *device);
    void *(*create_metal_view)(void *view, void *device);
    void *(*get_metal_layer)(void *view);
    void (*release_metal_view)(void *view);
    void (*on_main_thread)(void *block);
};

extern struct macdrv_functions macdrv_functions;

static const struct macdrv_functions *resolve_native_functions(void)
{
    static const struct macdrv_functions *functions;
    uint32_t index;

    if (functions) return functions;

    for (index = 0; index < _dyld_image_count(); ++index)
    {
        const char *path = _dyld_get_image_name(index);
        const char *name;
        void *handle;
        const struct macdrv_functions *candidate;

        if (!path) continue;
        name = strrchr(path, '/');
        name = name ? name + 1 : path;
        if (strcmp(name, "winemac.so")) continue;

        handle = dlopen(path, RTLD_LAZY | RTLD_NOLOAD);
        if (!handle) continue;
        candidate = dlsym(handle, "macdrv_functions");
        if (candidate && candidate != &macdrv_functions)
        {
            functions = candidate;
            return functions;
        }
    }
    return NULL;
}

static void *shim_get_win_data(void *hwnd)
{
    const struct macdrv_functions *functions = resolve_native_functions();

    return functions && functions->get_win_data
        ? functions->get_win_data(hwnd) : NULL;
}

static void shim_release_win_data(void *data)
{
    const struct macdrv_functions *functions = resolve_native_functions();

    if (functions && functions->release_win_data)
        functions->release_win_data(data);
}

static void *shim_create_metal_view(void *view, void *device)
{
    const struct macdrv_functions *functions = resolve_native_functions();

    return functions && functions->create_metal_view
        ? functions->create_metal_view(view, device) : NULL;
}

static void *shim_get_metal_layer(void *view)
{
    const struct macdrv_functions *functions = resolve_native_functions();

    return functions && functions->get_metal_layer
        ? functions->get_metal_layer(view) : NULL;
}

static void shim_release_metal_view(void *view)
{
    const struct macdrv_functions *functions = resolve_native_functions();

    if (functions && functions->release_metal_view)
        functions->release_metal_view(view);
}

__attribute__((visibility("default"), used))
struct macdrv_functions macdrv_functions =
{
    NULL,
    shim_get_win_data,
    shim_release_win_data,
    NULL,
    NULL,
    NULL,
    shim_create_metal_view,
    shim_get_metal_layer,
    shim_release_metal_view,
    NULL,
};
