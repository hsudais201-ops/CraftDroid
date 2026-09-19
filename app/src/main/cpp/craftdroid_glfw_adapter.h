#pragma once

#include <android/native_window.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Returns the current Android Surface as an ANativeWindow owned by CraftDroid. */
ANativeWindow* craftdroid_get_native_window();

/** Returns the current surface dimensions in physical pixels. */
void craftdroid_get_surface_size(int* width, int* height);

/** Polls one Android input event. Returns 1 when an event was returned. */
int craftdroid_poll_native_event(int* type, int* i, int* j, int* down,
                                 float* a, float* b, float* c, float* d);

/** EGL bridge used by an Android GLFW implementation. The functions operate
 * on the current ANativeWindow and are intended to be called from the same
 * thread that runs Minecraft/LWJGL. */
int craftdroid_egl_init();
int craftdroid_egl_make_current();
int craftdroid_egl_swap_buffers();
void craftdroid_egl_destroy();

/** Preflights the loaded native GLFW implementation against the Android Surface.
 * Returns 1 only when the Android Surface has a valid shared EGL context and
 * the current thread is bound to the bridge lifecycle. It intentionally does
 * not create a second desktop GLFW window.
 */
int craftdroid_glfw_prepare(int width, int height);
int craftdroid_glfw_make_current();
int craftdroid_glfw_swap_buffers();
void craftdroid_glfw_shutdown();

#ifdef __cplusplus
}
#endif
