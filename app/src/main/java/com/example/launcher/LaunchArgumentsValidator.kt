package com.example.launcher

/** Validates the final process arguments before a Java process is created. */
object LaunchArgumentsValidator {
    private val managedJvmPrefixes = listOf(
        "-Xmx", "-Xms", "-Djava.home=", "-Djava.library.path=", "-Dorg.lwjgl.librarypath=", "-cp", "-classpath"
    )

    fun validateJvmArguments(arguments: List<String>) {
        require(arguments.none { it.indexOf('\u0000') >= 0 || it.contains('\n') || it.contains('\r') }) {
            "JVM arguments contain an illegal control character"
        }
        require(arguments.count { it == "-cp" || it == "-classpath" } <= 1) {
            "Classpath option is defined more than once"
        }
        val managed = arguments.filter { value -> managedJvmPrefixes.any { prefix -> value == prefix || value.startsWith(prefix) } }
        require(managed.count { it.startsWith("-Xmx") } <= 1) { "Conflicting -Xmx arguments" }
        require(managed.count { it.startsWith("-Xms") } <= 1) { "Conflicting -Xms arguments" }
    }

    fun validateGameArguments(arguments: List<String>) {
        require(arguments.none { it.indexOf('\u0000') >= 0 }) { "Game arguments contain an illegal NUL character" }
    }

    fun isManagedUserJvmArgument(argument: String): Boolean =
        managedJvmPrefixes.any { argument == it || argument.startsWith(it) }
}
