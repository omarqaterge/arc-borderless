#!/usr/bin/env python3
"""Build, migrate, validate and update an isolated Arc Borderless installation."""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
SOURCE_ID = 'company.thebrowser.Browser'
SOURCE_REQUIREMENT = 'anchor apple generic and certificate leaf[subject.OU] = "S6N382Y83G" and identifier "company.thebrowser.Browser"'
DEFAULT_ROOT = Path.home() / 'Library/Application Support/Arc Borderless'
DEFAULT_APP = Path.home() / 'Applications/Arc Borderless.app'
UI_SYMBOLS = [b'18ViewWithScrimInset', b'SplitViewContentPaneView',
              b'WindowContentViewController', b'SplitViewDraggerHandleView',
              b'SplitViewBottomDraggerHandleView', b'DraggingDestinationForwardingView']

class Failure(Exception):
    pass

def run(*args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)

def read_plist(path):
    return plistlib.loads(Path(path).read_bytes())

def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def clone(source, target):
    source, target = Path(source), Path(target)
    if target.exists() or target.is_symlink():
        raise Failure(f'Destination already exists: {target}')
    # APFS copy-on-write is efficient without creating writable hard links.
    result = subprocess.run(['/bin/cp', '-cR', str(source), str(target)], capture_output=True)
    if result.returncode:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, symlinks=True)

def app_info(app):
    return read_plist(Path(app) / 'Contents/Info.plist')

def preflight(app):
    app = Path(app).resolve()
    info = app_info(app)
    if info.get('CFBundleIdentifier') != SOURCE_ID:
        raise Failure('Build source must be official Arc, not a previously patched clone.')
    if (app / 'Contents/MacOS/ArcOriginal').exists():
        raise Failure('Source app has already been patched.')
    verification = subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', '-R', '=' + SOURCE_REQUIREMENT, str(app)], capture_output=True)
    if verification.returncode:
        if b'resource fork, Finder information' not in verification.stderr:
            raise Failure('Source signature verification failed: ' + verification.stderr.decode().strip())
        # Finder metadata can invalidate strict checks without changing signed code.
        # Normalize ONLY a disposable copy, then verify the original developer seal.
        with tempfile.TemporaryDirectory(prefix='arc-signature-') as td:
            clean = Path(td) / 'Arc.app'
            clone(app, clean)
            run('xattr', '-cr', clean)
            run('/usr/bin/codesign', '--verify', '--deep', '--strict', '-R', '=' + SOURCE_REQUIREMENT, clean, capture_output=True)
    signature = run('/usr/bin/codesign', '-dv', '--verbose=4', app, capture_output=True).stderr.decode()
    if 'TeamIdentifier=S6N382Y83G' not in signature:
        raise Failure('Source does not have the expected Arc developer signature.')
    binary = app / 'Contents/MacOS' / info['CFBundleExecutable']
    data = binary.read_bytes()
    if any(symbol not in data for symbol in UI_SYMBOLS):
        raise Failure('Expected Arc UI classes are missing. This build needs a new patch.')
    return {'version': info['CFBundleShortVersionString'], 'build': str(info['CFBundleVersion']),
            'sourceSHA256': sha(binary), 'source': str(app), 'staticCompatible': True}

def build_tools():
    bindir = HERE / 'bin'
    bindir.mkdir(exist_ok=True)
    for name in ('Launcher', 'Manager'):
        source, dest = HERE / 'src' / (name + '.m'), bindir / name.lower()
        dependencies = [source]
        if dest.exists() and dest.stat().st_mtime >= max(p.stat().st_mtime for p in dependencies):
            continue
        run('xcrun', 'clang', '-fobjc-arc', '-Wno-deprecated-declarations', '-framework', 'Cocoa',
            '-framework', 'Security', '-lsqlite3', source, '-o', dest)
    return bindir

def config(app):
    return read_plist(Path(app) / 'Contents/Resources/Borderless.plist')

