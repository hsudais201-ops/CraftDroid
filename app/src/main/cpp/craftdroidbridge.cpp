#include <jni.h>
#include <android/native_window_jni.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <android/log.h>
#include <android/input.h>
#include <mutex>
#include <future>
#include <memory>
#include <deque>
#include <cstdint>
#include <dlfcn.h>
#include <cstdlib>
#include <string>
#include <vector>
#include <map>
#include <optional>
#include <cstdio>
#include <thread>
#include <atomic>
#include <chrono>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <cerrno>

#define LOG_TAG "CraftDroidBridge"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

namespace {
std::mutex g_mutex;
ANativeWindow* g_window = nullptr;
int g_width = 0;
int g_height = 0;
std::atomic<uint64_t> g_surface_generation{0};
EGLDisplay g_egl_display = EGL_NO_DISPLAY;
EGLSurface g_egl_surface = EGL_NO_SURFACE;
EGLContext g_egl_context = EGL_NO_CONTEXT;
EGLConfig g_egl_config = nullptr;
int g_egl_client_version = 0;

struct InputEvent {
    int type; // 1 mouse, 2 key, 3 gamepad axis, 4 gamepad button, 5 scroll, 6 char
    float a, b, c, d;
    int i, j;
    bool down;

    InputEvent() noexcept = default;

    InputEvent(
        int eventType,
        float av,
        float bv,
        float cv,
        float dv,
        int code,
        int button,
        int modifiers,
        bool pressed
    ) noexcept
        : type(eventType), a(av), b(bv), c(cv), d(dv), i(code), j(0), down(pressed) {
        // Legacy JNI callers used different meanings for the two integer slots:
        // mouse=(pointer/code, button), key=(key, modifiers), gamepad=(axis/button, 0).
        if (eventType == 1) j = button;
        else if (eventType == 2) j = modifiers;
        else if (eventType == 4) i = button;
    }
};
std::deque<InputEvent> g_events;
constexpr size_t MAX_EVENTS = 2048;
std::atomic<bool> g_glfw_input_ready{false};
std::atomic<uint64_t> g_input_enqueued{0};
std::atomic<uint64_t> g_input_dequeued{0};
std::atomic<uint64_t> g_input_dropped{0};
std::atomic<uint64_t> g_input_coalesced{0};
std::string g_clipboard;

// Cache the embedded JVM CallbackBridge class from a Java-invoked JNI call.
// FindClass() from a native-created/attached thread can use the wrong class
// loader, so the input pump must dispatch through this global class reference.
jclass g_callback_bridge_class = nullptr;
jmethodID g_callback_bridge_receive = nullptr;

// The Android app and the embedded HotSpot JVM are different VMs. Input must
// therefore be dispatched from a thread attached to the embedded JVM, not
// from the Android/ART JNI thread. CallbackBridge.nativeSetInputReady() is
// called by the embedded JVM and gives us the correct JavaVM handle.
JavaVM* g_game_vm = nullptr;
std::thread g_input_pump;
std::mutex g_input_pump_lifecycle_mutex;
std::atomic<bool> g_input_pump_stop{true};
// Desired callback state survives Android Surface destruction/recreation.
// g_glfw_input_ready is the current live-pump state; this flag records whether
// Minecraft has requested the callback bridge to remain enabled.
std::atomic<bool> g_input_requested{false};
std::atomic<bool> g_java_running{false};
std::atomic<int> g_java_state{0};
std::atomic<uint64_t> g_render_frame_count{0};
std::atomic<int64_t> g_last_render_frame_ms{0}; // 0=IDLE, 1=STARTING, 2=RUNNING, 3=STOPPING, 4=EXITED
std::mutex g_java_launch_mutex;

// JLI_Launch needs a process-wide environment because the embedded HotSpot
// runtime reads JAVA_HOME/LD_LIBRARY_PATH directly. Preserve every variable
// CraftDroid changes and restore the caller's environment when the launch
// returns so a stopped Minecraft instance cannot poison the next launch.
class ScopedEnvironment {
public:
    explicit ScopedEnvironment(JNIEnv* env, jobjectArray environment) {
        captureKey("JAVA_HOME");
        captureKey("JLI_HOME");
        captureKey("LD_LIBRARY_PATH");
        if (!env || !environment) return;
        const jsize n = env->GetArrayLength(environment);
        for (jsize i = 0; i < n; ++i) {
            auto value = (jstring) env->GetObjectArrayElement(environment, i);
            if (!value) continue;
            const char* line = env->GetStringUTFChars(value, nullptr);
            if (line) {
                std::string entry(line);
                const auto eq = entry.find('=');
                if (eq != std::string::npos) captureKey(entry.substr(0, eq).c_str());
                env->ReleaseStringUTFChars(value, line);
            }
            env->DeleteLocalRef(value);
        }
    }

    ScopedEnvironment(const ScopedEnvironment&) = delete;
    ScopedEnvironment& operator=(const ScopedEnvironment&) = delete;

    ~ScopedEnvironment() {
        for (const auto& item : values_) {
            if (item.second.has_value()) setenv(item.first.c_str(), item.second->c_str(), 1);
            else unsetenv(item.first.c_str());
        }
    }

private:
    std::map<std::string, std::optional<std::string>> values_;

    void captureKey(const char* key) {
        if (!key || !*key) return;
        if (values_.find(key) != values_.end()) return;
        const char* value = std::getenv(key);
        values_[key] = value ? std::optional<std::string>(value) : std::nullopt;
    }
};

std::thread::id g_glfw_owner_thread;
bool g_glfw_owner_bound = false;


// Opaque GLFW 3 API loaded from the selected Android native stack. We resolve
// these symbols dynamically so CraftDroid never links against a desktop GLFW
// at build time. The Android GLFW implementation remains responsible for
// mapping its window/context to the ANativeWindow supplied by this bridge.
typedef int (*GlfwInitFn)();
typedef void (*GlfwTerminateFn)();
typedef void* (*GlfwCreateWindowFn)(int, int, const char*, void*, void*);
typedef void (*GlfwDestroyWindowFn)(void*);
typedef void (*GlfwMakeContextCurrentFn)(void*);
typedef void (*GlfwSwapBuffersFn)(void*);
typedef void (*GlfwPollEventsFn)();
typedef void (*GlfwSetWindowSizeFn)(void*, int, int);

void* g_glfw_handle = nullptr;
void* g_lwjgl_handle = nullptr;
std::string g_glfw_library_name;
std::string g_lwjgl_library_name;
void* g_glfw_window = nullptr;
GlfwInitFn g_glfwInit = nullptr;
GlfwTerminateFn g_glfwTerminate = nullptr;
GlfwCreateWindowFn g_glfwCreateWindow = nullptr;
GlfwDestroyWindowFn g_glfwDestroyWindow = nullptr;
GlfwMakeContextCurrentFn g_glfwMakeContextCurrent = nullptr;
GlfwSwapBuffersFn g_glfwSwapBuffers = nullptr;
GlfwPollEventsFn g_glfwPollEvents = nullptr;
GlfwSetWindowSizeFn g_glfwSetWindowSize = nullptr;

void pushLocked(const InputEvent& e) {
    // Caller must hold g_mutex.
    // High-frequency motion/axis events should never evict key/button events.
    // Coalesce with the newest matching motion event when possible.
    if ((e.type == 1 && e.j < 0) || e.type == 3) {
        if (!g_events.empty()) {
            InputEvent& last = g_events.back();
            const bool sameMouseMove = e.type == 1 && last.type == 1 && last.j < 0;
            const bool sameAxis = e.type == 3 && last.type == 3 && last.i == e.i;
            if (sameMouseMove || sameAxis) {
                last = e;
                g_input_coalesced.fetch_add(1, std::memory_order_relaxed);
                return;
            }
        }
    }

    if (g_events.size() >= MAX_EVENTS) {
        // Preserve discrete input whenever possible by evicting an older
        // motion/axis event first. Only drop the oldest event as a last resort.
        auto victim = g_events.end();
        for (auto it = g_events.begin(); it != g_events.end(); ++it) {
            if ((it->type == 1 && it->j < 0) || it->type == 3) {
                victim = it;
                break;
            }
        }
        if (victim != g_events.end()) g_events.erase(victim);
        else g_events.pop_front();
        g_input_dropped.fetch_add(1, std::memory_order_relaxed);
    }
    g_events.push_back(e);
    g_input_enqueued.fetch_add(1, std::memory_order_relaxed);
}

void push(const InputEvent& e) {
    std::lock_guard<std::mutex> lock(g_mutex);
    pushLocked(e);
}
}



