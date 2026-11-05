#!/usr/bin/env python3
"""Install a reversible macOS Chrome launcher without modifying Chrome or profiles."""
import argparse
import datetime
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import urllib.parse


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs)


def export_dock():
    return run('/usr/bin/defaults', 'export', 'com.apple.dock', '-').stdout


def prepare(home, chrome):
    app = home / 'Applications/Chrome AI.app'
    if app.exists():
        raise RuntimeError('Launcher already exists; preserve it and inspect before replacing')
    profile = home / 'Library/Application Support/Google/Chrome/Default'
    state = json.loads((profile.parent / 'Local State').read_text())
    if not profile.is_dir() or not state['profile']['info_cache']['Default'].get('user_name'):
        raise RuntimeError('Existing signed-in Default profile required')
    if not (chrome / 'Contents/MacOS/Google Chrome').is_file():
        raise RuntimeError('Existing Chrome application required')
    # AppleScript application is handled by LaunchServices and works from Dock/Finder.
    command = ['/usr/bin/open', '-a', str(chrome), '--args',
               '--silent-debugger-extension-api', '--restore-last-session',
               '--profile-directory=Default']
    import shlex
    shell = shlex.join(command)
    literal = json.dumps(shell)
    script = 'on run\n do shell script ' + literal + '\nend run\n'
    app.parent.mkdir(parents=True, exist_ok=True)
    run('/usr/bin/osacompile', '-o', str(app), input=script.encode())
    info = app / 'Contents/Info.plist'
    pl = plistlib.loads(info.read_bytes())
    pl.update(CFBundleIdentifier='com.expertpartners.chrome-quiet-launcher',
              CFBundleName='Chrome AI', CFBundleDisplayName='Chrome AI')
    info.write_bytes(plistlib.dumps(pl))
    icon = chrome / 'Contents/Resources/app.icns'
    if icon.exists():
        shutil.copyfile(icon, app / 'Contents/Resources/applet.icns')
    print(json.dumps({'prepared_app': str(app), 'chrome_untouched': True,
                      'launch_arguments': command, 'restart_performed': False}))


def install(home, receipt):
    app = home / 'Applications/Chrome AI.app'
    if not app.is_dir():
        raise RuntimeError('Prepare the launcher first')
    receipt.mkdir(parents=True, exist_ok=False)
    agent = home / 'Library/LaunchAgents/com.expertpartners.chrome-quiet.plist'
    if agent.exists():
        shutil.copy2(agent, receipt / 'launchagent.before.plist')
    before = export_dock()
    (receipt / 'dock.before.plist').write_bytes(before)
    dock = plistlib.loads(before)
    replaced = 0
    target = app.as_uri() + '/'
    for tile in dock.get('persistent-apps', []):
        data = tile.get('tile-data', {})
        url = urllib.parse.unquote(data.get('file-data', {}).get('_CFURLString', ''))
        if url.rstrip('/') == 'file:///Applications/Google Chrome.app':
            replaced += 1
            data['file-data'] = {'_CFURLString': target, '_CFURLStringType': 15}
            data['file-label'] = 'Chrome AI'
            data['bundle-identifier'] = 'com.expertpartners.chrome-quiet-launcher'
            for key in ['book', 'file-bookmark', 'parent-bookmark']:
                data.pop(key, None)
    if replaced != 1:
        raise RuntimeError('Expected exactly one stock Chrome Dock tile; no config written')
    # Fresh guard against replacing concurrent Dock changes during preparation.
    if plistlib.loads(export_dock()) != plistlib.loads(before):
        raise RuntimeError('Dock changed during preparation; no config written')
    updated = receipt / 'dock.after.plist'
    updated.write_bytes(plistlib.dumps(dock))
    (receipt / 'manifest.json').write_text(json.dumps({'app': str(app), 'agent': str(agent),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'dock_tiles_replaced': replaced}, indent=2))
    run('/usr/bin/defaults', 'import', 'com.apple.dock', str(updated))
    agent.parent.mkdir(parents=True, exist_ok=True)
    agent.write_bytes(plistlib.dumps({'Label': 'com.expertpartners.chrome-quiet',
        'ProgramArguments': ['/usr/bin/open', str(app)], 'RunAtLoad': True}))
    os.chmod(agent, 0o644)
    run('/usr/bin/plutil', '-lint', str(agent))
    print(json.dumps({'installed': True, 'backup': str(receipt), 'restart_performed': False}))


def rollback(home, receipt):
    manifest = json.loads((receipt / 'manifest.json').read_text())
    agent = Path(manifest['agent'])
    # Restores only this owned tile, preserving subsequent changes to other Dock tiles.
    current = plistlib.loads(export_dock())
    original = plistlib.loads((receipt / 'dock.before.plist').read_bytes())
    stock = [t for t in original['persistent-apps'] if urllib.parse.unquote(
        t.get('tile-data', {}).get('file-data', {}).get('_CFURLString', '')
    ).rstrip('/') == 'file:///Applications/Google Chrome.app']
    for i, tile in enumerate(current.get('persistent-apps', [])):
        if tile.get('tile-data', {}).get('bundle-identifier') == 'com.expertpartners.chrome-quiet-launcher':
            current['persistent-apps'][i] = stock[0]
    restored = receipt / 'dock.rollback.plist'
    restored.write_bytes(plistlib.dumps(current))
    run('/usr/bin/defaults', 'import', 'com.apple.dock', str(restored))
    old = receipt / 'launchagent.before.plist'
    if old.exists():
        shutil.copy2(old, agent)
    else:
        agent.unlink(missing_ok=True)
    print(json.dumps({'restored_configuration': True, 'launcher_retained': manifest['app'],
                      'restart_performed': False}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'install', 'rollback'])
    p.add_argument('--receipt', type=Path)
    a = p.parse_args()
    home = Path.home()
    if a.action == 'prepare':
        prepare(home, Path('/Applications/Google Chrome.app'))
    else:
        if a.receipt is None:
            p.error('--receipt is required')
        globals()[a.action](home, a.receipt.resolve())