def build_app(source, target, root, identity):
    info = preflight(source)
    build_tools()
    clone(source, target)
    contents = Path(target) / 'Contents'
    p = app_info(target)
    executable = contents / 'MacOS' / p['CFBundleExecutable']
    executable.rename(contents / 'MacOS/ArcOriginal')
    shutil.copy2(HERE / 'bin/launcher', executable)
    p.update(CFBundleIdentifier=identity['bundleID'], CFBundleName='Arc',
             CFBundleDisplayName='Arc Borderless', SUAutomaticallyUpdate=False,
             SUEnableAutomaticChecks=False, SUAllowsAutomaticUpdates=False)
    p.pop('SUFeedURL', None)
    # Do not register the clone as a handler or replace the user's default browser.
    p.pop('CFBundleURLTypes', None)
    p.pop('CFBundleDocumentTypes', None)
    (contents / 'Info.plist').write_bytes(plistlib.dumps(p))
    cfg = dict(identity, dataRoot=str(Path(root).resolve()), sourceInfo=info, formatVersion=1)
    (contents / 'Resources/Borderless.plist').write_bytes(plistlib.dumps(cfg))
    run('xcrun', 'clang', '-dynamiclib', '-fobjc-arc', '-Wno-deprecated-declarations',
        '-framework', 'Cocoa', '-framework', 'CloudKit', '-framework', 'Security',
        '-framework', 'QuartzCore', '-lsqlite3', HERE / 'src/Borderless.m', '-o', contents / 'Frameworks/ArcBorderless.dylib')
    run('xattr', '-cr', target)
    run('codesign', '--force', '--sign', '-', contents / 'MacOS/ArcOriginal', capture_output=True)
    run('codesign', '--force', '--deep', '--sign', '-', target, capture_output=True)
    run('codesign', '--verify', '--deep', '--strict', target, capture_output=True)
    return cfg

def source_users(source_data):
    needle = str(Path(source_data).resolve())
    lines = run('ps', '-axo', 'pid=,command=', capture_output=True, text=True).stdout.splitlines()
    return [int(line.split(None, 1)[0]) for line in lines
            if needle in line and '/Contents/MacOS/' in line and '--user-data-dir=' in line]

def assert_closed(data, app=None):
    users = source_users(data)
    if app:
        appneedle = str(Path(app).resolve()) + '/Contents/'
        lines = run('ps', '-axo', 'pid=,comm=', capture_output=True, text=True).stdout.splitlines()
        users += [int(x.split(None, 1)[0]) for x in lines if appneedle in x]
    if users:
        raise Failure(f'Browser processes still use the source (PIDs {sorted(set(users))}). Quit it normally and retry.')

def quit_app(app):
    run(build_tools() / 'manager', 'quit', app)
    # Chromium helpers may take a little longer to release the databases.
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        lines = run('ps', '-axo', 'comm=', capture_output=True, text=True).stdout.splitlines()
        if not any(str(Path(app).resolve()) + '/Contents/' in x for x in lines):
            return
        time.sleep(.25)
    raise Failure('Browser helpers are still running; the profile has not been copied.')

def data_dir(root):
    return Path(root) / 'home/Library/Application Support/Arc'

def tree_manifest(path):
    out = {}
    for p in sorted(Path(path).rglob('*')):
        if p.is_symlink():
            continue
        if p.is_file():
            out[str(p.relative_to(path))] = [p.stat().st_size, sha(p)]
    return out

def prepare_profile(root, source=None, preferences=None):
    root = Path(root)
    root.mkdir(mode=0o700)
    (root / '.borderless-profile').write_text('1\n')
    target = data_dir(root)
    target.parent.mkdir(parents=True)
    if source:
        if not (Path(source) / 'User Data').is_dir():
            raise Failure('Source must contain the Chromium User Data directory.')
        for entry in Path(source).rglob('*'):
            if entry.is_symlink() and str(entry.relative_to(source)) not in {
                'User Data/SingletonLock', 'User Data/SingletonCookie', 'User Data/SingletonSocket'}:
                raise Failure('Linked profile files need explicit migration handling: ' + str(entry))
        before = tree_manifest(source)
        clone(source, target)
        if before != tree_manifest(source) or before != tree_manifest(target):
            raise Failure('Source changed during copying or the copy differs. Migration stopped.')
    else:
        target.mkdir()
        (target / 'User Data').mkdir()
    # Stale Chromium singleton links are never meaningful in a cloned profile.
    for name in ('SingletonLock', 'SingletonCookie', 'SingletonSocket', 'DevToolsActivePort'):
        p = target / 'User Data' / name
        if p.exists() or p.is_symlink():
            p.unlink()
    prefsdir = root / 'home/Library/Preferences'
    prefsdir.mkdir(parents=True, exist_ok=True)
    if preferences and Path(preferences).is_file():
        shutil.copy2(preferences, prefsdir / (SOURCE_ID + '.plist'))
    return inventory(target)

