# CraftDroid 2.3 — Pojav-style Local Account

## Flow
1. Accounts → + Add Account.
2. Choose Offline / Local Account.
3. Enter a 3–16 character Minecraft username using letters, numbers, or `_`.
4. Create the local profile.
5. The profile receives a stable `OfflinePlayer:<username>` UUID.
6. The new profile becomes the selected local account only after it is successfully inserted.
7. Select the profile from Account Manager and launch an already-installed Minecraft version.

## Authentication boundary
Local accounts do not create Microsoft/Xbox/Minecraft access tokens and are not presented as authenticated accounts. They are intended for local/offline gameplay only. They cannot authenticate to online-mode servers.

## Crash/bug fixes
- Fixed an undefined `isOfflineAccount` launch variable that could prevent compilation.
- Local profile validation now occurs before changing the selected account.
- Invalid UUIDs are rejected safely.
- Local username validation is consistent across create/update/rename.
- The local launch path always supplies the explicit offline/local flag to the command builder.
- Existing Microsoft and Ely.by authentication paths remain unchanged.
