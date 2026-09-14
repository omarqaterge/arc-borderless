#!/usr/bin/env python3
"""Build, validate, install, and remove Arc Borderless signed mode."""
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
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SOURCE_ID = 'company.thebrowser.Browser'
SOURCE_REQUIREMENT = 'anchor apple generic and certificate leaf[subject.OU] = "S6N382Y83G" and identifier "company.thebrowser.Browser"'
DEFAULT_STATE = Path.home() / 'Library/Application Support/Arc Borderless'
DEFAULT_APP = Path.home() / 'Applications/Arc Borderless.app'
SIGNED_BUNDLE_ID = 'local.arc-borderless.launcher'
UI_SYMBOLS = [b'18ViewWithScrimInset', b'SplitViewContentPaneView',
              b'WindowContentViewController', b'SplitViewDraggerHandleView',
              b'SplitViewBottomDraggerHandleView', b'DraggingDestinationForwardingView']

class Failure(Exception):
    pass

def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)

def read_plist(path):
    return plistlib.loads(Path(path).read_bytes())

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def clone(source, target):
    source, target = Path(source), Path(target)
    if target.exists() or target.is_symlink():
        raise Failure(f'Destination already exists: {target}')
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
        raise Failure('The source must be the official Arc application.')
    verification = subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict',
                                   '-R', '=' + SOURCE_REQUIREMENT, str(app)], capture_output=True)
    if verification.returncode:
        if b'resource fork, Finder information' not in verification.stderr:
            raise Failure('Arc signature verification failed: ' + verification.stderr.decode().strip())
        with tempfile.TemporaryDirectory(prefix='arc-signature-') as directory:
            clean = Path(directory) / 'Arc.app'
            clone(app, clean)
            run('xattr', '-cr', clean)
            run('/usr/bin/codesign', '--verify', '--deep', '--strict',
                '-R', '=' + SOURCE_REQUIREMENT, clean, capture_output=True)
    signature = run('/usr/bin/codesign', '-dv', '--verbose=4', app,
                    capture_output=True).stderr.decode()
    if 'TeamIdentifier=S6N382Y83G' not in signature:
        raise Failure('Arc does not have the expected developer signature.')
    binary = app / 'Contents/MacOS' / info['CFBundleExecutable']
    data = binary.read_bytes()
    if any(symbol not in data for symbol in UI_SYMBOLS):
        raise Failure('This Arc build changed the required interface components. No patch was installed.')
    return {'version': info['CFBundleShortVersionString'], 'build': str(info['CFBundleVersion']),
            'sourceSHA256': sha(binary), 'source': str(app), 'staticCompatible': True}

def build_tools():
    binary_directory = HERE / 'bin'
    binary_directory.mkdir(exist_ok=True)
    specifications = {
        'launcher': HERE / 'src/Launcher.m',
        'manager': HERE / 'src/Manager.m',
    }
    for name, source in specifications.items():
        destination = binary_directory / name
        if destination.exists() and destination.stat().st_mtime >= source.stat().st_mtime:
            continue
        run('xcrun', 'clang', '-fobjc-arc', '-Wno-deprecated-declarations',
            '-framework', 'Cocoa', source, '-o', destination)
    return binary_directory

def build_app(source, target):
    source_info = preflight(source)
    tools = build_tools()
    target = Path(target)
    contents = target / 'Contents'
    (contents / 'MacOS').mkdir(parents=True)
    (contents / 'Frameworks').mkdir()
    (contents / 'Resources').mkdir()
    shutil.copy2(tools / 'launcher', contents / 'MacOS/ArcBorderlessLauncher')
    info = {
        'CFBundleDevelopmentRegion': 'en',
        'CFBundleDisplayName': 'Arc Borderless',
        'CFBundleExecutable': 'ArcBorderlessLauncher',
        'CFBundleIdentifier': SIGNED_BUNDLE_ID,
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleName': 'Arc Borderless',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': source_info['build'],
        'LSMinimumSystemVersion': '13.0',
        'NSHighResolutionCapable': True,
    }
    icon = Path(source) / 'Contents/Resources/AppIcon.icns'
    if icon.is_file():
        shutil.copy2(icon, contents / 'Resources/AppIcon.icns')
        info['CFBundleIconFile'] = 'AppIcon'
    (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
    configuration = {'mode': 'signed-single-instance', 'formatVersion': 2,
                     'sourceInfo': source_info}
    (contents / 'Resources/Borderless.plist').write_bytes(plistlib.dumps(configuration))
    library = contents / 'Frameworks/ArcBorderless.dylib'
    run('xcrun', 'clang', '-dynamiclib', '-fobjc-arc', '-Wno-deprecated-declarations',
        '-framework', 'Cocoa', '-framework', 'QuartzCore',
        HERE / 'src/OfficialBorderless.m', '-o', library)
    run('xattr', '-cr', target)
    run('codesign', '--force', '--sign', '-', library, capture_output=True)
    run('codesign', '--force', '--deep', '--sign', '-', target, capture_output=True)
    run('codesign', '--verify', '--deep', '--strict', target, capture_output=True)
    return configuration

def config(app):
    return read_plist(Path(app) / 'Contents/Resources/Borderless.plist')

def quit_app(app):
    run(build_tools() / 'manager', 'quit', Path(app).resolve())

def validate(app, source, seconds=45):
    with tempfile.TemporaryDirectory(prefix='arc-borderless-probe-') as directory:
        probe = Path(directory) / 'User Data'
        probe.mkdir()
        report = Path(directory) / 'runtime-report.json'
        log_path = Path(directory) / 'runtime.log'
        executable = Path(app) / 'Contents/MacOS/ArcBorderlessLauncher'
        with log_path.open('w') as log:
            process = subprocess.Popen([str(executable), '--borderless-probe-root', str(probe),
                                        '--borderless-report', str(report)],
                                       stdout=log, stderr=log, start_new_session=True)
            try:
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise Failure(f'The startup test exited with {process.returncode}.')
                    if report.exists():
                        result = json.loads(report.read_text())
                        if (result.get('hooksInstalled') and result.get('windows', 0) > 0
                                and result.get('officialMode')
                                and result.get('bundleID') == SOURCE_ID):
                            return result
                    time.sleep(.25)
                raise Failure('The startup test did not report success before the timeout.')
            except BaseException:
                diagnostics = HERE / 'diagnostics' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                diagnostics.mkdir(parents=True, mode=0o700)
                log.flush()
                shutil.copy2(log_path, diagnostics / 'runtime.log')
                if report.exists():
                    shutil.copy2(report, diagnostics / 'runtime-report.json')
                print('Private diagnostics retained:', diagnostics, flush=True)
                raise
            finally:
                try:
                    quit_app(source)
                except (Failure, subprocess.SubprocessError):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)

