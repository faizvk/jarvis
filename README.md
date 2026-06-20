# Jarvis

A local, **voice-controlled terminal assistant** for Windows, powered by a model
running on [Ollama](https://ollama.com). Push-to-talk in, spoken replies out — and
the brain runs entirely on your own machine, so conversations never leave your PC.

Jarvis can:

- **Hold a conversation** — general questions, reasoning, quick drafting.
- **Search the web** — live DuckDuckGo results, no API key required.
- **Control your PC** — open apps, open URLs, run shell commands (with a safety confirm).
- **Manage reminders & timers** — spoken alerts that survive a restart.

## How it works

```
mic ──▶ record (silence-detected) ──▶ faster-whisper (STT)
                                            │
                                            ▼
                                   Ollama model + tools  ◀── web / system / reminders
                                            │
                                            ▼
                                     pyttsx3 (TTS) ──▶ speaker
```

Everything except the optional web search runs offline.

## Requirements

- Windows 10/11, **Python 3.11+** (3.12 tested)
- A working microphone and speakers
- [Ollama](https://ollama.com) with a **tool-calling capable** model (e.g. `llama3.1:8b`)

## Setup

```powershell
# 1. Python dependencies (creates .venv)
.\setup.ps1

# 2. Install Ollama and pull a model
winget install Ollama.Ollama
ollama pull llama3.1:8b

# 3. Verify everything is wired up
.\run.ps1 --doctor

# 4. Talk to Jarvis
.\run.ps1
```

## Usage

| Command | What it does |
|---|---|
| `.\run.ps1` | Voice mode — press **Enter**, speak, it auto-stops on silence |
| `.\run.ps1 --text` | Type instead of speaking (great for testing without a mic) |
| `.\run.ps1 --doctor` | Check Ollama, the model, mic, TTS and STT |
| `.\run.ps1 --say "hello"` | Speak one phrase (TTS test) and exit |
| `.\run.ps1 --model qwen2.5:7b` | Use a different Ollama model for this run |

Say **"goodbye"** (or press **Ctrl+C**) to quit.

### Example things to say

- "What's the weather in Bangalore right now?" *(web search)*
- "Open Notepad." / "Open chrome." *(PC control)*
- "Set a timer for five minutes." / "Remind me to call mom in two hours."
- "What reminders do I have?"
- "What time is it?"

## Configuration

Copy `config.example.toml` to `config.toml` and edit it (it's git-ignored). You can
tune the model, the Whisper size, microphone sensitivity, the TTS voice/rate, and
whether shell commands need confirmation. See the comments in the file for details.

Two environment variables also override config: `JARVIS_MODEL` and `OLLAMA_HOST`.

## Safety

`run_command` is the only tool that executes an arbitrary shell command, and by
default (`confirm_commands = true`) Jarvis prints the exact command and waits for
you to type `y` before running it. Leave this on unless you fully trust the model.

`open_application` only *launches* a named app, file, or URL through the Windows
shell verb — it never builds a shell command line and rejects names containing
shell metacharacters, so it can't be used to slip a command past the confirmation
prompt. It is intentionally not gated (opening Notepad shouldn't need a y/n).

## Troubleshooting

- **"Can't reach Ollama"** — start the Ollama app, or run `ollama serve`, then retry.
- **"model isn't pulled"** — `ollama pull llama3.1:8b` (or whatever model you set).
- **No audio / mic not found** — run `.\run.ps1 --doctor` to list input devices; pick a
  different default mic in Windows Sound settings.
- **It doesn't hear me** — raise/lower `silence_threshold` in `config.toml`.
- **First run is slow** — faster-whisper downloads the speech model once, then caches it.

## License

MIT © faizvk. See [LICENSE](LICENSE).
