# Changelog

All notable changes to Jarvis are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.2.1]

### Changed
- Default model is now **llama3.2:3b** — it fits a 4 GB GPU, whereas the 8B model
  spilled to CPU and made replies take ~100s on a GTX 1650. Added a model-choice guide.
- Ollama requests set **keep_alive** (model stays warm in VRAM between turns) and a
  fixed **num_ctx**; both configurable under `[llm]`.

### Added
- LLM + speech-model **pre-warming** on startup so the first turn isn't a cold load;
  `setup.ps1` now pre-downloads the Whisper model.
- Smarter `--doctor`: opens the mic at the configured rate, warns when the model is
  too big for the GPU, and validates `wake_mode`.
- Configurable STT beam size.

### Fixed
- No more silent replies on an empty model turn; the model's tool preamble is spoken.
- Conversation history is bounded (no silent context overflow) and rolled back when a
  turn fails partway.
- Wake mode recovers from transient mic glitches and falls back to press-Enter if the
  wake model can't load.
- Whisper near-silence hallucinations ("Thank you.", "you") are filtered out.
- TTS self-heals a wedged engine instead of stalling; audio recording is no longer
  held open by background noise; reminders are saved atomically; destructive shell
  commands are always confirmed.

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
