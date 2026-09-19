package com.example.logs

/** Classifies JVM/Minecraft failures into actionable repair categories. */
object LaunchFailureClassifier {
    enum class Kind { CLASS_MISSING, LINKAGE, NATIVE_LIBRARY, JVM_NATIVE_CRASH, JAVA_VERSION, MEMORY, RENDERER, MOD_LOADER, UNKNOWN }
    data class Result(val kind: Kind, val summary: String, val target: String? = null, val action: String)

    fun classify(text: String): Result {
        val t = text.lowercase()
        fun quoted(prefix: String): String? = Regex("${Regex.escape(prefix)}\\s*[:\\-]?\\s*([^\\s\\n]+)", RegexOption.IGNORE_CASE).find(text)?.groupValues?.getOrNull(1)
        return when {
            "classnotfoundexception" in t -> Result(Kind.CLASS_MISSING, "A required Java class is missing from the classpath.", quoted("ClassNotFoundException"), "Repair/download the missing library and rebuild the classpath.")
            "noclassdeffounderror" in t -> Result(Kind.CLASS_MISSING, "A required class was unavailable during JVM linking.", quoted("NoClassDefFoundError"), "Repair the library that provides the class; also check for a dependency version conflict.")
            "unsatisfiedlinkerror" in t || "cannot open shared object file" in t || "dlopen failed" in t -> {
                val lib = Regex("(?:no|cannot open|could not load).*?(lib[a-z0-9_+.-]+\\.so)", RegexOption.IGNORE_CASE).find(text)?.groupValues?.getOrNull(1)
                Result(Kind.NATIVE_LIBRARY, "Native library linkage failure: an Android native library could not be linked.", lib, "Verify ABI, LD_LIBRARY_PATH, JNI symbols, and the exact LWJGL/renderer native package.")
            }
            "sigsegv" in t || "sigabrt" in t || "problematic frame:" in t || "fatal error has been detected by the java runtime environment" in t -> Result(Kind.JVM_NATIVE_CRASH, "The JVM or a native library crashed.", null, "Use the hs_err_pid log and native stack to identify the crashing library; do not retry the same incompatible native binary.")
            "unsupportedclassversionerror" in t || "more recent version of the java runtime" in t -> Result(Kind.JAVA_VERSION, "Java version incompatibility: the selected Java runtime is incompatible with the Minecraft classes.", null, "Install/select the Java major required by the Minecraft version.")
            "outofmemoryerror" in t || "killed by android" in t -> Result(Kind.MEMORY, "Out of Memory: the JVM/device ran out of memory.", null, "Lower the maximum heap and close background applications.")
            "failed to create glfw" in t || "glfw error" in t || "egl_" in t || "opengl" in t && "error" in t -> Result(Kind.RENDERER, "Graphics/GLFW/EGL initialization failed.", null, "Switch renderer and verify the Android EGL/GLFW native stack.")
            "fabric" in t && ("loader" in t || "knotclient" in t) || "forge" in t && ("mod" in t || "loader" in t) -> Result(Kind.MOD_LOADER, "A mod-loader startup failure was detected.", null, "Verify loader profile, loader libraries, Minecraft version, and mod dependencies.")
            else -> Result(Kind.UNKNOWN, "Minecraft terminated without a recognized failure signature.", null, "Inspect the complete launch diagnostics and latest.log.")
        }
    }
}
