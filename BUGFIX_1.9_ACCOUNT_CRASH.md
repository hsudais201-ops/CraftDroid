# CraftDroid 2.0 Account Manager Crash Fix

## Fixed
- Invalid offline usernames no longer clear the active account before validation.
- Offline account creation errors are caught in the ViewModel and shown in the account dialog instead of escaping a coroutine and crashing the app.
- Offline account creation now stays open until success; the Success/Error state is visible.
- Default offline username changed to `Player`.
- Offline profile rename validates the same 3–16 character `[A-Za-z0-9_]+` rule and reports errors instead of crashing.
- Offline/local accounts are no longer blocked by LauncherViewModel before launch; MinecraftLaunchManager handles the offline session configuration.
- Account card popup state is keyed to the account UUID so it cannot leak between recomposed/reordered profiles.

## Why the crash happened
The most dangerous path was the local profile form: `LocalTestProfileProvider.createProfile()` used `require(...)` for username validation inside a ViewModel coroutine, while the UI immediately dismissed the dialog. An invalid username could therefore throw an uncaught coroutine exception and close the app. The fix validates before changing selection and converts the exception into `AuthState.Error`, which the dialog already knows how to display.

## Compose safety
The account list uses stable UUID keys. Compose recommends stable, unique keys for changing/reordered lazy lists so remembered item state stays attached to the correct account.
