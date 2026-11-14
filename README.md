# ChatGPT Themes

Experimental, unofficial custom themes for the ChatGPT desktop client on macOS.

The Sumerki theme adds a dark violet palette and a subtle animated geometric background. A local prototype has been tested with ChatGPT **26.1111.21308 / build 27194**, including repeated launches and an installation into the main app. This is not a general-purpose installer release yet.

## Current state

- CSS theme with reduced-motion support.
- Isolated development launcher with automatic CSS reapplication via local CDP.
- ASAR rebuilding, per-file hashes and archive-header hash updates.
- Embedded integrity-dictionary digest update for the tested Electron/Owl framework.
- Locally signed test copy, plus experimental installation and restore scripts.

The next test build includes a **Темы** entry in the account menu, directly after Settings, opening a centered theme panel: Sumerki, Ocean, Graphite and the native appearance; geometry and motion switches; cycle duration; persisted selection and cross-window synchronization. The manager is isolated in a Shadow DOM. Its exact inline-script hash is added to CSP; unrestricted inline JavaScript is not enabled. DOM tests pass; this manager build still needs manual verification in ChatGPT.

Theme import, update handling and compatibility with other builds are **not implemented**.

## Layout

- `tools/sumerki/`: prototype source, theme and launchers.
- `tools/prepare_copy.py`: builds and locally signs an isolated test copy.
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
