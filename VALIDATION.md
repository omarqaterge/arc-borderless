# Validation — signed single-instance beta

Tested on macOS Apple Silicon, September 13, 2026, against official Arc 1.164.0 (86805).

## Completed

- Verified the source app against Arc's Apple-anchored developer requirement, bundle identifier `company.thebrowser.Browser`, and Team ID `S6N382Y83G`.
- Verified the source executable hash before building the launcher.
- Built and ad-hoc signed the small launcher and borderless library without copying or modifying Arc.app.
- Started Arc's untouched executable through the launcher with the borderless library loaded.
- Confirmed the live browser process used Arc's official bundle identifier and Team ID.
- Confirmed the live executable retained `com.apple.developer.web-browser.public-key-credential`.
- Confirmed `ArcBorderless.dylib` was loaded in the running official Arc process.
- Confirmed signed mode uses the normal Arc profile in a normal launch. The automated startup test uses a disposable empty profile.
- Confirmed the patch hooks installed and produced a live Arc window during the disposable startup test.
- Confirmed the signed-mode patch does not interpose Keychain APIs, disable CloudKit, or block Arc's updater.
- Confirmed an older isolated Arc Borderless profile and the replaced app are retained during migration to signed mode.
- Installer shell syntax, Python syntax, code signatures, and 9 automated tests passed.

## Boundaries

- Native passkey entitlement presence was verified. A complete Google passkey login with Touch ID still requires the user to exercise their own account and Keychain entry.
- Arc and Borderless mode are the same signed application process and cannot run simultaneously.
- The real profile was opened only by the final normal launch. Automated validation used a disposable profile and did not inspect private browsing data.
- Compatibility with later Arc builds is not assumed. The launcher refuses to run if the verified Arc executable hash changes.
- Apple Silicon is tested. Intel macOS and every split arrangement are not exhaustively verified.
- A future Arc hardened-runtime or library-validation change could prevent local injection. Under default macOS System Integrity Protection (SIP), dyld strips dynamic libraries injected into Developer ID signed binaries that enable Hardened Runtime; local injection requires SIP debugging restrictions to be disabled.
- The installer preflight now detects SIP status and reports clear diagnostic explanations if the startup probe fails to complete.