void destroyEglLocked() {
    if (g_egl_display != EGL_NO_DISPLAY) {
        eglMakeCurrent(g_egl_display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        if (g_egl_surface != EGL_NO_SURFACE) eglDestroySurface(g_egl_display, g_egl_surface);
        if (g_egl_context != EGL_NO_CONTEXT) eglDestroyContext(g_egl_display, g_egl_context);
        eglTerminate(g_egl_display);
    }
    g_egl_display = EGL_NO_DISPLAY;
    g_egl_surface = EGL_NO_SURFACE;
    g_egl_context = EGL_NO_CONTEXT;
    g_egl_config = nullptr;
    g_egl_client_version = 0;
}

bool createEglLocked() {
    if (!g_window) return false;
    destroyEglLocked();
    g_egl_display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g_egl_display == EGL_NO_DISPLAY) return false;
    EGLint major = 0, minor = 0;
    if (!eglInitialize(g_egl_display, &major, &minor)) {
        destroyEglLocked();
        return false;
    }
    eglBindAPI(EGL_OPENGL_ES_API);
    const EGLint configAttrs[] = {
        EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT_KHR,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
        EGL_DEPTH_SIZE, 24, EGL_STENCIL_SIZE, 8,
        EGL_NONE
    };
    EGLint count = 0;
    if (!eglChooseConfig(g_egl_display, configAttrs, &g_egl_config, 1, &count) || count == 0) {
        const EGLint fallbackAttrs[] = {
            EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
            EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
            EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
            EGL_DEPTH_SIZE, 16, EGL_NONE
        };
        if (!eglChooseConfig(g_egl_display, fallbackAttrs, &g_egl_config, 1, &count) || count == 0) {
            destroyEglLocked();
            return false;
        }
        g_egl_client_version = 2;
    } else {
        g_egl_client_version = 3;
    }
    g_egl_surface = eglCreateWindowSurface(g_egl_display, g_egl_config,
                                            reinterpret_cast<EGLNativeWindowType>(g_window), nullptr);
    if (g_egl_surface == EGL_NO_SURFACE) {
        destroyEglLocked();
        return false;
    }
    const EGLint ctxAttrs3[] = {EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE};
    const EGLint ctxAttrs2[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    g_egl_context = eglCreateContext(g_egl_display, g_egl_config, EGL_NO_CONTEXT,
                                     g_egl_client_version == 3 ? ctxAttrs3 : ctxAttrs2);
    if (g_egl_context == EGL_NO_CONTEXT ||
        !eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context)) {
        destroyEglLocked();
        return false;
    }
    glViewport(0, 0, g_width, g_height);
    return true;
}

bool resolveGlfwApiLocked();

std::string prepareLaunchGraphicsLocked(int width, int height) {
    if (!g_window) return "FAIL: no Android Surface";
    if (width <= 0 || height <= 0 || width != g_width || height != g_height) {
        return "FAIL: surface dimensions changed";
    }
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE ||
        g_egl_context == EGL_NO_CONTEXT) {
        if (!createEglLocked()) {
            EGLint err = eglGetError();
            char buf[96];
            snprintf(buf, sizeof(buf), "FAIL: EGL create 0x%04x", err);
            return buf;
        }
    } else if (!eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context)) {
        EGLint err = eglGetError();
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: eglMakeCurrent 0x%04x", err);
        return buf;
    }
    glViewport(0, 0, width, height);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    glFinish();
    const GLenum glErr = glGetError();
    if (glErr != GL_NO_ERROR) {
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: GLES error 0x%04x", static_cast<unsigned>(glErr));
        return buf;
    }
    if (!eglSwapBuffers(g_egl_display, g_egl_surface)) {
        EGLint err = eglGetError();
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: eglSwapBuffers 0x%04x", err);
        return buf;
    }
    if (!resolveGlfwApiLocked()) return "FAIL: GLFW native API unavailable";
    return "OK: GRAPHICS_READY generation=" + std::to_string(g_surface_generation.load()) +
           " EGL=" + std::to_string(g_egl_client_version) +
           " size=" + std::to_string(width) + "x" + std::to_string(height);
}

bool resolveGlfwApiLocked() {
    if (!g_glfw_handle) {
        // Re-observe only the GLFW variant explicitly selected by the native
        // stack loader. The selection survives bridge shutdown so a later
        // render-thread call cannot silently bind the alternate ABI simply
        // because both libraries remain mapped in the process.
        if (g_glfw_library_name == "libglfw.so" || g_glfw_library_name == "libglfw3.so") {
            void* observed = dlopen(g_glfw_library_name.c_str(), RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
            if (observed) {
                g_glfw_handle = observed;
            }
        } else {
            const char* names[] = {"libglfw.so", "libglfw3.so"};
            for (const char* name : names) {
                void* observed = dlopen(name, RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
                if (observed) {
                    g_glfw_handle = observed;
                    g_glfw_library_name = name;
                    break;
                }
            }
        }
    }
    if (!g_glfw_handle) return false;
    g_glfwInit = reinterpret_cast<GlfwInitFn>(dlsym(g_glfw_handle, "glfwInit"));
    g_glfwTerminate = reinterpret_cast<GlfwTerminateFn>(dlsym(g_glfw_handle, "glfwTerminate"));
    g_glfwCreateWindow = reinterpret_cast<GlfwCreateWindowFn>(dlsym(g_glfw_handle, "glfwCreateWindow"));
    g_glfwDestroyWindow = reinterpret_cast<GlfwDestroyWindowFn>(dlsym(g_glfw_handle, "glfwDestroyWindow"));
    g_glfwMakeContextCurrent = reinterpret_cast<GlfwMakeContextCurrentFn>(dlsym(g_glfw_handle, "glfwMakeContextCurrent"));
    g_glfwSwapBuffers = reinterpret_cast<GlfwSwapBuffersFn>(dlsym(g_glfw_handle, "glfwSwapBuffers"));
    g_glfwPollEvents = reinterpret_cast<GlfwPollEventsFn>(dlsym(g_glfw_handle, "glfwPollEvents"));
    g_glfwSetWindowSize = reinterpret_cast<GlfwSetWindowSizeFn>(dlsym(g_glfw_handle, "glfwSetWindowSize"));
    return g_glfwInit && g_glfwTerminate && g_glfwCreateWindow &&
           g_glfwMakeContextCurrent && g_glfwSwapBuffers && g_glfwPollEvents;
}

extern "C" int craftdroid_glfw_prepare(int width, int height) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_window || width <= 0 || height <= 0) return 0;
    if (!resolveGlfwApiLocked()) return 0;

    // CraftDroid owns the Android ANativeWindow + EGL context. Never create a
    // second desktop-style GLFW window here: doing so can split the rendering
    // context from Minecraft's Android Surface. The Android GLFW Java stub is
    // responsible for binding LWJGL to the shared EGL handles passed by the
    // launcher.
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE ||
        g_egl_context == EGL_NO_CONTEXT) {
        if (!createEglLocked()) return 0;
    }
    if (eglGetCurrentContext() != g_egl_context &&
        !eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context)) {
        return 0;
    }

    // Do not bind the render owner on the Android UI thread. Minecraft/LWJGL
    // may initialize rendering on the embedded JVM thread. Bind ownership
    // lazily on the first actual make-current call instead.
    return 1;
}

extern "C" int craftdroid_glfw_make_current() {
    std::lock_guard<std::mutex> lock(g_mutex);
    const auto current = std::this_thread::get_id();
    if (!g_glfw_owner_bound) {
        g_glfw_owner_thread = current;
        g_glfw_owner_bound = true;
    }
    if (current != g_glfw_owner_thread) return 0;
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE ||
        g_egl_context == EGL_NO_CONTEXT) return 0;
    return eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context) ? 1 : 0;
}

extern "C" int craftdroid_glfw_swap_buffers() {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_glfw_owner_bound || std::this_thread::get_id() != g_glfw_owner_thread) return 0;
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE) return 0;
    const bool swapped = eglSwapBuffers(g_egl_display, g_egl_surface);
    if (swapped) {
        g_render_frame_count.fetch_add(1, std::memory_order_relaxed);
        const auto now = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        g_last_render_frame_ms.store(static_cast<int64_t>(now), std::memory_order_relaxed);
    }
    return swapped ? 1 : 0;
}

extern "C" void craftdroid_glfw_shutdown() {
    // Never tear down EGL/GLFW behind a live embedded Minecraft VM. JNI callers
    // can reach this entry point directly, bypassing the Kotlin lifecycle gate,
    // so keep the native state machine as the final safety boundary. State 4
    // (EXITED) and state 0 (IDLE/uninitialized) are safe for teardown.
    const int javaState = g_java_state.load(std::memory_order_acquire);
    if (javaState != 0 && javaState != 4) {
        LOGI("GLFW shutdown ignored while embedded JVM lifecycle state=%d", javaState);
        return;
    }

    // A full native GLFW shutdown is terminal for the current callback pipe.
    // Clear both the live and requested input states before joining the pump
    // so a concurrent surface transition cannot resurrect it after teardown.
    g_input_requested.store(false, std::memory_order_release);
    g_glfw_input_ready.store(false, std::memory_order_release);
    // Input pump teardown is handled by the embedded JVM lifecycle gate.
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_glfw_window && g_glfwDestroyWindow) g_glfwDestroyWindow(g_glfw_window);
    g_glfw_window = nullptr;
    if (g_glfwTerminate) g_glfwTerminate();
    g_glfw_owner_bound = false;
    g_glfw_owner_thread = std::thread::id{};
    g_glfwInit = nullptr;
    g_glfwTerminate = nullptr;
    g_glfwCreateWindow = nullptr;
    g_glfwDestroyWindow = nullptr;
    g_glfwMakeContextCurrent = nullptr;
    g_glfwSwapBuffers = nullptr;
    g_glfwPollEvents = nullptr;
    g_glfwSetWindowSize = nullptr;
    // Keep the selected GLFW handle pinned for the life of the process. The
    // embedded Minecraft/LWJGL VM may retain JNI/native function pointers
    // after the bridge shutdown callback returns; dlclose() here can turn
    // those pointers into use-after-unload crashes. Keep the handle itself
    // available so a later surface generation can re-resolve the same ABI
    // without probing the alternate GLFW implementation.
    // The function pointers above are intentionally cleared because the GLFW
    // state may have been terminated; resolveGlfwApiLocked() repopulates them
    // from this exact pinned handle before a subsequent prepare/make-current.
}

