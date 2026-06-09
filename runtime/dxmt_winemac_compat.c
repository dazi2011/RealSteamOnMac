/*
 * DXMT compatibility bridge for the Wine 11 macOS driver.
 *
 * DXMT v0.80 understands an optional exported macdrv_functions table, but
 * its window-data view predates Wine's client-surface refactor. Keep Wine's
 * private structure private and return a short-lived legacy-shaped proxy.
 */

#if 0
#pragma makedep unix
#endif

#include "config.h"

#include <pthread.h>
#include <stdlib.h>

#include "macdrv.h"

struct dxmt_surface_entry
{
    macdrv_view view;
    macdrv_metal_view metal_view;
    struct macdrv_client_surface *surface;
    struct dxmt_surface_entry *next;
};

struct dxmt_legacy_win_data
{
    HWND hwnd;
    macdrv_window cocoa_window;
    macdrv_view cocoa_view;
    macdrv_view client_cocoa_view;
    struct macdrv_win_data *native;
    struct dxmt_surface_entry *surface_entry;
};

struct dxmt_macdrv_functions
{
    void (*init_display_devices)(BOOL force);
    struct macdrv_win_data *(*get_win_data)(HWND hwnd);
    void (*release_win_data)(struct macdrv_win_data *data);
    macdrv_window (*get_cocoa_window)(HWND hwnd, BOOL require_on_screen);
    macdrv_metal_device (*create_metal_device)(void);
    void (*release_metal_device)(macdrv_metal_device device);
    macdrv_metal_view (*create_metal_view)(macdrv_view view, macdrv_metal_device device);
    macdrv_metal_layer (*get_metal_layer)(macdrv_metal_view view);
    void (*release_metal_view)(macdrv_metal_view view);
    void (*on_main_thread)(void *block);
};

static pthread_mutex_t dxmt_surface_mutex = PTHREAD_MUTEX_INITIALIZER;
static struct dxmt_surface_entry *dxmt_surfaces;

static BOOL surface_entry_has_metal_view(struct dxmt_surface_entry *entry)
{
    BOOL result;

    pthread_mutex_lock(&dxmt_surface_mutex);
    result = entry->metal_view != NULL;
    pthread_mutex_unlock(&dxmt_surface_mutex);
    return result;
}

static void release_surface_entry(struct dxmt_surface_entry *entry)
{
    struct dxmt_surface_entry **cursor;

    if (!entry) return;

    pthread_mutex_lock(&dxmt_surface_mutex);
    for (cursor = &dxmt_surfaces; *cursor; cursor = &(*cursor)->next)
    {
        if (*cursor != entry) continue;
        *cursor = entry->next;
        break;
    }
    pthread_mutex_unlock(&dxmt_surface_mutex);

    client_surface_release(&entry->surface->client);
    free(entry);
}

static struct macdrv_win_data *dxmt_get_win_data(HWND hwnd)
{
    struct macdrv_win_data *native = get_win_data(hwnd);
    struct dxmt_legacy_win_data *legacy;
    struct dxmt_surface_entry *entry = NULL;

    if (!native) return NULL;
    if (!native->client_view)
    {
        struct macdrv_client_surface *surface;

        release_win_data(native);
        if (!(surface = macdrv_client_surface_create(hwnd))) return NULL;
        if (!(native = get_win_data(hwnd)))
        {
            client_surface_release(&surface->client);
            return NULL;
        }
        if (!(entry = malloc(sizeof(*entry))))
        {
            release_win_data(native);
            client_surface_release(&surface->client);
            return NULL;
        }
        entry->view = native->client_view
            ? native->client_view : surface->cocoa_view;
        entry->metal_view = NULL;
        entry->surface = surface;
        pthread_mutex_lock(&dxmt_surface_mutex);
        entry->next = dxmt_surfaces;
        dxmt_surfaces = entry;
        pthread_mutex_unlock(&dxmt_surface_mutex);
    }
    if (!(legacy = malloc(sizeof(*legacy))))
    {
        release_win_data(native);
        release_surface_entry(entry);
        return NULL;
    }

    legacy->hwnd = native->hwnd;
    legacy->cocoa_window = native->cocoa_window;
    legacy->cocoa_view = entry ? entry->view : native->client_view;
    legacy->client_cocoa_view = legacy->cocoa_view;
    legacy->native = native;
    legacy->surface_entry = entry;
    return (struct macdrv_win_data *)legacy;
}

static void dxmt_release_win_data(struct macdrv_win_data *data)
{
    struct dxmt_legacy_win_data *legacy = (struct dxmt_legacy_win_data *)data;

    if (!legacy) return;
    release_win_data(legacy->native);
    if (legacy->surface_entry
        && !surface_entry_has_metal_view(legacy->surface_entry))
        release_surface_entry(legacy->surface_entry);
    free(legacy);
}

static macdrv_metal_view dxmt_create_metal_view(
    macdrv_view view, macdrv_metal_device device)
{
    struct dxmt_surface_entry *entry;
    macdrv_metal_view metal_view;

    metal_view = macdrv_view_create_metal_view(view, device);
    if (!metal_view) return NULL;

    pthread_mutex_lock(&dxmt_surface_mutex);
    for (entry = dxmt_surfaces; entry; entry = entry->next)
    {
        if (entry->view != view || entry->metal_view) continue;
        entry->metal_view = metal_view;
        break;
    }
    pthread_mutex_unlock(&dxmt_surface_mutex);
    return metal_view;
}

static void dxmt_release_metal_view(macdrv_metal_view view)
{
    struct dxmt_surface_entry *entry;

    pthread_mutex_lock(&dxmt_surface_mutex);
    for (entry = dxmt_surfaces; entry; entry = entry->next)
        if (entry->metal_view == view) break;
    pthread_mutex_unlock(&dxmt_surface_mutex);

    macdrv_view_release_metal_view(view);
    release_surface_entry(entry);
}

__attribute__((visibility("default"), used))
struct dxmt_macdrv_functions macdrv_functions =
{
    NULL,
    dxmt_get_win_data,
    dxmt_release_win_data,
    macdrv_get_cocoa_window,
    macdrv_create_metal_device,
    macdrv_release_metal_device,
    dxmt_create_metal_view,
    macdrv_view_get_metal_layer,
    dxmt_release_metal_view,
    NULL,
};
