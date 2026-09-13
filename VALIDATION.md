# Validation — 0.2.0 beta

Tested on macOS Apple Silicon, September 13, 2026, against official Arc 1.164.0 (86805).

## Completed

- Official Apple-anchored developer signature and expected Arc team/identifier checked. Source executable hash remained unchanged.
- Fresh isolated clone built, locally signed, launched, and normally quit.
- Existing Borderless prototype profile copied with file hashes checked and SQLite integrity verified.
- Prototype Safe Storage and Arc authentication copied into a unique clone Keychain namespace without exporting secret values.
- Migrated sidebar and Arc authentication restored in a live browser window.
- Cookie and saved-password decryption verified inside the cloned browser.
- Password Manager remains usable when one legacy credential is unreadable;
  readable entries are returned and the unreadable row is preserved.
- Single-page borderless rendering, side-by-side and stacked splits, Find-in-Page match highlighting, and Little Arc startup exercised interactively. Stacked-pane drag resizing was visually verified.
- Update built a new staged app from official Arc, checked startup and credential decryption in a disposable profile copy, and replaced the app while retaining the existing profile.
- A duplicate running test copy caused candidate rejection; duplicate-instance checks and candidate cleanup were added.
- The double-click installer was checked for first-run guidance, prerequisite
  detection, existing-install detection, readable failure handling, and shell
  syntax. Its update path can be safely dismissed before any change by closing
  the window.
- 16 fixture tests passed: copy consistency and isolation, corrupt database rejection, symlink rejection, path overlap rejection, existing destination refusal, downgrade refusal, failed-update preservation, successful-update backup retention, rollback of matched app/profile, rollback failure recovery, and uninstall data retention.

## Boundaries

- The real update test reapplied Arc 1.164.0 to a clone based on that same official build. Migration started from the older Borderless prototype. Compatibility with unreleased future Arc builds has not been established.
- Rollback and uninstall were exercised with fixtures, not by removing the user's working installation.
- Initial creation from an official Arc profile, Intel macOS, all extension behaviors, all websites' session validity, fullscreen transitions, and every split arrangement have not been exhaustively tested.
- The automated update gate checks the source signature, required symbols/methods, startup, home isolation, a browser window, and encrypted-data readability. It does not replace a complete visual regression suite.
- The disposable validation profile is isolated on disk. It uses the clone's Keychain namespace; official Arc's Keychain items are not used for subsequent updates.
- CloudKit is disabled. Other Arc account/sync behavior is not guaranteed.

This is a usable first beta, not an official Arc distribution or a promise of compatibility with all future releases.
