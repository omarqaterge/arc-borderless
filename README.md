# Arc Borderless

[![Tests](https://github.com/omarqaterge/arc-borderless/actions/workflows/tests.yml/badge.svg)](https://github.com/omarqaterge/arc-borderless/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Arc Borderless is an experimental macOS launcher that opens your official Arc browser in a borderless mode. It removes the frame around webpages and the visible gaps between split panes while keeping split resizing available.

It uses Arc's untouched, officially signed executable and your normal Arc profile. Your passwords, cookies, tabs, Spaces, folders, extensions, account, and settings therefore remain exactly where Arc already stores them.

> [!WARNING]
> This is an unofficial community modification. It is not made, supported, or endorsed by The Browser Company. The launcher loads local code into Arc at startup and must be rebuilt after Arc updates.

## What changes?

| Area | Regular Arc | Arc Borderless mode |
| --- | --- | --- |
| Webpage edges | Visible margins surround web content | Content extends to the window edges |
| Split panes | Outlines and visible gaps separate panes | Pane outlines and gaps are removed |
| Split toolbars | Each pane has its own toolbar area | Individual split-pane toolbars are hidden |
| Split resizing | Visible dividers can be dragged | Invisible drag areas keep resizing available |
| Browser data | Uses your normal Arc profile | Uses the same normal Arc profile |
| App identity | Official Arc signature and entitlements | The running browser is still official signed Arc |
| Passkeys | Native iCloud Keychain passkeys are available | The same native passkey entitlement remains available |

The patch focuses on Arc's native window frame. The sidebar, command bar, downloads, Find in Page, Little Arc, tabs, Spaces, folders, extensions, Arc Sync, and normal browsing remain part of Arc.

## Easy installation

No Terminal commands need to be typed.

1. Install official Arc in `/Applications` and open it once.
2. Download **[Arc-Borderless-Installer.zip](https://github.com/omarqaterge/arc-borderless/releases/latest/download/Arc-Borderless-Installer.zip)**.
3. Double-click the ZIP and open the resulting folder.
4. Control-click **Install Arc Borderless.command**, choose **Open**, then confirm **Open** if macOS asks.
5. Read the explanation and press Return.

The installer verifies Arc's official signature, checks that the required Arc interface components still exist, builds a local launcher, and tests the patch with an empty temporary profile. Arc's application files and real profile are never edited by the installer.

The launcher is installed at:

`~/Applications/Arc Borderless.app`

Open **Arc Borderless** when you want the borderless interface. Open **Arc** normally when you want the regular interface.

## One Arc process at a time

Arc and Arc Borderless mode cannot run simultaneously. Both launch choices ultimately run the same officially signed Arc application.

If Arc is already open when you choose Arc Borderless, the launcher offers to quit Arc and continue. Arc restores its windows and tabs from the same profile. If Borderless mode is already running and you click regular Arc, macOS brings the existing Borderless process forward; quit it first to return to regular Arc.

This single-instance design is what preserves Arc's signing identity and restricted browser entitlements. Copying Arc's signature onto a modified clone is not possible: changing a signed app invalidates its cryptographic seal.

## Passwords, cookies, and iCloud Keychain

Borderless mode uses Arc's normal profile and Arc's normal **Arc Safe Storage** Keychain item. There is no password CSV migration and no second password database to keep synchronized.

The running browser retains Arc's official bundle identifier, developer Team ID, and Apple's `com.apple.developer.web-browser.public-key-credential` entitlement. This is the entitlement used for the native **Touch ID to Use Passkey** sheet. Apple's iCloud Passwords extension can also be used as it is in regular Arc.

The installer does not read, export, copy, or rewrite passwords, cookies, passkeys, or Keychain secrets.

## Updating Arc

Let official Arc receive its normal Chromium and security updates. After Arc updates, run the latest Arc Borderless installer again.

The launcher records the exact verified Arc executable it was built for. If Arc changes, Borderless mode refuses to load the old patch and asks you to rerun the installer. This prevents an outdated private-interface patch from opening your real profile on an untested Arc build.

The installer keeps an existing launcher until the replacement builds and passes its startup test. Arc's profile is not part of that replacement.

## Upgrading from the earlier clone version

The new signed mode uses your normal Arc profile. The earlier isolated profile is retained at:

`~/Library/Application Support/Arc Borderless`

It is not deleted or merged automatically. Chromium profiles cannot be safely combined as whole folders. Keep the old profile as a recovery copy until you have confirmed that everything you need is present in regular Arc.

A backup of the replaced launcher or clone app is stored under:

`~/Library/Application Support/Arc Borderless Backups`

## Manual commands

Most people should use the double-click installer. Developers can run:

```sh
python3 borderless.py check
python3 borderless.py install
python3 borderless.py status
python3 borderless.py uninstall
```

`check` performs a read-only signature and compatibility check. `install` builds and tests the launcher. `status` shows which Arc build the launcher expects. `uninstall` moves only the launcher to the Trash and retains recovery data.

## Requirements

- macOS with official Arc installed in `/Applications`
- Apple Silicon, which is the currently tested platform
- Python 3.9 or newer
- Apple's free Command Line Tools

## Limitations

- Arc and Borderless mode cannot run at the same time.
- Arc's native interface classes are private and may change in a Chromium or security update. Rerun the installer after every Arc update.
- The launcher uses `DYLD_INSERT_LIBRARIES` to load the local borderless library into Arc. This works because the current official Arc build allows compatible local libraries; a future Arc security-policy change could block it.
- The official Arc application is discontinued except for Chromium and security maintenance, but compatibility still must be checked for every released build.
- Native passkey eligibility is preserved and the entitlement is verified during development. Individual passkey providers, websites, and account policies may still affect a login.
- This project is tested on Apple Silicon; Intel Macs have not been verified.

## Privacy and distribution

The repository and release contain patch and installer source only. They do not contain Arc, Chromium, browser profiles, credentials, cookies, passwords, or passkeys. The installer uses the Arc copy already installed on the user's Mac.

Do not distribute a modified Arc application. Arc and its bundled components remain the property of their respective owners.

## License

The launcher, installer, and patch source in this repository are available under the [MIT License](LICENSE). This license does not grant rights to Arc or any files installed with Arc.

## Development checks

```sh
python3 -m unittest discover -s tests -v
```

See [VALIDATION.md](VALIDATION.md) for the currently verified Arc build and test boundaries.
