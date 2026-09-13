#!/bin/zsh

# Friendly entry point for people who are not comfortable with Terminal.
set -uo pipefail
cd -- "${0:A:h}"

APP="$HOME/Applications/Arc Borderless.app"
PROFILE="$HOME/Library/Application Support/Arc Borderless"
SOURCE_APP="/Applications/Arc.app"
SOURCE_PROFILE="$HOME/Library/Application Support/Arc"
SOURCE_PREFERENCES="$HOME/Library/Preferences/company.thebrowser.Browser.plist"

finish() {
  printf '\nPress Return to close this window. '
  read -r
}

stop() {
  printf '\nInstallation stopped: %s\n' "$1"
  finish
  exit 1
}

clear
cat <<'WELCOME'
Arc Borderless Installer
========================

This installer creates a separate Arc Borderless browser. Your official Arc
application stays unchanged.
WELCOME

[[ "$(uname -s)" == "Darwin" ]] || stop "This installer requires macOS."
[[ -d "$SOURCE_APP" ]] || stop "Official Arc was not found in Applications. Install Arc first, open it once, and run this installer again."

if ! xcrun --find clang >/dev/null 2>&1; then
  cat <<'TOOLS'

Apple's free Command Line Tools are required to build the local patch.
macOS will now offer to install them. When that installation finishes,
double-click this installer again.
TOOLS
  xcode-select --install >/dev/null 2>&1 || true
  finish
  exit 0
fi

command -v python3 >/dev/null 2>&1 || stop "Python 3 was not found. Reinstall Apple's Command Line Tools and try again."
python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))' \
  || stop "Python 3.9 or newer is required. Update Apple's Command Line Tools and try again."

if [[ -e "$APP" || -e "$PROFILE" ]]; then
  [[ -d "$APP" && -d "$PROFILE" ]] \
    || stop "Only part of an earlier installation was found. See the troubleshooting section in README.md before continuing."
  cat <<'UPDATE'

An existing Arc Borderless installation was found.
This will rebuild it from your current official Arc while keeping its profile.
Both the app and profile will be backed up first.
UPDATE
  printf '\nPress Return to continue, or close this window to cancel. '
  read -r
  python3 borderless.py update || stop "The update failed safely. Your existing Arc Borderless installation was not replaced. Review the message above."
else
  [[ -d "$SOURCE_PROFILE/User Data" ]] \
    || stop "Arc profile data was not found. Open official Arc once, finish its setup, quit it, and run this installer again."
  cat <<'CREATE'

The installer will now:
  1. Quit official Arc so its data can be copied safely.
  2. Create Arc Borderless in your Applications folder.
  3. Copy your Arc profile, including Spaces, folders, tabs and local logins.
  4. Test the copy before installing it.

macOS may ask whether the new browser can use an Arc Safe Storage Keychain
item. Choose Allow so copied website cookies and saved logins can be read.
CREATE
  printf '\nPress Return to continue, or close this window to cancel. '
  read -r
  python3 borderless.py create \
    --source-data "$SOURCE_PROFILE" \
    --preferences "$SOURCE_PREFERENCES" \
    --quit-source \
    || stop "The installation failed safely. Official Arc and its profile were not modified. Review the message above."
fi

printf '\nSuccess! Arc Borderless is ready.\n'
open "$APP"
printf 'The browser is opening now. Use this same installer after official Arc updates.\n'
finish
