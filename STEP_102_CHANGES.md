# CraftDroid Step 102

## Embedded HotSpot lifecycle safety

- Corrected Step 101's retryable-state regression.
- `g_game_vm` is populated by the optional CallbackBridge path and cannot reliably prove that JLI_Launch did not partially create a VM.
- After any completed `JLI_Launch()` invocation, the bridge now remains terminal `EXITED` for the current Android process.
- Prevents unsafe second-VM creation after partial HotSpot initialization.
- Updated Kotlin state documentation to match the native lifecycle contract.
