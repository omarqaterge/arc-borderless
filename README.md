# Arc Borderless

[![Tests](https://github.com/omarqaterge/arc-borderless/actions/workflows/tests.yml/badge.svg)](https://github.com/omarqaterge/arc-borderless/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An experimental macOS installer that creates an isolated, borderless clone of
Arc and can rebuild it from later official Arc releases.

Creates a locally patched copy of your installed Arc browser, with its own profile and Keychain namespace. Official Arc is the source for application updates. It is never patched in place.

The clone removes Arc's outer web-content margins, split-pane outlines and
per-pane split toolbars while keeping split resizing available. It uses native
runtime hooks because these elements are implemented in AppKit rather than web
page CSS.

> [!WARNING]
> This is an unofficial, locally signed modification. It is not made,
> supported, or endorsed by The Browser Company. Back up important data and
> read the limitations before use.

## Requirements

- macOS, with Arc installed locally. Tested platform: Apple Silicon.
- Python 3.9 or newer and Apple Command Line Tools (`xcode-select --install`).
- Enough free space for an app/profile backup. APFS copy-on-write is used when available.
- macOS may ask you to authorize access to the source encryption key. Secrets stay within native process memory and Keychain; they are never written to logs, files, or the ZIP.

The package contains patch source, installer code, and tests. It contains no Arc application, profile, cookies, or passwords.

## Create from official Arc

Double-click `Create.command`, or run:

```sh
python3 borderless.py create --source-data "$HOME/Library/Application Support/Arc" --preferences "$HOME/Library/Preferences/company.thebrowser.Browser.plist" --quit-source
```

This quits official Arc normally, copies its application data, migrates the Safe Storage encryption key into a new isolated Keychain item, checks copied SQLite databases and cookie decryption, and tests the candidate in a disposable profile copy. The original app/profile are retained.

For a fresh profile that does not copy cookies or saved logins:

```sh
python3 borderless.py create --empty
```

Default destinations:

- App: `~/Applications/Arc Borderless.app`
- Data: `~/Library/Application Support/Arc Borderless`

You may supply `--app PATH` and `--root PATH` to choose other separate destinations. An existing destination is never overwritten by `create`.

Arc account sign-in may be required after migration from official Arc. Website cookies and saved passwords are separate from Arc account authentication. Copied login records do not guarantee that every website will retain its session.

## Migrate the earlier Borderless prototype

The prototype has two apparent profile locations; the active one is normally the `User Data` folder inside its fixed home. Supply the parent Arc application-support folder, not the unused standalone `profile` folder:

```sh
python3 borderless.py create \
  --source-data '/path/to/arc-mod/home/Library/Application Support/Arc' \
  --source-app '/path/to/arc-mod/Arc-Borderless.app' \
  --source-key-service 'ArcBorderlessTest/Arc Safe Storage' \
  --preferences '/path/to/arc-mod/home/Library/Preferences/company.thebrowser.Browser.plist' \
  --quit-source
```

This also copies authentication items specifically from the prototype's `ArcBorderlessTest/` Keychain namespace. It does not enumerate or export other applications' secret values.

## Update

First update **official Arc** through its normal updater. Then double-click `Update.command`, or run:

```sh
python3 borderless.py update
```

The installer verifies the official developer signature and expected native UI symbols, builds a staged clone, normally quits Borderless, backs up its app and profile, and tests the new app against a disposable copy of that profile. The candidate must reach a browser window and verify cookie/password decryption before replacement. A failed candidate does not replace the installed app. A successful update retains the existing Borderless profile and Keychain namespace; it never reimports older official-Arc data.

The clone's Sparkle updater is blocked; it must be updated through this installer. This version does not download releases, schedule background checks, or silently apply updates.

Static checks and startup checks are not proof of all UI behavior. Future Chromium releases may still need patch changes. Do not keep using an obsolete browser indefinitely if a security update fails validation.

## Roll back

The update command prints a matched app/profile backup directory:

```sh
python3 borderless.py rollback '/path/printed/by/update'
```

Both app and profile are restored together because Chromium profile migrations may not be backward compatible. Your newer app/profile are preserved in another backup before restoring. Changes made after the chosen snapshot are not merged into the older snapshot.

## Inspect or uninstall

```sh
python3 borderless.py check
python3 borderless.py status
python3 borderless.py uninstall
```

`check` verifies the source without changing it. Finder metadata, if needed, is normalized only on a disposable copy before checking the original signature.

`uninstall` moves the managed clone app to Trash and retains its profile, backups, and isolated Keychain items. Official Arc is unaffected.

## Limitations

- Unofficial, locally re-signed app. Official signing identity and restricted entitlements cannot be retained. CloudKit is disabled; official sync is not promised.
- Only one-time profile migration, not continuous synchronization or two-way merging.
- Arc's native private UI classes may change, even in a Chromium-only update.
- Keychain access may prompt again after rebuilding a locally signed executable.
- The clone is not registered as the default browser or a URL handler by the installer.
- Website sessions, device-bound credentials, and server-side login validity cannot be guaranteed by copying a profile.
- Backups contain private browsing data. Keep them private.

## Privacy and distribution

This repository contains source code only. It does not include Arc, Chromium,
an application bundle, a browser profile, credentials, cookies, or private
Keychain data. You must already have an official local Arc installation.

Do not distribute a patched Arc application: Arc and its bundled components
remain the property of their respective owners.

## License

The installer and patch source in this repository are available under the
[MIT License](LICENSE). This license does not grant rights to Arc or any files
copied from an Arc installation.

## Development checks

```sh
python3 -m unittest discover -s tests -v
```

See `VALIDATION.md` for the actual tested build and outstanding limitations.

Credential verification during updates runs inside the cloned browser, using its existing Keychain authorization. If macOS requires renewed authorization after a future Arc executable change, the normal browser Keychain prompt may still appear. The installer does not bypass that permission.
