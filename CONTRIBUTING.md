# Contributing

Bug reports and pull requests are welcome. Include the macOS version, Mac
architecture, Arc version and build number, the installer command, and the
non-sensitive error message.

Never upload an Arc application bundle, browser profile, cookies, saved-login
database, Keychain export, runtime log containing browsing data, or other
proprietary/private data.

Run the tests before submitting a change:

```sh
python3 -m unittest discover -s tests -v
python3 borderless.py check
```

The second command requires an official Arc installation at
`/Applications/Arc.app` unless `--source` is supplied.
