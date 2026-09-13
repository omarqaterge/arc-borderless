#!/bin/zsh
set -eu
cd -- "${0:A:h}"
python3 borderless.py create --source-data "$HOME/Library/Application Support/Arc" --preferences "$HOME/Library/Preferences/company.thebrowser.Browser.plist" --quit-source
