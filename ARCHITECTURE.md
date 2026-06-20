# Architecture

Jarvis is a small, modular Python package. Each module has one job and a narrow,
documented interface, which keeps the voice pipeline easy to reason about and test.

## Module map

| Module | Responsibility |
|---|---|
| `jarvis/config.py` | Load defaults + optional `config.toml` into a `Config` dataclass |
| `jarvis/wakeword.py` | `WakeWordListener` — offline "Hey Jarvis" via openWakeWord (lazy load) |
| `jarvis/audio.py` | Capture mic audio with energy-based silence detection |
| `jarvis/chime.py` | Short acknowledgement chime played when the wake word fires |
| `jarvis/stt.py` | `Transcriber` — faster-whisper speech-to-text (lazy model load) |
| `jarvis/tts.py` | `Speaker` — pyttsx3 / SAPI5 text-to-speech on a single COM worker thread |
| `jarvis/llm.py` | `OllamaClient` — `/api/chat` with tool calling, availability checks |
| `jarvis/prompts.py` | The spoken-friendly system prompt / persona + tool guidance |
| `jarvis/logconf.py` | Rotating file logging under `state/jarvis.log` |
| `jarvis/tools/` | Tool implementations + registry (`TOOLS_SCHEMA`, `dispatch`) |
| `jarvis/agent.py` | `Jarvis` — orchestration, tool loop, wake/enter/text/once loops |
| `jarvis/__main__.py` | CLI: arg parsing, `--wake`/`--ptt`/`--once`/`--doctor`/`--say` |

Tools live in `jarvis/tools/`: `clock`, `web`, `system` (open app / run command /
system info), `calculator` (safe AST arithmetic), `clipboard`, and `reminders`
(with the persistent `Scheduler`).

## Interaction loops

`run_voice_loop` dispatches on `config.wake_mode`:

- **wakeword** (default): `_wake_loop` waits on `WakeWordListener.wait_for_wake()`,
  plays a chime, then captures and answers one utterance, then cools down and resumes.
- **enter**: `_enter_loop` waits for the Enter key before each utterance.

Both share `_capture_one` (record → transcribe) and `_handle_utterance` (exit-word
check → respond). `run_text_loop` is the keyboard-only variant; `run_once` answers a
single query for `--once`. The wake listener and recorder open the mic sequentially,
never at the same time, and TTS is blocking so Jarvis never records its own voice.

## The turn loop

`Jarvis.handle_text` implements a bounded tool-calling loop:

1. Append the user message and send the conversation + `TOOLS_SCHEMA` to Ollama.
2. If the reply has no `tool_calls`, return its text — Jarvis speaks it.
3. Otherwise run each tool via `dispatch(name, args, ctx)`, append the results as
   `role: "tool"` messages, and loop (up to `MAX_TOOL_ITERATIONS`).
4. If the loop is exhausted, do one final tool-free call to force a spoken answer.

## The tool contract

Every module in `jarvis/tools/` exposes:

```python
SCHEMAS  = [ { "type": "function", "function": {...} }, ... ]
HANDLERS = { "tool_name": lambda arguments, ctx: "string result", ... }
```

`tools/__init__.py` aggregates these into `TOOLS_SCHEMA` and a `dispatch` function.
Handlers receive a `ToolContext` carrying `config`, `speaker`, `scheduler`, a
`confirm(prompt) -> bool` callback (used to gate `run_command`), and a `notify`
callback (used by the scheduler to announce fired reminders). Handlers return a
plain string and never raise — `dispatch` converts exceptions into text the model
can read and recover from.

## Reminders

`tools/reminders.Scheduler` runs a daemon thread that wakes once a second, fires
items whose time has come via the `notify` callback, and persists pending items to
`state/reminders.json` so they survive a restart.

## Design choices

- **Local-first**: STT (faster-whisper) and TTS (SAPI5) run offline; only web search
  touches the network. The LLM runs on Ollama on `localhost`.
- **Lazy loading**: heavy imports (faster-whisper, pyttsx3) happen on first use so
  `--doctor` and `--say` stay fast and degrade gracefully.
- **Fail soft**: tool errors and an unreachable model become spoken messages rather
  than crashes.
