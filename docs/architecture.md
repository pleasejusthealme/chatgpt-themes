# Implementation notes

## Working approaches

For development, the normal release client accepts `--remote-debugging-port` with a separate user-data directory. CDP can insert an idempotent style element. This needs a special launch; it does not satisfy ordinary Dock startup by itself.

For ordinary startup, CSS is embedded in `webview/index.html` and `webview/detached-window.html` in a local copy of app.asar. Rebuilding requires all three integrity layers to agree:

1. Modified-file SHA256 and block hashes inside ASAR.
2. ASAR JSON-header SHA256 in Info.plist / ElectronAsarIntegrity.
3. SHA256 of the sorted integrity dictionary, embedded in the framework's `__asar_integrity` slot.

The third layer was the cause of a failed test build. Its slot uses sentinel `AGbevlPCksUGKNL8TSn7wGmJEuJsXb2A`, used/version bytes and a 32-byte digest. The implementation verifies the original digest and replaces exactly one matching slot. The validation fuse stays enabled. Local code signing is then required.

The dictionary digest concatenates UTF-8 path, algorithm and hash for each sorted key. See upstream: https://github.com/electron/electron/blob/main/shell/common/asar/integrity_digest.mm

## Approaches that did not work

- Persisted Chromium `devtools.remote_debugging.user-enabled` starts an approval-mode server, but the tested Owl client rejected browser WebSocket connections with HTTP 403. HTTP 404 for /json/list is expected in that mode.
- A loaded MV3 extension could enumerate the app shell, but chrome.debugger.attach was denied for app:// even with all_urls. The extension was removed from the test profile.
- ChromeFeatureState is feature/field-trial state for app shims, not a verified general launch-argument configuration.

## Scope and limits

Only macOS arm64 build 26.1111.21308 / 27194 was manually tested. There is no public theme API. Static CSS patching currently requires rebuilding and signing for each theme change. App updates, publisher identity, keychain access and system permissions require care. An in-app theme manager is the next milestone.

## Account-menu integration

The manager has no floating launcher. The tested build's profile-menu module is patched to add one native H.tJ item after Settings. Its selection closes the account menu and dispatches chatgpt-themes:open; the manager opens a centered dialog. Exact module path and render-list checks make unknown layouts fail closed. The module's file/block hashes, archive header and embedded dictionary digest are updated together.

A locally re-signed copy can trigger a macOS Keychain request for Codex Storage Key, even with an isolated Chromium profile. This is separate from theme settings. Theme tests do not require granting that request. Original keychain credentials are never read or published by this project.

The menu-test launcher now explicitly uses --ui-only: a dedicated empty profile plus Chromium's --use-mock-keychain. This substitutes a test encryption key for UI development; it does not grant access to the real Keychain. Do not sign in or store personal data in this profile. Normal launches and the main app are not configured with this flag. Reference: https://github.com/GoogleChrome/chrome-launcher/blob/main/src/flags.ts

## Native patcher

The AppKit GUI runs the bundled standard-library Python backend and consumes JSON-lines progress. Install uses a clone staged next to the selected app, verifies signatures and ASAR header metadata, updates all integrity layers and locally signs the stage. The original is parked before the final rename; a failed second rename restores it. Recovery metadata and a baseline backup are persisted before any replacement. Each operation retains a snapshot; no account profile or Keychain entry is copied. A file lock prevents concurrent patcher operations, and lsof checks that the target app is closed. Known previous HTML/menu injections are replaced rather than accumulated; unknown layouts fail closed. A local Python interpreter is a current packaging dependency.
