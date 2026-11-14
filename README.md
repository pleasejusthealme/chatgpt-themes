# ChatGPT Themes

Experimental, unofficial custom themes for the ChatGPT desktop client on macOS.

The Sumerki theme adds a dark violet palette and a subtle animated geometric background. A local prototype has been tested with ChatGPT **26.1111.21308 / build 27194**, including repeated launches and an installation into the main app. This is not a general-purpose installer release yet.

## Graphical patcher (macOS prototype)

A native AppKit application now provides app selection, install/update, progress, rollback and an Open ChatGPT button. No Terminal is needed to use the built `.app`. It requires an existing Python 3 installation (Python is not bundled yet).

To build it from source:

```sh
python3 tools/build_gui.py
```

Open `dist/ChatGPT Themes Patcher.app`, select ChatGPT, fully quit ChatGPT, and click **Установить / Обновить**. The app prepares and verifies a locally signed replacement before swapping it into place. If the exact current manager is already present, it skips replacement and re-signing. **Откатить** restores the version saved before the first operation by this GUI; if that version was already patched, rollback restores that patched version, not a vendor-original download.

Backups are stored under `~/Library/Application Support/ChatGPT Themes`, separately for each selected app path. Account profiles and Keychain entries are not copied or edited. The patcher's local re-signing can still cause macOS to request Keychain permission when ChatGPT next starts. This prototype does not suppress that prompt for real accounts.

## Current state

- CSS theme with reduced-motion support.
- Isolated development launcher with automatic CSS reapplication via local CDP.
- ASAR rebuilding, per-file hashes and archive-header hash updates.
- Embedded integrity-dictionary digest update for the tested Electron/Owl framework.
- Locally signed test copy, plus experimental installation and restore scripts.

The next test build includes a **Темы** entry in the account menu, directly after Settings, opening a centered theme panel: Sumerki, Ocean, Graphite and the native appearance; geometry and motion switches; cycle duration; persisted selection and cross-window synchronization. The manager is isolated in a Shadow DOM. Its exact inline-script hash is added to CSP; unrestricted inline JavaScript is not enabled. DOM tests pass; this manager build still needs manual verification in ChatGPT.

Theme import, automatic handling of vendor updates and compatibility with other builds are **not implemented**. GUI reapplication of our known patches is supported.

## Layout

- `tools/sumerki/`: prototype source, theme and launchers.
- `tools/prepare_copy.py`: builds and locally signs an isolated test copy.
- `app/Patcher.m`: native GUI; `tools/gui_backend.py`: backup/build/swap operations.
- `manager/manager.js`: in-app theme controls, bundled into the patched documents.
- `experiments/extension-probe/`: unsuccessful extension approach, retained for research; do not install it.
- `docs/architecture.md`: findings and limitations.
- `work/`: local app copies, backups, profiles and logs; ignored by Git.

## Build a test copy

Requires macOS/APFS, Python 3.10+ and Apple's `codesign` tool. Use an **unmodified** source app matching the tested version. If your installed app is already patched, use its original backup as the source.

```sh
python3 tools/prepare_copy.py --source /Applications/ChatGPT.app
zsh tools/sumerki/Start-patched-test.command
```

The launcher uses an isolated profile and does not copy your account data. Quit the test with Cmd+Q or Ctrl+C. The copy has a local ad-hoc signature; it no longer carries the original publisher signature. macOS permissions, keychain-dependent features and updates need further testing.

The existing `Install-main.command` and `Restore-main.command` are experimental local scripts, not recommended release installers. Review them before use. They replace the installed bundle, require ChatGPT to be fully quit, and keep an original backup. App updates may remove the patch.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Manager DOM tests use Node.js 22 and `linkedom@0.18.12`; see the workflow for the bundle-generation and test commands.

Only original project code is distributed. No ChatGPT binaries, extracted application source, user profiles, logs, cookies or credentials belong in this repository. Not affiliated with OpenAI.
