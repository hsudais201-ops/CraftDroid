# CraftDroid Step 20 — Microsoft Account Session Hardening

## What changed
- Added a real Minecraft Services profile validation before a Microsoft account can launch.
- The cached Minecraft access token is checked against the selected account UUID.
- If the token belongs to another profile, launch is blocked instead of sending mismatched authentication arguments to Minecraft.
- The latest Minecraft username/skin are synchronized back into the local account record after validation.
- Added secure-token expiry access for keeping the account database timestamp synchronized.
- Local/offline test profiles remain explicitly separate and do not claim Microsoft/Xbox authentication.

## Why
A non-empty cached token is not enough to prove that it still represents the selected Minecraft profile. CraftDroid now validates the token against the Minecraft profile endpoint immediately before launch.

## Important limitation
This does not make Microsoft authentication independent of Microsoft/Xbox services. A Microsoft account still needs a valid Minecraft Java profile and an active Minecraft Services session.

## Verification
- Kotlin source changes were checked for the expected methods and call flow.
- Full Gradle/APK compilation still depends on the project build environment and network availability.
- Real Minecraft boot and online multiplayer are not claimed until tested on a physical Android device.
