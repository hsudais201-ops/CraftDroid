# Embedded JVM bridge

`MinecraftLaunchManager` now uses `NativeGameBridge.launchJava()` instead of spawning a second OS process. The native code dynamically loads `<javaHome>/lib/jli/libjli.so` and resolves `JLI_Launch`.

This is the key boundary needed by an Android Java launcher: the JVM, GLFW bridge and Android Surface can live in the same process. Pojav's Android implementation similarly uses a JLI/native launch path and custom GLFW stub.

## Runtime requirements

The selected OpenJDK package must be an Android-compatible build and must contain a working:

- `lib/jli/libjli.so`
- `lib/server/libjvm.so` (or the runtime's supported JVM library)
- Android-compatible Java libraries

A normal desktop Linux/Windows JRE is not sufficient.