def configure_preferences(root, cfg):
    prefs = Path(root) / 'home/Library/Preferences'
    prefs.mkdir(parents=True, exist_ok=True)
    original = prefs / (SOURCE_ID + '.plist')
    values = read_plist(original) if original.exists() else {}
    values.update(SUAutomaticallyUpdate=False, SUEnableAutomaticChecks=False)
    (prefs / (cfg['bundleID'] + '.plist')).write_bytes(plistlib.dumps(values))


def inventory(data):
    data = Path(data)
    result = {'sidebarSHA256': None, 'profiles': {}}
    sidebar = data / 'StorableSidebar.json'
    if sidebar.exists():
        json.loads(sidebar.read_text())
        result['sidebarSHA256'] = sha(sidebar)
    for folder in sorted((data / 'User Data').glob('*')):
        if not folder.is_dir():
            continue
        counts = {}
        for rel, table in [('Cookies', 'cookies'), ('Network/Cookies', 'cookies'), ('Login Data', 'logins'), ('History', 'urls')]:
            db = folder / rel
            if db.is_file():
                with contextlib.closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as conn:
                    if conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise Failure('Copied database failed integrity check: ' + str(db))
                    counts[rel] = conn.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        if counts:
            result['profiles'][folder.name] = counts
    return result

def migrate_key(service, cfg, app):
    run(build_tools() / 'manager', 'migrate-key', service,
        cfg['keychainNamespace'] + 'Arc Safe Storage', app)
    if service == 'ArcBorderlessTest/Arc Safe Storage':
        run(build_tools() / 'manager', 'migrate-test-auth', 'ArcBorderlessTest/', cfg['keychainNamespace'], app)

def validate(app, root, seconds=60, require_browser=False, require_encryption=False):
    root = Path(root)
    report = root / 'runtime-report.json'
    report.unlink(missing_ok=True)
    run(build_tools() / 'manager', 'assert-id-idle', config(app)['bundleID'])
    exe = Path(app) / 'Contents/MacOS' / app_info(app)['CFBundleExecutable']
    with (root / 'runtime.log').open('w') as log:
        launch_args = [str(exe), '--borderless-probe-root', str(root.resolve()), '--borderless-report', str(report.resolve())]
        if require_encryption:
            launch_args.append('--borderless-verify-encryption')
        process = subprocess.Popen(launch_args, stdout=log, stderr=log,
                                   start_new_session=True)
        try:
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise Failure(f'Candidate exited with {process.returncode}. See {root / "runtime.log"}')
                if report.exists():
                    result = json.loads(report.read_text())
                    if result.get('hooksInstalled') and result.get('windows', 0) > 0 and (not require_browser or result.get('browserWindows', 0) > 0) and (not require_encryption or result.get('encryptionVerified')):
                        if result.get('home') != str(root.resolve() / 'home'):
                            raise Failure('Runtime home isolation check failed.')
                        return result
                time.sleep(.25)
            raise Failure('Candidate did not report a successful startup before the timeout.')
        except BaseException:
            diagnostics = HERE / 'diagnostics' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            diagnostics.mkdir(parents=True, mode=0o700)
            log.flush()
            shutil.copy2(root / 'runtime.log', diagnostics / 'runtime.log')
            if report.exists():
                shutil.copy2(report, diagnostics / 'runtime-report.json')
            print('Private diagnostics retained:', diagnostics, flush=True)
            raise
        finally:
            if process.poll() is None:
                try:
                    quit_app(app)
                except (Failure, subprocess.SubprocessError):
                    # This is ONLY our disposable candidate process group, never the user's browser.
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)

def independent_paths(app, root, source, source_data=None):
    paths = [Path(x).expanduser().resolve() for x in [app, root, source] + ([source_data] if source_data else [])]
    for i, a in enumerate(paths):
        for b in paths[i + 1:]:
            if a == b or a in b.parents or b in a.parents:
                raise Failure('App, data root, source app and source data must be separate, non-nested paths.')

