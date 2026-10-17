# Multilingual Voice Research Assistant

A small, runnable MVP for a voice assistant using **Sarvam Saaras STT**, **OpenAI with optional web search**, and **Sarvam Bulbul TTS**. The backend keeps API keys private and serves a simple browser UI.

## Important scope note

This first version is a **short-utterance push-to-talk MVP**, not yet a full-duplex, partial-transcript WebSocket agent. It uses Sarvam's synchronous STT endpoint (maximum 30 seconds per request), OpenAI Responses API (with its web search tool when research is enabled), and Sarvam HTTP-streaming TTS whose audio chunks are buffered before the response is returned as JSON. This keeps the first install relatively straightforward. The upgrade path for true live STT/audio streaming is in `docs/REALTIME_UPGRADE.md`.

Provider availability, model access, language/voice support, quotas, and API behavior depend on your accounts. Run the smoke checks below before considering a deployment production-ready.

## Requirements

- Python 3.11 recommended (3.10+ should work if provider SDKs support it)
- A Sarvam API key with STT and TTS access
- An OpenAI API key with access to the Responses API and, when using research mode, the web search tool
- A modern browser with microphone support (localhost or HTTPS)

## 1. Configure

```bash
git clone <your-repository-url>
cd voice-research-assistant
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and create your environment file:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead of `cp` if needed. Edit `.env` and set `SARVAM_API_KEY` and `OPENAI_API_KEY`. Never commit `.env`.

### Model configuration

Default values in `.env.example` are configurable:

- `SARVAM_STT_MODEL=saaras:v4`
- `SARVAM_TTS_MODEL=bulbul:v4-flash`
- `OPENAI_MODEL=gpt-4.1-mini`

If a model is unavailable to your account, change it to a model currently enabled for your account. Model names and availability can change; check provider dashboards/docs.

## 2. Run locally

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000>. API health: <http://127.0.0.1:8000/api/health>. Interactive API docs: <http://127.0.0.1:8000/docs>.

## 3. Use it

1. Choose an answer language or leave it on Auto.
2. Press **Start recording**, ask a short question, and press **Stop & ask**; or type a question.
3. The backend transcribes voice with Sarvam, decides whether web research is needed (or follows your explicit setting), asks OpenAI to answer, extracts web citations when available, and synthesizes audio with Sarvam.
4. Read the transcript/answer, play the audio, and open any returned sources.

The synchronous Sarvam STT API is limited to 30 seconds. Keep questions short in this version. The audio upload limit is controlled by `MAX_UPLOAD_MB`.

## API endpoints

### `GET /api/health`
Reports configuration status and configured model IDs. It does not make paid provider calls.

### `POST /api/text`

```json
{
  "query": "What are the latest developments in speech recognition?",
  "response_language": "English",
  "research": true
}
```

`response_language` is optional. `research` can be `true`, `false`, or `null` (automatic heuristic).

### `POST /api/voice`
Multipart form fields:

- `audio`: recorded audio file (supported format depends on Sarvam; browser WebM/Opus is accepted by the documented REST API formats)
- `response_language`: optional natural-language output preference (e.g. `Telugu`, `English`)
- `research`: `auto`, `true`, or `false`

Both endpoints return transcript, answer, audio as base64, audio MIME type, sources, research flag, and stage timing measurements.

## Tests and checks

```bash
python -m compileall app tests
python -m pytest -q
curl http://127.0.0.1:8000/api/health
```

Tests do not call external APIs and do not require keys. To test live integrations, set real keys, start the server, then use the UI or `/docs`.

## Troubleshooting

- **`needs_configuration` / HTTP 503:** set both API keys in `.env`; restart the server.
- **403:** check the key and whether your account has access to the selected model.
- **429:** quota/rate limit; reduce requests or review provider plan limits.
- **OpenAI model or permission error:** set `OPENAI_MODEL` to a currently available model in your OpenAI project, and verify that your account can use the Responses API and web search when research is enabled.
- **No source links:** the model may not have returned grounding chunks for that response; do not fabricate citations.
- **Microphone permission error:** use `localhost` or HTTPS, grant microphone access, and check browser permissions.
- **STT rejects recording:** keep the clip under 30 seconds; try a current Chrome/Edge browser and check the recorded MIME type.
- **TTS voice/language error:** choose a voice compatible with the chosen language and check the current Sarvam voice catalog. The default speaker is only a starting point.
- **Slow first response:** this MVP buffers the answer audio. Use the realtime upgrade plan before claiming full streaming latency.

## Security notes

- Never place provider API keys in frontend code.
- Do not commit `.env`, audio recordings, or user transcripts.
- Add authentication, request rate limits, retention policy, and TLS before public deployment.
- Treat retrieved web content as untrusted data. Do not let webpage text override system instructions.
- This starter is not production-hardened; review provider terms, privacy requirements, and error handling before public use.

## Official references

- Sarvam STT REST: <https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/rest-api>
- Sarvam realtime STT: <https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-streaming>
- Sarvam TTS streaming: <https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/streaming-api/http-stream>
- OpenAI Responses API: <https://developers.openai.com/api/docs/guides/migrate-to-responses>
- OpenAI web search: <https://developers.openai.com/api/docs/guides/tools-web-search>

- Versal Link - https://sarvam-ai-eight.vercel.app/
