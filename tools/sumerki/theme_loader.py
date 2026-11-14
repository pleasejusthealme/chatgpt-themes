"""Local CSS-only experiment. Explicit target id required; no automatic injection."""
import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


class CDP:
    def __init__(self, url, port=19381):
        u = urlsplit(url)
        if u.hostname != '127.0.0.1' or u.port != port or port not in (19381, 19382):
            raise ValueError('Only the local test endpoint is allowed')
        self.sock = socket.create_connection((u.hostname, u.port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {u.path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
                           f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        response = b''
        while not response.endswith(b'\r\n\r\n'):
            response += self.exact(1)
            if len(response) > 16384:
                raise RuntimeError('Invalid handshake')
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        if b' 101 ' not in response.split(b'\r\n')[0] or accept not in response:
            self.sock.close()
            raise RuntimeError('WebSocket handshake rejected: ' + response.split(b'\r\n')[0].decode(errors='replace'))

    def exact(self, n):
        result = b''
        while len(result) < n:
            chunk = self.sock.recv(n - len(result))
            if not chunk:
                raise EOFError('Connection closed')
            result += chunk
        return result

    def send(self, data, opcode=1):
        mask = os.urandom(4)
        n = len(data)
        header = bytes([128 | opcode])
        header += bytes([128 | n]) if n < 126 else (bytes([254]) + struct.pack('!H', n) if n < 65536 else bytes([255]) + struct.pack('!Q', n))
        self.sock.sendall(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(data)))

    def evaluate(self, expression):
        result = self.command('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
        if 'exceptionDetails' in result:
            raise RuntimeError(str(result))
        return result['result'].get('value')

    def command(self, method, params=None):
        self.send(json.dumps({'id': 1, 'method': method, 'params': params or {}}).encode())
        fragments = b''
        while True:
            a, b = self.exact(2)
            n = b & 127
            if n == 126:
                n = struct.unpack('!H', self.exact(2))[0]
            elif n == 127:
                n = struct.unpack('!Q', self.exact(8))[0]
            if n > 8_000_000:
                raise RuntimeError('Oversized frame')
            mask = self.exact(4) if b & 128 else None
            data = self.exact(n)
            if mask:
                data = bytes(v ^ mask[i % 4] for i, v in enumerate(data))
            opcode = a & 15
            if opcode == 8:
                raise EOFError('WebSocket closed')
            if opcode == 9:
                self.send(data, 10)
                continue
            if opcode not in (0, 1):
                continue
            fragments += data
            if not a & 128:
                continue
            result = json.loads(fragments)
            fragments = b''
            if result.get('id') == 1:
                if 'error' in result:
                    raise RuntimeError(str(result))
                return result['result']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['list', 'apply', 'remove'])
    parser.add_argument('--target')
    parser.add_argument('--port', type=int, choices=[19381, 19382], default=19381)
    args = parser.parse_args()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{args.port}/json/list', timeout=4) as response:
        targets = json.load(response)
    if args.action == 'list':
        print(json.dumps([{'id': t['id'], 'type': t['type'], 'url': t.get('url', '').split('?')[0]} for t in targets], indent=2))
        return
    target = next(t for t in targets if t['id'] == args.target and t['type'] == 'page')
    css = (Path(__file__).parent / 'theme.css').read_text()
    expression = """(() => {
      const id = 'sumerki-experimental-theme';
      document.getElementById(id)?.remove();
      %s
      return {applied: !!document.getElementById(id), background: getComputedStyle(document.body).backgroundColor};
    })()""" % ("const s = document.createElement('style'); s.id = id; s.textContent = " + json.dumps(css) + "; document.head.appendChild(s);" if args.action == 'apply' else '')
    client = CDP(target['webSocketDebuggerUrl'], args.port)
    try:
        print(json.dumps(client.evaluate(expression)))
    finally:
        client.sock.close()


if __name__ == '__main__':
    main()