def new_identity():
    token = uuid.uuid4().hex
    return {'bundleID': 'local.arc-borderless.' + token, 'keychainNamespace': 'ArcBorderless/' + token + '/'}

@contextlib.contextmanager
def operation_lock(root):
    root = Path(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    lock = root.with_name('.' + root.name + '.installer.lock')
    with lock.open('a') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Failure('Another installer operation is already running.')
        yield

def create(args):
    app, root, source = args.app.resolve(), args.root.resolve(), args.source.resolve()
    source_data = args.source_data.resolve() if args.source_data else None
    independent_paths(app, root, source, source_data)
    if app.exists() or root.exists():
        raise Failure('Destination exists. Use update; creation never overwrites an existing app or profile.')
    app.parent.mkdir(parents=True, exist_ok=True)
    with operation_lock(root), tempfile.TemporaryDirectory(prefix='.arc-borderless-', dir=app.parent) as temp:
        temp = Path(temp)
        staged = temp / 'Arc Borderless.app'
        cfg = build_app(source, staged, root, new_identity())
        probe = temp / 'probe'
        if source_data:
            if args.quit_source:
                quit_app(args.source_app or source)
            assert_closed(source_data, args.source_app or source)
        snapshot = temp / 'snapshot'
        stats = prepare_profile(snapshot, source_data, args.preferences)
        configure_preferences(snapshot, cfg)
        clone(snapshot, probe)
        if source_data:
            migrate_key(args.source_key_service, cfg, staged)
        # Preserve the unlaunched snapshot for installation; only probe is opened.
        print('Validating candidate in a disposable profile copy...', flush=True)
        runtime = validate(staged, probe, require_browser=args.source_key_service == 'ArcBorderlessTest/Arc Safe Storage' and bool(source_data), require_encryption=bool(source_data))
        # Validation may modify the disposable copy. Install a pristine source snapshot.
        try:
            clone(snapshot, root)
            atomic_json(root / 'installation.json', dict(cfg, app=str(app), migration=stats,
                        runtime=runtime, created=datetime.datetime.now().isoformat()))
            staged.rename(app)
        except BaseException:
            # This is an unpublished snapshot created by this operation, not existing user data.
            if root.exists() and not app.exists():
                shutil.rmtree(root)
            raise
        print('Created:', app, '\nData:', root, '\nSource app and profile were not modified.')

def update(args):
    app = args.app.resolve()
    cfg = config(app)
    root = Path(cfg['dataRoot'])
    independent_paths(app, root, args.source)
    newinfo = preflight(args.source)
    if int(newinfo['build']) < int(cfg['sourceInfo']['build']):
        raise Failure('Downgrades are refused; newer Chromium profiles may not be backward compatible.')
    with operation_lock(root), tempfile.TemporaryDirectory(prefix='.arc-borderless-', dir=app.parent) as temp:
        temp = Path(temp)
        staged = temp / 'Arc Borderless.app'
        newcfg = build_app(args.source, staged, root, cfg_identity(cfg))
        quit_app(app)
        assert_closed(data_dir(root), app)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = root.parent / (root.name + ' Backups') / stamp
        backup.mkdir(parents=True, mode=0o700)
        clone(root, backup / 'profile')
        clone(app, backup / 'Arc Borderless.app')
        atomic_json(backup / 'backup.json', {'app': str(app), 'root': str(root), 'build': cfg['sourceInfo']['build']})
        probe = temp / 'probe'
        clone(root, probe)
        runtime = validate(staged, probe, require_browser=True, require_encryption=True)
        assert_closed(data_dir(root), app)
        old = temp / 'old.app'
        app.rename(old)
        try:
            staged.rename(app)
            previous = json.loads((root / 'installation.json').read_text()) if (root / 'installation.json').exists() else {}
            previous.update(dict(newcfg, app=str(app), runtime=runtime, updated=datetime.datetime.now().isoformat(), backup=str(backup)))
            atomic_json(root / 'installation.json', previous)
        except BaseException:
            if app.exists():
                shutil.rmtree(app)
            old.rename(app)
            raise
        print('Updated:', app, '\nExisting profile retained. Matched app/profile backup:', backup)

def cfg_identity(cfg):
    return {key: cfg[key] for key in ['bundleID', 'keychainNamespace']}

def rollback(args):
    backup = args.backup.resolve()
    meta = json.loads((backup / 'backup.json').read_text())
    app, root = Path(meta['app']), Path(meta['root'])
    if config(app)['bundleID'] != config(backup / 'Arc Borderless.app')['bundleID']:
        raise Failure('Backup belongs to a different clone.')
    with operation_lock(root):
        quit_app(app)
        assert_closed(data_dir(root), app)
        # Keep current app AND current profile; rollback never discards newer browsing data.
        preserved = backup.parent / ('Before-rollback-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        preserved.mkdir(mode=0o700)
        clone(app, preserved / 'Arc Borderless.app')
        clone(root, preserved / 'profile')
        atomic_json(preserved / 'backup.json', meta)
        with tempfile.TemporaryDirectory(prefix='.arc-rollback-', dir=app.parent) as td:
            staged = Path(td) / 'app'
            clone(backup / 'Arc Borderless.app', staged)
            old = Path(td) / 'old'
            app.rename(old)
            try:
                staged.rename(app)
                replacement = root.with_name(root.name + '.restore-' + uuid.uuid4().hex)
                clone(backup / 'profile', replacement)
                displaced = root.with_name(root.name + '.displaced-' + uuid.uuid4().hex)
                root.rename(displaced)
                try:
                    replacement.rename(root)
                except BaseException:
                    displaced.rename(root)
                    raise
                # Cleanup failure must not roll back only the app after the pair committed.
                shutil.rmtree(displaced, ignore_errors=True)
            except BaseException:
                if app.exists():
                    shutil.rmtree(app)
                old.rename(app)
                raise
        print('Restored matched app/profile snapshot. Newer data preserved at:', preserved)

def uninstall(args):
    app = args.app.resolve()
    cfg = config(app)
    root = Path(cfg['dataRoot'])
    if not cfg['bundleID'].startswith('local.arc-borderless.'):
        raise Failure('This is not a clone managed by this installer.')
    with operation_lock(root):
        quit_app(app)
        assert_closed(data_dir(root), app)
        trash = Path.home() / '.Trash'
        trash.mkdir(exist_ok=True)
        target = trash / ('Arc Borderless-' + uuid.uuid4().hex[:8] + '.app')
        app.rename(target)
        print('App moved to Trash. Profile, backups, and isolated Keychain items retained:', root)


def main():
    if sys.platform != 'darwin':
        raise Failure('macOS is required.')
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    check = sub.add_parser('check', help='Read-only signature and static compatibility check')
    check.add_argument('--source', type=Path, default=Path('/Applications/Arc.app'))
    for action in ('create', 'update'):
        c = sub.add_parser(action)
        c.add_argument('--source', type=Path, default=Path('/Applications/Arc.app'))
        c.add_argument('--app', type=Path, default=DEFAULT_APP)
        if action == 'create':
            c.add_argument('--root', type=Path, default=DEFAULT_ROOT)
            group = c.add_mutually_exclusive_group(required=True)
            group.add_argument('--source-data', type=Path, help='Arc application support directory containing User Data and StorableSidebar.json')
            group.add_argument('--empty', action='store_true', help='Create a fresh profile without credential migration')
            c.add_argument('--source-app', type=Path, help='App using source data, if different from official Arc')
            c.add_argument('--preferences', type=Path)
            c.add_argument('--source-key-service', default='Arc Safe Storage')
            c.add_argument('--quit-source', action='store_true', help='Quit source normally to take a consistent snapshot')
    c = sub.add_parser('rollback')
    c.add_argument('backup', type=Path)
    c = sub.add_parser('uninstall')
    c.add_argument('--app', type=Path, default=DEFAULT_APP)
    c = sub.add_parser('status')
    c.add_argument('--app', type=Path, default=DEFAULT_APP)
    args = p.parse_args()
    if args.action == 'check':
        print(json.dumps(preflight(args.source), indent=2))
    elif args.action == 'status':
        print(json.dumps(config(args.app), indent=2))
    else:
        globals()[args.action](args)

if __name__ == '__main__':
    try:
        main()
    except (Failure, OSError, ValueError, subprocess.SubprocessError, sqlite3.Error) as e:
        print('Stopped:', e, file=sys.stderr)
        sys.exit(1)
