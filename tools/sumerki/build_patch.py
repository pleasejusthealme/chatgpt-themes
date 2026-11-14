"""Build a CSS-only ASAR candidate outside the installed app. Does NOT install or sign it."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import struct


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_header(stream):
    stream.seek(0)
    prefix = stream.read(16)
    if len(prefix) != 16:
        raise ValueError('Truncated ASAR')
    size, header_size, payload_size, length = struct.unpack('<4I', prefix)
    if size != 4 or header_size != payload_size + 4 or length > 64_000_000:
        raise ValueError('Unsupported ASAR header')
    raw = stream.read(length)
    return json.loads(raw), 8 + header_size, raw


def entries(tree, prefix=''):
    for name, value in tree.items():
        path = prefix + name
        if 'files' in value:
            yield from entries(value['files'], path + '/')
        else:
            yield path, value


def pack_header(header):
    raw = json.dumps(header, separators=(',', ':'), ensure_ascii=False).encode()
    padded = raw + b'\0' * ((-len(raw)) % 4)
    pickle = struct.pack('<II', 4 + len(padded), len(raw)) + padded
    return struct.pack('<II', 4, len(pickle)) + pickle, raw


def build(source_app, css_path, output):
    output = output.resolve()
    if output.is_relative_to(source_app.resolve()):
        raise ValueError('Output must be outside the installed application')
    output.mkdir(parents=True, exist_ok=True)
    archive = source_app / 'Contents/Resources/app.asar'
    plist = plistlib.loads((source_app / 'Contents/Info.plist').read_bytes())
    css = css_path.read_text()
    if '</style' in css.lower():
        raise ValueError('CSS contains a closing style tag')
    with archive.open('rb') as stream:
        header, base, raw = read_header(stream)
        expected = plist['ElectronAsarIntegrity']['Resources/app.asar']['hash']
        if sha(raw) != expected:
            raise ValueError('Original ASAR header does not match Info.plist')
        header = copy.deepcopy(header)
        files = dict(entries(header['files']))
        patches, changes = {}, []
        for name in ('webview/index.html', 'webview/detached-window.html'):
            entry = files.get(name)
            if entry is None:
                if name == 'webview/index.html':
                    raise ValueError('Main app document not found')
                continue
            stream.seek(base + int(entry['offset']))
            original = stream.read(entry['size'])
            text = original.decode()
            if 'sumerki-bundled-theme' in text or text.count('</head>') != 1:
                raise ValueError('Unexpected HTML document: ' + name)
            data = text.replace('</head>', '<style id="sumerki-bundled-theme">\n' + css + '\n</style>\n</head>').encode()
            patches[name] = data
            block_size = entry.get('integrity', {}).get('blockSize', 4194304)
            entry['size'] = len(data)
            entry['integrity'] = {'algorithm': 'SHA256', 'hash': sha(data), 'blockSize': block_size,
                                  'blocks': [sha(data[i:i+block_size]) for i in range(0, len(data), block_size)]}
            changes.append({'path': name, 'before': sha(original), 'after': sha(data)})
        ordered = sorted(((name, e, int(e['offset'])) for name, e in files.items()
                          if 'offset' in e and not e.get('unpacked')), key=lambda item: item[2])
        offset = 0
        for name, entry, old_offset in ordered:
            entry['offset'] = str(offset)
            offset += entry['size']
        encoded, patched_raw = pack_header(header)
        candidate = output / 'app.asar'
        if candidate.resolve() == archive.resolve():
            raise ValueError('Cannot overwrite original archive')
        with candidate.open('wb') as target:
            target.write(encoded)
            for name, entry, old_offset in ordered:
                if name in patches:
                    target.write(patches[name])
                else:
                    stream.seek(base + old_offset)
                    remaining = entry['size']
                    while remaining:
                        chunk = stream.read(min(remaining, 8_388_608))
                        if not chunk:
                            raise ValueError('Truncated original archive')
                        target.write(chunk)
                        remaining -= len(chunk)
    plist['ElectronAsarIntegrity']['Resources/app.asar']['hash'] = sha(patched_raw)
    (output / 'Info.plist').write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_BINARY))
    report = {'source': str(source_app), 'version': plist['CFBundleShortVersionString'],
              'originalHeaderHash': expected, 'patchedHeaderHash': sha(patched_raw),
              'themeHash': sha(css.encode()), 'changes': changes, 'installed': False,
              'requiresResigning': True,
              'requiresFrameworkDictionaryDigestUpdate': True}
    (output / 'patch-report.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/Applications/ChatGPT.app'))
    parser.add_argument('--css', type=Path, default=Path(__file__).with_name('theme.css'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.css, args.output), indent=2))