void deliverToGlfw(JNIEnv* env, const InputEvent& e) {
    if (!g_glfw_input_ready.load(std::memory_order_acquire)) return;
    jclass cls = nullptr;
    jmethodID receive = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        if (g_callback_bridge_class && g_callback_bridge_receive) {
            // Take a local reference while the global reference is protected.
            // The input-pump shutdown path may delete the global reference
            // immediately after this lock is released, so retaining only the
            // raw global handle here can race with DeleteGlobalRef().
            cls = reinterpret_cast<jclass>(env->NewLocalRef(g_callback_bridge_class));
            if (!cls && env->ExceptionCheck()) {
                // A failed local-reference allocation (for example under JNI
                // memory pressure) must not leak a pending exception into the
                // Minecraft input callback path. The event is dropped safely
                // and the next event gets another chance.
                env->ExceptionClear();
            }
            receive = g_callback_bridge_receive;
        }
    }
    if (!cls || !receive) {
        if (cls) env->DeleteLocalRef(cls);
        return;
    }
    int type = 0, i1 = 0, i2 = 0, i3 = 0, i4 = 0;
    switch (e.type) {
        case 1: // mouse: a=x b=y c=dx d=dy, i=unused, j=button
            if (e.j >= 0) {
                type = 1006; i1 = e.j; i2 = e.down ? 1 : 0;
            } else {
                type = 1003; i1 = static_cast<int>(e.a); i2 = static_cast<int>(e.b);
            }
            break;
        case 2: // key
            type = 1005; i1 = e.i; i2 = e.down ? 1 : 0; i3 = static_cast<int>(e.a);
            break;
        case 3: // Gamepad axis. Use the same callback pipe with a dedicated type.
            type = 1010; i1 = e.i; i2 = static_cast<int>(e.a * 1000.0f);
            break;
        case 4: // gamepad button -> key-like event for compatibility
            type = 1005; i1 = 320 + e.i; i2 = e.down ? 1 : 0;
            break;
        case 5: // scroll: GLFW scroll event
            type = 1007; i1 = static_cast<int>(e.a * 1000.0f); i2 = static_cast<int>(e.b * 1000.0f);
            break;
        case 6: // Unicode character input
            type = 1000; i1 = e.i; i2 = 0;
            break;
        default: return;
    }
    env->CallStaticVoidMethod(cls, receive, type, i1, i2, i3, i4);
    if (env->ExceptionCheck()) env->ExceptionClear();
    env->DeleteLocalRef(cls);
}

void flushGlfwEvents(JNIEnv* env) {
    while (true) {
        InputEvent e{};
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            if (g_events.empty()) break;
            e = g_events.front();
            g_events.pop_front();
            g_input_dequeued.fetch_add(1, std::memory_order_relaxed);
        }
        deliverToGlfw(env, e);
    }
}

void stopInputPump(bool clearPendingEvents = false) {
    std::lock_guard<std::mutex> lifecycleLock(g_input_pump_lifecycle_mutex);
    g_input_pump_stop.store(true);
    if (g_input_pump.joinable()) {
        if (std::this_thread::get_id() == g_input_pump.get_id()) {
            // A pump-thread caller must never detach itself. Detaching would
            // let the thread outlive native state and makes later lifecycle
            // cleanup race with its final callbacks. The stop flag is enough
            // to request shutdown; a non-pump caller will perform the join.
            LOGI("input pump stop requested from pump thread; deferring join");
            return;
        } else {
            g_input_pump.join();
        }
    }
    if (clearPendingEvents) {
        std::lock_guard<std::mutex> lock(g_mutex);
        const auto dropped = static_cast<uint64_t>(g_events.size());
        g_events.clear();
        if (dropped) g_input_dropped.fetch_add(dropped, std::memory_order_relaxed);
    }
}

