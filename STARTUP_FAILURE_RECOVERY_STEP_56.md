# CraftDroid Step 56 — Startup Failure Recovery

This step hardens the six common startup failure families:

- ClassNotFoundException / NoClassDefFoundError: classpath preflight now triggers one automatic deterministic installation repair, rebuilds the classpath, and re-runs preflight before JLI starts.
- UnsatisfiedLinkError: native stack, ELF ABI, dependency validation, and GLFW preparation are completed before JVM startup; an unprepared bridge is rejected.
- SIGSEGV/SIGABRT: live native segmentation faults cannot safely be recovered inside the crashing process. A previous HotSpot `hs_err` report is used on the next launch to select the Compatibility renderer when graphics/native components were implicated, avoiding immediate repetition.
- GLFW failures: GLFW native handshake and pre-JVM preparation must succeed before the embedded JVM is started.
- OOM / Android kill: heap sizing is capped from current device available memory, custom `-Xmx`/`-Xms` overrides are ignored so the launcher policy remains authoritative, and JVM OOM exits produce diagnostics/heap-dump evidence.

The project still distinguishes static/source fixes from device-level verification. A real SIGSEGV or OOM on a physical device requires the resulting native/JVM diagnostic evidence to identify any remaining device-specific issue.
