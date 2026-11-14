"""Build an isolated, locally signed app copy; never modify the source app."""
import argparse
import hashlib
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools/sumerki'))
from build_patch import build

SENTINEL = b'AGbevlPCksUGKNL8TSn7wGmJEuJsXb2A'

def dictionary_digest(info):
    integrity = info['ElectronAsarIntegrity']
    return hashlib.sha256(b''.join((k + v['algorithm'] + v['hash']).encode()
                                  for k, v in sorted(integrity.items()))).digest()

def update_digest(data, old, new):
    result = bytearray(data)
    positions = []
    start = 0
    while True:
        i = result.find(SENTINEL, start)
        if i < 0:
            break
        n = i + len(SENTINEL)
        if result[n:n+2] == b'\x01\x01' and result[n+2:n+34] == old:
            positions.append(n+2)
        start = i + len(SENTINEL)
    if len(positions) != 1:
        raise ValueError('Expected exactly one original integrity-dictionary slot; unsupported build')
    n = positions[0]
    result[n:n+32] = new
    return bytes(result)

def run(*args):
    subprocess.run(args, check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/Applications/ChatGPT.app'))
    args = parser.parse_args()
    source = args.source.resolve()
    info = plistlib.loads((source/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleVersion') != '27194' or info.get('CFBundleShortVersionString') != '26.1111.21308':
        raise SystemExit('This prototype only supports build 26.1111.21308 / 27194')
    destination = ROOT/'work/ChatGPT Theme Test.app'
    if destination.exists():
        raise SystemExit('Test copy already exists; move it aside before rebuilding')
    output = ROOT/'work/bundled-theme-candidate'
    output.mkdir(parents=True, exist_ok=True)
    build(source, ROOT/'tools/sumerki/theme.css', output)
    run('/bin/cp', '-cR', str(source), str(destination))
    shutil.copyfile(output/'app.asar', destination/'Contents/Resources/app.asar')
    patched = plistlib.loads((output/'Info.plist').read_bytes())
    # Keep original bundle metadata; isolation is explicit in patched_runner.py.
    (destination/'Contents/Info.plist').write_bytes(plistlib.dumps(patched, fmt=plistlib.FMT_XML, sort_keys=False))
    framework = (destination/'Contents/Frameworks/Codex Framework.framework/Versions/Current/Codex Framework').resolve()
    if not framework.is_relative_to(destination.resolve()):
        raise SystemExit('Framework resolves outside the test bundle')
    framework.write_bytes(update_digest(framework.read_bytes(), dictionary_digest(info), dictionary_digest(patched)))
    entitlements = ROOT/'work/theme-test-entitlements.plist'
    entitlements.write_bytes(plistlib.dumps({
        'com.apple.security.cs.allow-jit': True,
        'com.apple.security.cs.allow-unsigned-executable-memory': True,
        'com.apple.security.cs.disable-library-validation': True,
    }))
    run('/usr/bin/codesign', '--force', '--deep', '--sign', '-', '--options', 'runtime',
        '--entitlements', str(entitlements), str(destination))
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', str(destination))
    print('Prepared:', destination)
    print('Launch with: zsh tools/sumerki/Start-patched-test.command')

if __name__ == '__main__':
    main()
