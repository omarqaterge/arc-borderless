#!/bin/zsh

# Friendly entry point for people who are not comfortable with Terminal.
set -uo pipefail
cd -- "${0:A:h}"

APP="$HOME/Applications/Arc Borderless.app"
SOURCE_APP="/Applications/Arc.app"

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

This installer adds Borderless mode to your official Arc without modifying
Arc's application files. Borderless mode uses your normal Arc profile.
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

cat <<'INSTALL'

The installer will now:
  1. Quit Arc so the startup test can run safely.
  2. Verify Arc's official signature and browser compatibility.
  3. Install a small Arc Borderless launcher in your Applications folder.
  4. Test Borderless mode without opening your real profile.

Arc itself and your Arc profile will not be copied, patched or replaced.
If you used an older isolated Arc Borderless clone, its profile will be kept
as a recovery copy.
INSTALL
printf '\nPress Return to continue, or close this window to cancel. '
read -r
python3 borderless.py install \
  || stop "The installation failed safely. Arc and any existing Arc Borderless installation were not replaced. Review the message above."

printf '\nSuccess! Arc Borderless is ready.\n'
open "$APP"
printf 'Borderless mode is opening your normal Arc profile now. Run this installer again after Arc updates.\n'
finish
