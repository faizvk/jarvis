# Changelog

All notable changes to Jarvis are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.2.0]

### Added
- **"Hey Jarvis" wake word** — offline, hands-free activation via openWakeWord
  (`jarvis/wakeword.py`), now the default. A short chime acknowledges detection.
- **Calculator tool** — safe AST-based arithmetic so the model never shells out
  for maths.
- **Clipboard tools** — `read_clipboard` / `write_clipboard`.
- **CLI flags** — `--wake`, `--ptt`, `--once "QUERY"`; `--doctor` now checks the
  wake word too.
- **File logging** — rotating log at `state/jarvis.log` (`jarvis/logconf.py`).
- Configurable STT beam size and `[wake]` config section.

### Changed
- Default `wake_mode` is now `wakeword` (was `enter`).
- Stronger system prompt: explicit tool routing (calculate for maths, web_search
  for facts, run_command only for real system actions).
- Hardened web search (rate-limit handling, URL dedupe, snippet trimming).
- Destructive shell commands (`del`, `format`, `Remove-Item`, `shutdown`, …) now
  always require confirmation, even when `confirm_commands` is off.

## [0.1.0]

### Added
- Initial release: voice loop, faster-whisper STT, pyttsx3 TTS, Ollama tool-calling
  client, and tools for web search, PC control, reminders/timers, and the clock.