@contextlib.contextmanager
def operation_lock(state):
    state = Path(state)
    state.parent.mkdir(parents=True, exist_ok=True)
    lock = state.with_name('.' + state.name + '.installer.lock')
    with lock.open('a') as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Failure('Another installer operation is already running.')
        yield

def install(args):
    app, source, state = args.app.resolve(), args.source.resolve(), args.state.resolve()
    app.parent.mkdir(parents=True, exist_ok=True)
    with operation_lock(state), tempfile.TemporaryDirectory(prefix='.arc-borderless-', dir=app.parent) as directory:
        staged = Path(directory) / 'Arc Borderless.app'
        configuration = build_app(source, staged)
        if app.exists():
            quit_app(app)
        quit_app(source)
        validate(staged, source)
        backup = None
        if app.exists():
            backup_root = state.parent / (state.name + ' Backups')
            backup = backup_root / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            backup.mkdir(parents=True, mode=0o700)
            clone(app, backup / 'Arc Borderless.app')
        displaced = Path(directory) / 'previous.app'
        if app.exists():
            app.rename(displaced)
        try:
            staged.rename(app)
        except BaseException:
            if displaced.exists():
                displaced.rename(app)
            raise
        atomic_json(state / 'signed-installation.json', {
            **configuration, 'app': str(app), 'installed': datetime.datetime.now().isoformat(),
            'previousAppBackup': str(backup) if backup else None,
            'legacyProfileRetained': (state / 'home').exists(),
        })
        print('Installed signed single-instance launcher:', app)
        print('Official Arc and its profile were not modified.')
        if (state / 'home').exists():
            print('The earlier isolated Borderless profile was retained for recovery:', state)

def uninstall(args):
    app = args.app.resolve()
    configuration = config(app)
    if configuration.get('mode') != 'signed-single-instance':
        raise Failure('This is not a signed-mode installation managed by this installer.')
    quit_app(Path(configuration['sourceInfo']['source']))
    trash = Path.home() / '.Trash'
    trash.mkdir(exist_ok=True)
    destination = trash / ('Arc Borderless-' + uuid_token() + '.app')
    app.rename(destination)
    print('Launcher moved to Trash. Arc, its profile, and recovery data were retained.')

def uuid_token():
    return hashlib.sha256(os.urandom(32)).hexdigest()[:8]

def main():
    if sys.platform != 'darwin':
        raise Failure('macOS is required.')
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    check = commands.add_parser('check', help='Read-only signature and compatibility check')
    check.add_argument('--source', type=Path, default=Path('/Applications/Arc.app'))
    for name in ('install', 'install-signed'):
        command = commands.add_parser(name, help='Install signed single-instance mode')
        command.add_argument('--source', type=Path, default=Path('/Applications/Arc.app'))
        command.add_argument('--app', type=Path, default=DEFAULT_APP)
        command.add_argument('--state', type=Path, default=DEFAULT_STATE)
    status = commands.add_parser('status')
    status.add_argument('--app', type=Path, default=DEFAULT_APP)
    remove = commands.add_parser('uninstall')
    remove.add_argument('--app', type=Path, default=DEFAULT_APP)
    args = parser.parse_args()
    if args.action == 'check':
        print(json.dumps(preflight(args.source), indent=2))
    elif args.action == 'status':
        print(json.dumps(config(args.app), indent=2))
    elif args.action in ('install', 'install-signed'):
        install(args)
    else:
        uninstall(args)

if __name__ == '__main__':
    try:
        main()
    except (Failure, OSError, ValueError, subprocess.SubprocessError) as error:
        print('Stopped:', error, file=sys.stderr)
        sys.exit(1)