bool startInputPump() {
    std::lock_guard<std::mutex> lifecycleLock(g_input_pump_lifecycle_mutex);
    g_input_pump_stop.store(true);
    if (g_input_pump.joinable()) {
        if (std::this_thread::get_id() == g_input_pump.get_id()) {
            // The caller is the pump thread itself. It cannot join itself;
            // leave shutdown to the pump loop and report failure to the caller.
            return false;
        }
        g_input_pump.join();
    }
    g_input_pump_stop.store(false);
    auto startup = std::make_shared<std::promise<bool>>();
    auto startupFuture = startup->get_future();
    g_input_pump = std::thread([startup]() {
        JavaVM* vm = nullptr;
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            vm = g_game_vm;
        }
        // A callback request can outlive a Surface transition, but it must not
        // resurrect an input thread after JLI_Launch has already terminated.
        // Gate startup on the live embedded-JVM state as well as the VM handle.
        if (!vm || !g_java_running.load(std::memory_order_acquire)) {
            startup->set_value(false);
            return;
        }
        JNIEnv* env = nullptr;
        bool attached = false;
        if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) {
#if defined(__ANDROID__)
            if (vm->AttachCurrentThread(&env, nullptr) != JNI_OK) { startup->set_value(false); return; }
#else
            if (vm->AttachCurrentThread(reinterpret_cast<void**>(&env), nullptr) != JNI_OK) { startup->set_value(false); return; }
#endif
            attached = true;
        }
        auto failStartup = [&]() {
            {
                std::lock_guard<std::mutex> lock(g_mutex);
                if (g_callback_bridge_class && env) {
                    env->DeleteGlobalRef(g_callback_bridge_class);
                    g_callback_bridge_class = nullptr;
                    g_callback_bridge_receive = nullptr;
                }
            }
            if (attached) vm->DetachCurrentThread();
            startup->set_value(false);
        };
        // A surface transition stops the old pump, which releases the cached
        // CallbackBridge global reference. Re-cache it from this active embedded
        // JVM before declaring the restarted dispatcher ready.
        bool callbackReady = false;
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            if (!g_callback_bridge_class && env) {
                jclass localClass = env->FindClass("org/lwjgl/glfw/CallbackBridge");
                if (localClass) {
                    jmethodID receive = env->GetStaticMethodID(localClass, "receiveCallback", "(IIIII)V");
                    if (receive) {
                        jclass globalClass = reinterpret_cast<jclass>(env->NewGlobalRef(localClass));
                        if (globalClass) {
                            g_callback_bridge_class = globalClass;
                            g_callback_bridge_receive = receive;
                        }
                    } else {
                        env->ExceptionClear();
                    }
                    env->DeleteLocalRef(localClass);
                } else {
                    env->ExceptionClear();
                }
            }
            callbackReady = g_callback_bridge_class && g_callback_bridge_receive;
        }
        if (!callbackReady) {
            failStartup();
            return;
        }
        startup->set_value(true);

        while (!g_input_pump_stop.load(std::memory_order_acquire)) {
            // Snapshot the optional GLFW poll function under the mutex, then call
            // it without the mutex held. GLFW callbacks may re-enter CraftDroid JNI.
            GlfwPollEventsFn poll = nullptr;
            void* glfwWindow = nullptr;
            bool inputReady = false;
            bool pollAllowed = false;
            {
                std::lock_guard<std::mutex> lock(g_mutex);
                inputReady = g_glfw_input_ready.load(std::memory_order_acquire);
                poll = g_glfwPollEvents;
                glfwWindow = g_glfw_window;
                // GLFW event processing is not generally thread-safe and the
                // render/context owner is established by craftdroid_glfw_make_current().
                // Only poll from that owner thread. The Android input queue is
                // still flushed below, so callbacks do not depend on violating
                // GLFW's thread-affinity rules.
                pollAllowed = !g_glfw_owner_bound ||
                        std::this_thread::get_id() == g_glfw_owner_thread;
            }
            if (inputReady && poll && glfwWindow && pollAllowed) poll();
            bool readyAfterPoll = false;
            {
                std::lock_guard<std::mutex> lock(g_mutex);
                readyAfterPoll = g_glfw_input_ready.load(std::memory_order_acquire);
            }
            if (readyAfterPoll) flushGlfwEvents(env);
            std::this_thread::sleep_for(std::chrono::milliseconds(8));
        }

        // The pump is no longer able to dispatch callbacks. Publish that fact
        // before releasing the cached JNI reference so Java cannot observe a
        // stale "ready" state and enqueue more work for a dead dispatcher.
        // Keep g_input_requested unchanged here: a Surface transition may have
        // intentionally stopped this pump while Minecraft still wants input,
        // and nativeSetSurface() will recreate it for the replacement surface.
        g_glfw_input_ready.store(false, std::memory_order_release);

        // The cached CallbackBridge class belongs to this embedded JVM. Once
        // the input pump is gone, release the global reference so the next
        // callback session can cache a fresh class reference from the active
        // JVM/class loader instead of retaining a stale loader object.
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            if (g_callback_bridge_class && env) {
                env->DeleteGlobalRef(g_callback_bridge_class);
                g_callback_bridge_class = nullptr;
                g_callback_bridge_receive = nullptr;
            }
        }
        if (attached) vm->DetachCurrentThread();
    });
    return startupFuture.get();
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativeValidateNativeStack(JNIEnv* env, jclass, jstring directory, jboolean preferLwjgl3, jstring selectedGlfwName) {
    if (!directory) return env->NewStringUTF("FAIL: no native directory");
    const char* dir = env->GetStringUTFChars(directory, nullptr);
    if (!dir) return env->NewStringUTF("FAIL: invalid native directory");

    // Validate the same GLFW handle selected by loadNativeStack(). Do not
    // dlopen a candidate here: doing so could load the alternate GLFW ABI
    // after the loader already chose another implementation.
    std::string selectedGlfw;
    if (selectedGlfwName) {
        const char* name = env->GetStringUTFChars(selectedGlfwName, nullptr);
        if (name) { selectedGlfw = name; env->ReleaseStringUTFChars(selectedGlfwName, name); }
    }
    void* glfw = nullptr;
    std::string loadedGlfwName;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        glfw = g_glfw_handle;
        loadedGlfwName = g_glfw_library_name;
    }
    std::string result;
    if (!glfw) {
        // The stack loader must have recorded the selected GLFW handle before
        // validation. Do not rediscover it from the filesystem here.
        result = "FAIL: selected GLFW handle is not loaded";
    } else if (selectedGlfw.empty() || loadedGlfwName != selectedGlfw) {
        result = "FAIL: GLFW selection mismatch selected=" + selectedGlfw + " loaded=" + (loadedGlfwName.empty() ? "UNKNOWN" : loadedGlfwName);
    } else {
        const char* symbols[] = {
            "glfwInit", "glfwTerminate", "glfwCreateWindow",
            "glfwMakeContextCurrent", "glfwSwapBuffers", "glfwPollEvents"
        };
        int found = 0;
        for (const char* symbol : symbols) {
            if (dlsym(glfw, symbol)) ++found;
        }
        result = "GLFW=" + std::to_string(found) + "/" + std::to_string(sizeof(symbols)/sizeof(symbols[0]));

        const char* selectedName = preferLwjgl3 ? "liblwjgl3.so" : "liblwjgl.so";
        void* lwjgl = nullptr;
        std::string loadedLwjglName;
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            lwjgl = g_lwjgl_handle;
            loadedLwjglName = g_lwjgl_library_name;
        }
        if (!lwjgl) {
            // The native stack loader is the sole authority for LWJGL
            // selection. Validation must never rediscover or reopen a JNI
            // library, even with RTLD_NOLOAD, because the process may contain
            // multiple ABI-compatible filenames.
            result = std::string("GLFW=") + std::to_string(found) + "/6 LWJGL=" + selectedName + ":NOT_LOADED";
            env->ReleaseStringUTFChars(directory, dir);
            return env->NewStringUTF(("FAIL: " + result).c_str());
        }
        if (loadedLwjglName != selectedName) {
            result += std::string(" LWJGL=") + selectedName +
                "=LOADED_AS_" + (loadedLwjglName.empty() ? "UNKNOWN" : loadedLwjglName);
            env->ReleaseStringUTFChars(directory, dir);
            return env->NewStringUTF(("FAIL: " + result).c_str());
        }
        result += std::string(" LWJGL=") + selectedName +
            (dlsym(lwjgl, "JNI_OnLoad") ? ":JNI" : ":NO_JNI_OnLoad");

        std::lock_guard<std::mutex> lock(g_mutex);
        result += g_window ? " SURFACE=READY" : " SURFACE=NONE";
        result += " SIZE=" + std::to_string(g_width) + "x" + std::to_string(g_height);
        if (found != 6) result = "FAIL: " + result;
    }

    env->ReleaseStringUTFChars(directory, dir);
    return env->NewStringUTF(result.c_str());
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativeValidateGlfwHandshake(JNIEnv* env, jclass, jboolean requireCallbackBridge, jboolean preferLwjgl3, jstring selectedGlfwName) {
    // This check intentionally does not call craftdroid_glfw_prepare(): doing
    // so would bind GLFW ownership to the launcher thread before Minecraft's
    // render thread starts. We only inspect the already-loaded process ABI.
    std::lock_guard<std::mutex> lock(g_mutex);
    std::string expectedGlfw;
    if (selectedGlfwName) {
        const char* name = env->GetStringUTFChars(selectedGlfwName, nullptr);
        if (name) { expectedGlfw = name; env->ReleaseStringUTFChars(selectedGlfwName, name); }
    }
    if (expectedGlfw != "libglfw.so" && expectedGlfw != "libglfw3.so") {
        return env->NewStringUTF("FAIL: invalid selected GLFW library");
    }
    if (!g_glfw_handle) {
        return env->NewStringUTF("FAIL: selected GLFW handle is not loaded");
    }
    if (g_glfw_library_name != expectedGlfw) {
        std::string mismatch = "FAIL: GLFW selection mismatch selected=" + expectedGlfw +
            " loaded=" + (g_glfw_library_name.empty() ? "UNKNOWN" : g_glfw_library_name);
        return env->NewStringUTF(mismatch.c_str());
    }

    const char* glfwSymbols[] = {
        "glfwInit", "glfwTerminate", "glfwCreateWindow",
        "glfwMakeContextCurrent", "glfwGetCurrentContext",
        "glfwSwapBuffers", "glfwPollEvents", "glfwSetWindowSize"
    };
    int glfwFound = 0;
    for (const char* symbol : glfwSymbols) {
        if (dlsym(g_glfw_handle, symbol)) ++glfwFound;
    }

    // Current Android LWJGL packages may expose either liblwjgl.so or
    // liblwjgl3.so. Validate whichever binary was actually loaded instead of
    // assuming the legacy filename.
    void* lwjgl = g_lwjgl_handle;
    const char* selectedLwjglName = preferLwjgl3 ? "liblwjgl3.so" : "liblwjgl.so";
    if (!lwjgl) {
        return env->NewStringUTF("FAIL: selected LWJGL handle is not loaded");
    }
    int lwjglJni = dlsym(lwjgl, "JNI_OnLoad") ? 1 : 0;

    // CallbackBridge is the Java -> native input/cursor/clipboard contract.
    // Verify the JNI exports directly so a stale callback-patch JAR cannot
    // silently call methods that no longer exist in this native bridge.
    const char* callbackSymbols[] = {
        "Java_org_lwjgl_glfw_CallbackBridge_nativeSendData",
        "Java_org_lwjgl_glfw_CallbackBridge_nativeSetInputReady",
        "Java_org_lwjgl_glfw_CallbackBridge_nativeClipboard",
        "Java_org_lwjgl_glfw_CallbackBridge_nativeSetGrabbing"
    };
    int callbackFound = 0;
    void* self = dlopen("libcraftdroidbridge.so", RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
    if (!self) self = dlopen("libcraftdroidbridge.so", RTLD_NOW | RTLD_GLOBAL);
    for (const char* symbol : callbackSymbols) {
        if (self && dlsym(self, symbol)) ++callbackFound;
    }

    std::string result = "GLFW=" + expectedGlfw + "=" + std::to_string(glfwFound) + "/" +
        std::to_string(sizeof(glfwSymbols) / sizeof(glfwSymbols[0]));
    result += " LWJGL=" + std::string(selectedLwjglName ? selectedLwjglName : "NONE") + " JNI=" + std::to_string(lwjglJni);
    result += " CALLBACK_JNI=" + std::to_string(callbackFound) + "/" +
        std::to_string(sizeof(callbackSymbols) / sizeof(callbackSymbols[0]));
    result += g_window ? " SURFACE=READY" : " SURFACE=NONE";
    if (glfwFound != static_cast<int>(sizeof(glfwSymbols) / sizeof(glfwSymbols[0]))) {
        return env->NewStringUTF(("FAIL: " + result).c_str());
    }
    if (!lwjglJni) {
        return env->NewStringUTF(("FAIL: " + result + " LWJGL has no JNI_OnLoad").c_str());
    }
    if (requireCallbackBridge && callbackFound != static_cast<int>(sizeof(callbackSymbols) / sizeof(callbackSymbols[0]))) {
        return env->NewStringUTF(("FAIL: " + result + " callback JNI contract incomplete").c_str());
    }
    if (!requireCallbackBridge && callbackFound != 0 && callbackFound != static_cast<int>(sizeof(callbackSymbols) / sizeof(callbackSymbols[0]))) {
        LOGI("Optional CallbackBridge JNI exports are partially present (%d/%zu); native GLFW mode does not require them", callbackFound, sizeof(callbackSymbols) / sizeof(callbackSymbols[0]));
    }
    result += requireCallbackBridge ? " CALLBACK_REQUIRED=1" : " CALLBACK_REQUIRED=0";
    return env->NewStringUTF(("OK: " + result).c_str());
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeLoadLibrary(JNIEnv* env, jclass, jstring path) {
    if (!path) return JNI_FALSE;
    const char* p = env->GetStringUTFChars(path, nullptr);
    if (!p) return JNI_FALSE;

    // Determine the basename before calling dlopen. Native libraries are
    // process-global; rejecting an incompatible GLFW/LWJGL family *after*
    // dlopen would already have inserted the alternate ABI into the process.
    const std::string loadedPath(p);
    const auto slash = loadedPath.find_last_of('/');
    const std::string base = slash == std::string::npos ? loadedPath : loadedPath.substr(slash + 1);
    const bool isGlfw = base == "libglfw.so" || base == "libglfw3.so";
    const bool isLwjgl = base == "liblwjgl.so" || base == "liblwjgl3.so";
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        if (isGlfw && !g_glfw_library_name.empty() && g_glfw_library_name != base) {
            LOGI("Rejecting GLFW ABI switch before dlopen from %s to %s", g_glfw_library_name.c_str(), base.c_str());
            env->ReleaseStringUTFChars(path, p);
            return JNI_FALSE;
        }
        if (isLwjgl && !g_lwjgl_library_name.empty() && g_lwjgl_library_name != base) {
            LOGI("Rejecting LWJGL ABI switch before dlopen from %s to %s", g_lwjgl_library_name.c_str(), base.c_str());
            env->ReleaseStringUTFChars(path, p);
            return JNI_FALSE;
        }
    }

    void* handle = dlopen(p, RTLD_NOW | RTLD_GLOBAL);
    if (!handle) {
        LOGI("dlopen failed for %s: %s", p, dlerror());
        env->ReleaseStringUTFChars(path, p);
        return JNI_FALSE;
    }
    LOGI("dlopen global: %s", p);

    // Remember the exact GLFW/LWJGL handle that was loaded. Upstream packages
    // may use either filename, and validation must use the library actually
    // selected by the Kotlin loader rather than rediscovering a variant.
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        if (isGlfw) {
            g_glfw_handle = handle;
            g_glfw_library_name = base;
        } else if (isLwjgl) {
            g_lwjgl_handle = handle;
            g_lwjgl_library_name = base;
        }
    }

    env->ReleaseStringUTFChars(path, p);
    return JNI_TRUE;
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativeInitEgl(JNIEnv* env, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_window) return env->NewStringUTF("FAIL: no Android Surface");
    if (!createEglLocked()) {
        EGLint err = eglGetError();
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: EGL init error 0x%04x", err);
        return env->NewStringUTF(buf);
    }
    const char* vendor = reinterpret_cast<const char*>(glGetString(GL_VENDOR));
    const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    const char* version = reinterpret_cast<const char*>(glGetString(GL_VERSION));
    std::string out = "EGL=" + std::to_string(g_egl_client_version);
    out += " vendor=" + std::string(vendor ? vendor : "unknown");
    out += " renderer=" + std::string(renderer ? renderer : "unknown");
    out += " version=" + std::string(version ? version : "unknown");
    return env->NewStringUTF(out.c_str());
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeEglMakeCurrent(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return g_egl_display != EGL_NO_DISPLAY &&
           g_egl_surface != EGL_NO_SURFACE &&
           g_egl_context != EGL_NO_CONTEXT &&
           eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context);
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeEglSwapBuffers(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE) return JNI_FALSE;
    return eglSwapBuffers(g_egl_display, g_egl_surface) ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeDestroyEgl(JNIEnv*, jclass) {
    // EGL is part of the same live render state as GLFW. Reject direct JNI
    // teardown while the embedded Minecraft JVM is STARTING/RUNNING/STOPPING;
    // otherwise a late Surface callback could invalidate the game render
    // context even though the GLFW shutdown entry point is already protected.
    const int javaState = g_java_state.load(std::memory_order_acquire);
    if (javaState != 0 && javaState != 4) {
        LOGI("EGL destroy ignored while embedded JVM lifecycle state=%d", javaState);
        return;
    }
    std::lock_guard<std::mutex> lock(g_mutex);
    destroyEglLocked();
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetEglDisplay(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return reinterpret_cast<jlong>(g_egl_display);
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetEglContext(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return reinterpret_cast<jlong>(g_egl_context);
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetEglSurfaceRead(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return reinterpret_cast<jlong>(g_egl_surface);
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetEglSurfaceDraw(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return reinterpret_cast<jlong>(g_egl_surface);
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativeValidateEglFrame(JNIEnv* env, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE ||
        g_egl_context == EGL_NO_CONTEXT) {
        return env->NewStringUTF("FAIL: EGL handles unavailable");
    }
    if (!eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context)) {
        EGLint err = eglGetError();
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: eglMakeCurrent 0x%04x", err);
        return env->NewStringUTF(buf);
    }
    const auto beforeError = eglGetError();
    (void)beforeError;
    glViewport(0, 0, g_width > 0 ? g_width : 1, g_height > 0 ? g_height : 1);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    glFinish();
    const GLenum glErr = glGetError();
    if (glErr != GL_NO_ERROR) {
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: GLES error 0x%04x", static_cast<unsigned>(glErr));
        return env->NewStringUTF(buf);
    }
    if (!eglSwapBuffers(g_egl_display, g_egl_surface)) {
        EGLint err = eglGetError();
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: eglSwapBuffers 0x%04x", err);
        return env->NewStringUTF(buf);
    }
    const char* version = reinterpret_cast<const char*>(glGetString(GL_VERSION));
    const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    std::string result = "OK: frame=1 size=" + std::to_string(g_width) + "x" +
        std::to_string(g_height) + " GLES=" + (version ? version : "unknown") +
        " renderer=" + (renderer ? renderer : "unknown");
    return env->NewStringUTF(result.c_str());
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativeValidateOpenGlBootstrap(JNIEnv* env, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE ||
        g_egl_context == EGL_NO_CONTEXT) {
        return env->NewStringUTF("FAIL: EGL handles unavailable");
    }
    if (!eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context)) {
        EGLint err = eglGetError();
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: eglMakeCurrent 0x%04x", err);
        return env->NewStringUTF(buf);
    }

    const char* version = reinterpret_cast<const char*>(glGetString(GL_VERSION));
    const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    const char* vendor = reinterpret_cast<const char*>(glGetString(GL_VENDOR));
    const char* extensions = reinterpret_cast<const char*>(glGetString(GL_EXTENSIONS));
    if (!version || !renderer || !vendor) {
        return env->NewStringUTF("FAIL: OpenGL ES capability strings unavailable");
    }

    GLint maxTexture = 0;
    GLint maxTextureUnits = 0;
    GLint maxViewport[2] = {0, 0};
    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &maxTexture);
    glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS, &maxTextureUnits);
    glGetIntegerv(GL_MAX_VIEWPORT_DIMS, maxViewport);
    const GLenum err = glGetError();
    if (err != GL_NO_ERROR) {
        char buf[96];
        snprintf(buf, sizeof(buf), "FAIL: GLES capability query error 0x%04x", static_cast<unsigned>(err));
        return env->NewStringUTF(buf);
    }

    const std::string ext = extensions ? extensions : "";
    const bool hasFramebuffer = ext.find("GL_OES_framebuffer_object") != std::string::npos ||
                                ext.find("GL_EXT_framebuffer_object") != std::string::npos ||
                                ext.find("GL_ANGLE_framebuffer_blit") != std::string::npos;
    const bool hasTextureFloat = ext.find("GL_OES_texture_float") != std::string::npos ||
                                 ext.find("GL_EXT_color_buffer_float") != std::string::npos;

    std::string out = "OK: GLES_BOOTSTRAP";
    out += " version=" + std::string(version);
    out += " vendor=" + std::string(vendor);
    out += " renderer=" + std::string(renderer);
    out += " maxTexture=" + std::to_string(maxTexture);
    out += " textureUnits=" + std::to_string(maxTextureUnits);
    out += " viewport=" + std::to_string(maxViewport[0]) + "x" + std::to_string(maxViewport[1]);
    out += " fboExt=" + std::to_string(hasFramebuffer ? 1 : 0);
    out += " floatTexExt=" + std::to_string(hasTextureFloat ? 1 : 0);
    return env->NewStringUTF(out.c_str());
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativePrepareLaunchGraphics(JNIEnv* env, jclass, jint width, jint height) {
    std::lock_guard<std::mutex> lock(g_mutex);
    const std::string result = prepareLaunchGraphicsLocked(width, height);
    return env->NewStringUTF(result.c_str());
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetSurfaceGeneration(JNIEnv*, jclass) {
    return static_cast<jlong>(g_surface_generation.load());
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeGlfwPrepare(JNIEnv*, jclass, jint width, jint height) {
    return craftdroid_glfw_prepare(width, height) ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeGlfwMakeCurrent(JNIEnv*, jclass) {
    return craftdroid_glfw_make_current() ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeGlfwSwapBuffers(JNIEnv*, jclass) {
    return craftdroid_glfw_swap_buffers() ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetRenderFrameCount(JNIEnv*, jclass) {
    return static_cast<jlong>(g_render_frame_count.load(std::memory_order_relaxed));
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetLastRenderFrameTimeMs(JNIEnv*, jclass) {
    return static_cast<jlong>(g_last_render_frame_ms.load(std::memory_order_relaxed));
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeGlfwShutdown(JNIEnv*, jclass) {
    craftdroid_glfw_shutdown();
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeSetSurface(JNIEnv* env, jclass, jobject surface, jint width, jint height) {
    // Kotlin normally defers Surface changes while Minecraft is running. Keep a
    // native guard as the final safety boundary: a late/duplicate Android
    // callback must never destroy the EGL/GLFW objects belonging to the live
    // embedded JVM. Also cover the STARTING/STOPPING states where
    // g_java_running may not yet reflect the full lifecycle transition. State 4
    // (EXITED) is terminal and safe for cleanup/replacement.
    const int javaState = g_java_state.load(std::memory_order_acquire);
    if (javaState != 0 && javaState != 4) {
        LOGI("surface change ignored while embedded JVM lifecycle state=%d; Java layer will defer it", javaState);
        return;
    }

    // Stop the input pump before destroying/replacing the GLFW window.
    // Remember the requested callback state separately from the live pump.
    // Surface destruction turns the live state off, but a recreated surface
    // must restore the dispatcher when Minecraft previously requested it.
    const bool restartInput = g_input_requested.load(std::memory_order_acquire);
    // Events captured for the old Android Surface must never leak into the
    // replacement Surface. A rotation/activity recreation can otherwise
    // replay stale touch/key events after the new GLFW context is ready.
    stopInputPump(true);
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        if (g_glfw_window && g_glfwDestroyWindow) g_glfwDestroyWindow(g_glfw_window);
        g_glfw_window = nullptr;
        destroyEglLocked();
        if (g_window) {
            ANativeWindow_release(g_window);
            g_window = nullptr;
        }
        if (surface) g_window = ANativeWindow_fromSurface(env, surface);
        g_width = width;
        g_height = height;
        // A surface replacement destroys the EGL context/surface that belonged
        // to the previous render owner. The next Minecraft render-thread call
        // must be allowed to claim ownership for the new context. Keeping the
        // old thread id here would make craftdroid_glfw_make_current() reject
        // a legitimate render thread after rotation/activity recreation.
        g_glfw_owner_bound = false;
        g_glfw_owner_thread = std::thread::id{};
        g_surface_generation.fetch_add(1);
        // Surface dimensions are authoritative through the surface-query API;
        // never encode a resize as mouse motion.
        LOGI("surface=%p size=%dx%d", g_window, g_width, g_height);
        g_glfw_input_ready.store(false, std::memory_order_release);
    }
    // Recreate the callback/input dispatcher whenever it was active before the
    // surface transition. Keeping this outside g_mutex avoids the startup path
    // deadlocking while it snapshots g_game_vm and callback state.
    bool hasSurface = false;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        hasSurface = g_window != nullptr;
    }
    if (restartInput && hasSurface) {
        if (!startInputPump()) {
            LOGI("surface input restart failed; leaving callback pipe disabled");
            g_glfw_input_ready.store(false, std::memory_order_release);
        } else {
            g_glfw_input_ready.store(true, std::memory_order_release);
        }
    }
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_game_NativeGameBridge_nativeGetSurfaceHandle(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return reinterpret_cast<jlong>(g_window);
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_game_NativeGameBridge_nativeGetSurfaceWidth(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return g_width;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_game_NativeGameBridge_nativeGetSurfaceHeight(JNIEnv*, jclass) {
    std::lock_guard<std::mutex> lock(g_mutex);
    return g_height;
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeMouse(JNIEnv*, jclass, jfloat x, jfloat y,
                                                    jfloat dx, jfloat dy, jint button, jboolean down) {
    push({1, x, y, dx, dy, 0, button, 0, static_cast<bool>(down)});
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeMouseScroll(JNIEnv*, jclass, jfloat horizontal, jfloat vertical) {
    if (horizontal == 0.0f && vertical == 0.0f) return;
    push({5, vertical, horizontal, 0, 0, 0, -1, 0, false});
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeKey(JNIEnv*, jclass, jint key, jboolean down, jint modifiers) {
    push({2, static_cast<float>(modifiers), 0, 0, 0, key, 0, 0, static_cast<bool>(down)});
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeGamepadAxis(JNIEnv*, jclass, jint axis, jfloat value) {
    push({3, value, 0, 0, 0, axis, 0, 0, true});
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeGamepadButton(JNIEnv*, jclass, jint button, jboolean down) {
    push({4, 0, 0, 0, 0, button, 0, 0, static_cast<bool>(down)});
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_game_NativeGameBridge_nativePollEvent(JNIEnv* env, jclass, jintArray out) {
    if (!out || env->GetArrayLength(out) < 8) return 0;
    InputEvent e{};
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        if (g_events.empty()) return 0;
        e = g_events.front();
        g_events.pop_front();
    }
    jint v[8] = {
        e.type, e.i, e.j,
        static_cast<jint>(e.down ? 1 : 0),
        static_cast<jint>(e.a * 1000.0f), static_cast<jint>(e.b * 1000.0f),
        static_cast<jint>(e.c * 1000.0f), static_cast<jint>(e.d * 1000.0f)
    };
    env->SetIntArrayRegion(out, 0, 8, v);
    return 1;
}

// Native API intended for the Android GLFW/native input adapter.
// The actual GLFW implementation can link against these symbols instead of
// trying to access Android Surface objects directly from the Java process.
extern "C" ANativeWindow* craftdroid_get_native_window() {
    std::lock_guard<std::mutex> lock(g_mutex);
    return g_window;
}

extern "C" void craftdroid_get_surface_size(int* width, int* height) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (width) *width = g_width;
    if (height) *height = g_height;
}

extern "C" int craftdroid_poll_native_event(int* type, int* i, int* j, int* down,
                                              float* a, float* b, float* c, float* d) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_events.empty()) return 0;
    const auto e = g_events.front();
    g_events.pop_front();
    g_input_dequeued.fetch_add(1, std::memory_order_relaxed);
    if (type) *type = e.type;
    if (i) *i = e.i;
    if (j) *j = e.j;
    if (down) *down = e.down ? 1 : 0;
    if (a) *a = e.a;
    if (b) *b = e.b;
    if (c) *c = e.c;
    if (d) *d = e.d;
    return 1;
}



extern "C" JNIEXPORT jstring JNICALL
Java_com_example_game_NativeGameBridge_nativeInputDiagnostics(JNIEnv* env, jclass) {
    size_t queued = 0;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        queued = g_events.size();
    }
    std::string result =
        "queued=" + std::to_string(queued) +
        " enqueued=" + std::to_string(g_input_enqueued.load(std::memory_order_relaxed)) +
        " dequeued=" + std::to_string(g_input_dequeued.load(std::memory_order_relaxed)) +
        " dropped=" + std::to_string(g_input_dropped.load(std::memory_order_relaxed)) +
        " coalesced=" + std::to_string(g_input_coalesced.load(std::memory_order_relaxed)) +
        " ready=" + std::to_string(g_glfw_input_ready.load(std::memory_order_acquire) ? 1 : 0);
    return env->NewStringUTF(result.c_str());
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_game_NativeGameBridge_nativeSendChar(JNIEnv*, jclass, jint codePoint) {
    if (codePoint <= 0 || codePoint > 0x10FFFF) return;
    InputEvent e{};
    e.type = 6;
    e.i = codePoint;
    push(e);
}

extern "C" JNIEXPORT void JNICALL
Java_org_lwjgl_glfw_CallbackBridge_nativeSendData(JNIEnv* env, jclass, jboolean, jint type, jstring data) {
    const char* text = data ? env->GetStringUTFChars(data, nullptr) : nullptr;
    LOGI("GLFW CallbackBridge data type=%d data=%s", type, text ? text : "");
    if (text) env->ReleaseStringUTFChars(data, text);
}

extern "C" JNIEXPORT jboolean JNICALL
Java_org_lwjgl_glfw_CallbackBridge_nativeSetInputReady(JNIEnv* env, jclass, jboolean ready) {
    // A stale callback may arrive while JLI_Launch is already unwinding. Do not
    // resurrect the callback request for a JVM that is no longer live. The
    // launch path clears this state after JLI_Launch returns, but rejecting the
    // request here closes the small concurrent-callback window before then.
    const int inputJavaState = g_java_state.load(std::memory_order_acquire);
    if (ready == JNI_TRUE &&
        (!g_java_running.load(std::memory_order_acquire) || inputJavaState != 2)) {
        // Only the fully RUNNING embedded JVM may own the callback dispatcher.
        // During STARTING/STOPPING a late GLFW callback must not resurrect the
        // input pump or retain a stale callback request across lifecycle edges.
        g_input_requested.store(false, std::memory_order_release);
        g_glfw_input_ready.store(false, std::memory_order_release);
        LOGI("CallbackBridge input-ready ignored: embedded JVM state=%d running=%d",
             inputJavaState, g_java_running.load(std::memory_order_acquire) ? 1 : 0);
        return JNI_FALSE;
    }
    g_input_requested.store(ready == JNI_TRUE, std::memory_order_release);
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        if (ready) {
            if (!g_callback_bridge_class && env) {
                jclass localClass = env->FindClass("org/lwjgl/glfw/CallbackBridge");
                if (localClass) {
                    jmethodID receive = env->GetStaticMethodID(localClass, "receiveCallback", "(IIIII)V");
                    if (receive) {
                        g_callback_bridge_class = reinterpret_cast<jclass>(env->NewGlobalRef(localClass));
                        g_callback_bridge_receive = receive;
                    } else {
                        env->ExceptionClear();
                    }
                    env->DeleteLocalRef(localClass);
                } else {
                    env->ExceptionClear();
                }
            }
            JavaVM* vm = nullptr;
            // Preserve a previously captured embedded VM handle if a later
            // callback cannot retrieve it. Clearing g_game_vm on a transient
            // GetJavaVM() failure would strand the input/stop paths even
            // though the original HotSpot VM is still alive.
            if (env && env->GetJavaVM(&vm) == JNI_OK && vm) {
                if (g_game_vm && g_game_vm != vm) {
                    LOGI("CallbackBridge VM mismatch: keeping original embedded VM handle");
                } else {
                    g_game_vm = vm;
                }
            }
        }
    }
    if (!ready) {
        {
            std::lock_guard<std::mutex> lock(g_mutex);
            g_glfw_input_ready.store(false, std::memory_order_release);
        }
        stopInputPump(true);
        return JNI_TRUE;
    }
    bool calledFromPump = false;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        calledFromPump = g_input_pump.joinable() &&
                std::this_thread::get_id() == g_input_pump.get_id();
    }
    // A CallbackBridge callback can be delivered by the input pump itself.
    // Never ask that thread to stop/join/restart itself; keep the existing pump
    // alive and simply transition its readiness state.
    if (calledFromPump) {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_glfw_input_ready.store(true, std::memory_order_release);
        return JNI_TRUE;
    }
    // Start the pump before reporting readiness to Java. If the embedded VM
    // handle disappeared or the pump cannot attach, leave the callback pipe
    // disabled rather than claiming success with no dispatcher behind it.
    if (!startInputPump()) {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_glfw_input_ready.store(false, std::memory_order_release);
        return JNI_FALSE;
    }
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_glfw_input_ready.store(true, std::memory_order_release);
    }
    // Flush anything queued before the JVM enabled the callback pipe, then
    // keep polling GLFW + dispatching Android events on the embedded JVM.
    flushGlfwEvents(env);
    return JNI_TRUE;
}

extern "C" JNIEXPORT jstring JNICALL
Java_org_lwjgl_glfw_CallbackBridge_nativeClipboard(JNIEnv* env, jclass, jint action, jstring copy) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (action == 2000 && copy) {
        const char* text = env->GetStringUTFChars(copy, nullptr);
        g_clipboard = text ? text : "";
        if (text) env->ReleaseStringUTFChars(copy, text);
        return copy;
    }
    return env->NewStringUTF(g_clipboard.c_str());
}

extern "C" JNIEXPORT void JNICALL
Java_org_lwjgl_glfw_CallbackBridge_nativeSetGrabbing(JNIEnv*, jclass, jboolean grab, jint, jint) {
    LOGI("GLFW cursor grab=%d", grab ? 1 : 0);
}

using JLI_LaunchFn = int (*)(int, char**, int, const char**, int, const char**,
                              const char*, const char*, const char*, const char*,
                              jboolean, jboolean, jboolean, jint);

static bool regularFileExists(const std::string& path) {
    struct stat st{};
    return !path.empty() && stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

static void prependEnvPath(const char* name, const std::vector<std::string>& entries) {
    std::vector<std::string> valid;
    for (const auto& entry : entries) {
        if (!entry.empty()) valid.push_back(entry);
    }
    const char* current = std::getenv(name);
    if (current && *current) valid.emplace_back(current);
    std::string joined;
    for (size_t i = 0; i < valid.size(); ++i) {
        if (i) joined.push_back(':');
        joined += valid[i];
    }
    if (!joined.empty()) setenv(name, joined.c_str(), 1);
}

static std::vector<std::string> runtimeLibDirs(const std::string& homePath) {
    // Android OpenJDK packages exist in both the desktop-style layout
    // (lib/jli, lib/server) and the Pojav-style multiarch layout
    // (lib/aarch64/jli, lib/aarch64, ...). Include both so the launcher
    // can use the same bridge with all supported runtime packages.
    return {
        homePath + "/lib/jli",
        homePath + "/lib/server",
        homePath + "/lib/client",
        homePath + "/lib",
        homePath + "/lib/aarch64/jli",
        homePath + "/lib/aarch64",
        homePath + "/lib/aarch64/client",
        homePath + "/lib/aarch64/server",
        homePath + "/lib/aarch32/jli",
        homePath + "/lib/aarch32",
        homePath + "/lib/aarch32/client",
        homePath + "/lib/aarch32/server",
        homePath + "/lib/arm/jli",
        homePath + "/lib/arm",
        homePath + "/lib/arm/client",
        homePath + "/lib/arm/server",
        homePath + "/lib/x86_64/jli",
        homePath + "/lib/x86_64",
        homePath + "/lib/x86_64/client",
        homePath + "/lib/x86_64/server",
        homePath + "/lib/i386/jli",
        homePath + "/lib/i386",
        homePath + "/lib/i386/client",
        homePath + "/lib/i386/server"
    };
}

static std::string firstExistingRuntimeFile(const std::vector<std::string>& paths, const char* fileName) {
    for (const auto& dir : paths) {
        const std::string candidate = dir + "/" + fileName;
        if (regularFileExists(candidate)) return candidate;
    }
    return {};
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_game_NativeGameBridge_nativeLaunchJava(JNIEnv* env, jclass,
                                                         jstring javaHome,
                                                         jobjectArray arguments,
                                                         jobjectArray environment) {
    std::unique_lock<std::mutex> launchLock(g_java_launch_mutex, std::defer_lock);
    if (!launchLock.try_lock()) {
        LOGI("Embedded JVM launch rejected: another launch is active");
        return -107;
    }
    // HotSpot's JNI invocation interface permits only one VM per native
    // process. Once JLI_Launch has returned and the bridge is EXITED (4),
    // attempting to create a second embedded VM in this same process is not a
    // supported restart path and can fail with JNI_EEXIST. Keep EXITED as a
    // terminal state for this process rather than pretending it is IDLE.
    int expectedState = g_java_state.load();
    if (expectedState == 4) {
        LOGI("Embedded JVM launch rejected: previous VM already exited in this process; restart CraftDroid process before launching again");
        return -108;
    }
    for (;;) {
        if (expectedState != 0) {
            LOGI("Embedded JVM launch rejected: state=%d", expectedState);
            return -107;
        }
        if (g_java_state.compare_exchange_weak(expectedState, 1)) break;
    }
    const char* home = javaHome ? env->GetStringUTFChars(javaHome, nullptr) : nullptr;
    if (!home || !*home) {
        if (home) env->ReleaseStringUTFChars(javaHome, home);
        g_java_state.store(0);
        return -100;
    }

    // Snapshot the caller environment BEFORE applying launch overrides.
    // Otherwise the guard would capture CraftDroid's temporary values and
    // restore those same values instead of the real caller state.
    ScopedEnvironment savedEnvironment(env, environment);

    if (environment) {
        const jsize n = env->GetArrayLength(environment);
        for (jsize i = 0; i < n; ++i) {
            auto value = (jstring) env->GetObjectArrayElement(environment, i);
            if (!value) continue;
            const char* line = env->GetStringUTFChars(value, nullptr);
            if (line) {
                std::string s(line);
                const auto eq = s.find('=');
                if (eq != std::string::npos) {
                    setenv(s.substr(0, eq).c_str(), s.substr(eq + 1).c_str(), 1);
                }
                env->ReleaseStringUTFChars(value, line);
            }
            env->DeleteLocalRef(value);
        }
    }

    const std::string homePath(home);
    env->ReleaseStringUTFChars(javaHome, home);

    const std::vector<std::string> libDirs = runtimeLibDirs(homePath);
    const std::string jli = firstExistingRuntimeFile(libDirs, "libjli.so");
    const std::vector<std::string> jvmCandidates = {
        homePath + "/lib/server/libjvm.so",
        homePath + "/lib/client/libjvm.so",
        homePath + "/lib/libjvm.so",
        homePath + "/lib/aarch64/libjvm.so",
        homePath + "/lib/aarch64/server/libjvm.so",
        homePath + "/lib/aarch64/client/libjvm.so",
        homePath + "/lib/aarch32/libjvm.so",
        homePath + "/lib/aarch32/server/libjvm.so",
        homePath + "/lib/aarch32/client/libjvm.so",
        homePath + "/lib/arm/libjvm.so",
        homePath + "/lib/arm/server/libjvm.so",
        homePath + "/lib/arm/client/libjvm.so",
        homePath + "/lib/x86_64/libjvm.so",
        homePath + "/lib/x86_64/server/libjvm.so",
        homePath + "/lib/x86_64/client/libjvm.so",
        homePath + "/lib/i386/libjvm.so",
        homePath + "/lib/i386/server/libjvm.so",
        homePath + "/lib/i386/client/libjvm.so"
    };
    if (jli.empty()) {
        LOGI("JLI runtime file missing under %s", homePath.c_str());
        g_java_state.store(0);
        return -104;
    }
    std::string jvmPath;
    for (const auto& candidate : jvmCandidates) {
        if (regularFileExists(candidate)) { jvmPath = candidate; break; }
    }
    if (jvmPath.empty()) {
        LOGI("JVM runtime file missing under %s", homePath.c_str());
        g_java_state.store(0);
        return -105;
    }

    // JLI resolves libjvm and its companion modules through the process
    // environment. Establish the runtime search path in native code before
    // opening any JRE library, so Android's linker sees the correct JRE first.
    setenv("JAVA_HOME", homePath.c_str(), 1);
    const std::string jliDir = jli.substr(0, jli.find_last_of('/'));
    setenv("JLI_HOME", jliDir.c_str(), 1);
    prependEnvPath("LD_LIBRARY_PATH", libDirs);

    // Make CraftDroid's JNI symbols visible to the embedded Java VM. The
    // Android activity loaded this library before JLI_Launch, but Android
    // loaders may keep it local unless we explicitly promote it.
    void* selfBridge = dlopen("libcraftdroidbridge.so", RTLD_NOW | RTLD_GLOBAL);
    LOGI("craftdroidbridge global handle=%p", selfBridge);

    // Preload only JRE libraries that exist. Absolute paths prevent an
    // unrelated renderer/native package from satisfying the VM's generic
    // library names. The dependency order starts with libjvm and then the
    // Java modules used by the launcher.
    const char* preloadNames[] = {
        "libjvm.so", "libjsig.so", "libverify.so", "libjava.so", "libnio.so",
        "libnet.so", "libzip.so", "libmanagement.so", "libmanagement_ext.so",
        "libinstrument.so", "libjawt.so", "libawt.so", "libawt_headless.so",
        "libawt_xawt.so", "libjsound.so", "libprefs.so", "libj2pkcs11.so",
        "libsunec.so", "libjdwp.so", "libfreetype.so", "libfontmanager.so",
        "libmlib_image.so", "libjaas_unix.so", "libj2gss.so", "libdt_socket.so",
        "libsctp.so", "libextnet.so"
    };
    for (const char* name : preloadNames) {
        bool loaded = false;
        for (const auto& dir : libDirs) {
            const std::string candidate = dir + "/" + name;
            if (!regularFileExists(candidate)) continue;
            void* h = dlopen(candidate.c_str(), RTLD_NOW | RTLD_GLOBAL);
            if (h) { loaded = true; break; }
            const char* err = dlerror();
            LOGI("Optional JRE preload failed %s: %s", candidate.c_str(), err ? err : "unknown");
        }
        if (!loaded) LOGI("JRE library not present/loadable (continuing): %s", name);
    }

    // libjvm must be resident before JLI is invoked. RTLD_NOLOAD avoids
    // opening a second copy when the preload succeeded.
    void* vmHandle = dlopen(jvmPath.c_str(), RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
    if (!vmHandle) vmHandle = dlopen(jvmPath.c_str(), RTLD_NOW | RTLD_GLOBAL);
    if (!vmHandle) {
        const char* err = dlerror();
        LOGI("Unable to load JVM %s: %s", jvmPath.c_str(), err ? err : "unknown");
        g_java_state.store(0);
        return -106;
    }

    void* handle = dlopen(jli.c_str(), RTLD_NOW | RTLD_GLOBAL);
    if (!handle) {
        LOGI("Unable to load %s: %s", jli.c_str(), dlerror());
        g_java_state.store(0);
        return -101;
    }
    auto launch = reinterpret_cast<JLI_LaunchFn>(dlsym(handle, "JLI_Launch"));
    if (!launch) {
        LOGI("JLI_Launch missing: %s", dlerror());
        dlclose(handle);
        g_java_state.store(0);
        return -102;
    }

    std::vector<std::string> args;
    const jsize n = arguments ? env->GetArrayLength(arguments) : 0;
    for (jsize i = 0; i < n; ++i) {
        auto value = (jstring) env->GetObjectArrayElement(arguments, i);
        if (!value) continue;
        const char* text = env->GetStringUTFChars(value, nullptr);
        args.emplace_back(text ? text : "");
        if (text) env->ReleaseStringUTFChars(value, text);
        env->DeleteLocalRef(value);
    }
    // LaunchCommandBuilder supplies JVM/game arguments only (it does not
    // include an argv[0]). JLI_Launch follows the normal Java launcher ABI,
    // where argv[0] must be the launcher name and every JVM option follows it.
    // Treating the first -X/-D option as argv[0] can make JLI mis-parse the
    // command line and fail before the VM is created.
    const std::string expectedJava = homePath + "/bin/java";
    if (args.empty() || args[0] != expectedJava) {
        args.insert(args.begin(), expectedJava);
    }
    LOGI("Launching embedded Java: home=%s argv0=%s argc=%zu", homePath.c_str(), args[0].c_str(), args.size());

    std::vector<char*> argv;
    argv.reserve(args.size());
    for (auto& a : args) argv.push_back(a.data());

    // Capture stdout/stderr from the embedded JVM so the launcher can show
    // useful crash diagnostics instead of an empty StringBuilder.
    int oldOut = dup(STDOUT_FILENO);
    int oldErr = dup(STDERR_FILENO);
    int logFd = -1;
    const char* logPath = std::getenv("CRAFTDROID_LOG_FILE");
    if (logPath && *logPath) {
        logFd = open(logPath, O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (logFd >= 0) {
            dup2(logFd, STDOUT_FILENO);
            dup2(logFd, STDERR_FILENO);
        }
    }

    // JLI_Launch creates the Android-compatible Java VM inside this process.
    // Track this independently of Android's Process API because Minecraft is
    // embedded in CraftDroid rather than running as a child process.
    g_java_state.store(2);
    g_java_running.store(true);
    const int rc = launch(static_cast<int>(argv.size()), argv.data(), 0, nullptr,
                          0, nullptr, "CraftDroid", "CraftDroid", "CraftDroid", "CraftDroid",
                          JNI_FALSE, JNI_FALSE, JNI_FALSE, 0);
    g_java_running.store(false, std::memory_order_release);
    // The embedded VM has ended. Clear the desired input state before stopping
    // the pump so a concurrent Android Surface callback cannot observe a stale
    // request and recreate a dispatcher for a dead JVM.
    g_input_requested.store(false, std::memory_order_release);
    g_glfw_input_ready.store(false, std::memory_order_release);
    // JLI_Launch may return after partial VM initialization even when the
    // bridge never received CallbackBridge.nativeSetInputReady(). Therefore
    // g_game_vm is not a reliable indicator that the HotSpot VM slot is free.
    // Treat every completed JLI_Launch call as terminal for this process;
    // attempting to recreate an embedded HotSpot VM in the same process is not
    // a supported restart path and can fail with JNI_EEXIST or leave stale
    // runtime state behind.
    g_java_state.store(4);
    stopInputPump();
    // JLI_Launch owns the embedded VM lifecycle. Once it returns, the VM is
    // no longer a valid target for stop/input calls. Do not rediscover a JVM
    // with JNI_GetCreatedJavaVMs here: on Android that API may report ART's
    // VM rather than the embedded HotSpot VM, which could cause later native
    // code to attach to the wrong runtime. Clear the embedded VM handle
    // unconditionally and require the next process to create a fresh bridge.
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        g_game_vm = nullptr;
    }

    fflush(stdout);
    fflush(stderr);
    if (oldOut >= 0) { dup2(oldOut, STDOUT_FILENO); close(oldOut); }
    if (oldErr >= 0) { dup2(oldErr, STDERR_FILENO); close(oldErr); }
    if (logFd >= 0) close(logFd);
    return rc;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeIsJavaRunning(JNIEnv*, jclass) {
    return g_java_running.load() ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_game_NativeGameBridge_nativeGetJavaState(JNIEnv*, jclass) {
    return g_java_state.load();
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_game_NativeGameBridge_nativeRequestJavaStop(JNIEnv*, jclass) {
    if (!g_java_running.load()) return JNI_TRUE;
    g_java_state.store(3);

    // JLI_Launch is not a child process, so Process.destroy() cannot stop it.
    // Ask the embedded HotSpot VM to perform a normal Java shutdown instead.
    // Only the embedded HotSpot VM captured from CallbackBridge.nativeSetInputReady
    // may be used for shutdown. Never fall back to JNI_GetCreatedJavaVMs(): on
    // Android that can return ART's VM and would route System.exit() into the
    // wrong runtime.
    JavaVM* vm = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_mutex);
        vm = g_game_vm;
    }
    if (!vm) {
        LOGI("Embedded JVM stop rejected: game VM handle is unavailable");
        g_java_state.store(2);
        return JNI_FALSE;
    }

    JNIEnv* jni = nullptr;
    bool attached = false;
    if (vm->GetEnv(reinterpret_cast<void**>(&jni), JNI_VERSION_1_6) != JNI_OK) {
        if (vm->AttachCurrentThread(&jni, nullptr) != JNI_OK) {
            g_java_state.store(2);
            return JNI_FALSE;
        }
        attached = true;
    }

    jclass systemClass = jni->FindClass("java/lang/System");
    jmethodID exitMethod = systemClass ? jni->GetStaticMethodID(systemClass, "exit", "(I)V") : nullptr;
    if (exitMethod) {
        jni->CallStaticVoidMethod(systemClass, exitMethod, 0);
        if (jni->ExceptionCheck()) {
            jni->ExceptionDescribe();
            jni->ExceptionClear();
            LOGI("Embedded JVM stop: System.exit() raised a Java exception; JVM remains running");
            g_java_state.store(2);
            if (systemClass) jni->DeleteLocalRef(systemClass);
            if (attached) vm->DetachCurrentThread();
            return JNI_FALSE;
        }
    }
    if (systemClass) jni->DeleteLocalRef(systemClass);
    if (attached) vm->DetachCurrentThread();
    if (!exitMethod) {
        g_java_state.store(2);
        return JNI_FALSE;
    }
    return JNI_TRUE;
}

extern "C" int craftdroid_egl_init() {
    std::lock_guard<std::mutex> lock(g_mutex);
    return createEglLocked() ? 1 : 0;
}

extern "C" int craftdroid_egl_make_current() {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_egl_display == EGL_NO_DISPLAY) return 0;
    return eglMakeCurrent(g_egl_display, g_egl_surface, g_egl_surface, g_egl_context) ? 1 : 0;
}

extern "C" int craftdroid_egl_swap_buffers() {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_egl_display == EGL_NO_DISPLAY || g_egl_surface == EGL_NO_SURFACE) return 0;
    return eglSwapBuffers(g_egl_display, g_egl_surface) ? 1 : 0;
}

extern "C" void craftdroid_egl_destroy() {
    // Keep the exported native entry point consistent with the JNI guard.
    // Callers outside NativeGameBridge must not bypass the embedded-JVM
    // lifecycle protection and destroy the live Minecraft render context.
    const int javaState = g_java_state.load(std::memory_order_acquire);
    if (javaState != 0 && javaState != 4) {
        LOGI("EGL destroy ignored while embedded JVM lifecycle state=%d", javaState);
        return;
    }
    std::lock_guard<std::mutex> lock(g_mutex);
    destroyEglLocked();
}
