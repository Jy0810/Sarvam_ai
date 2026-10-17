# Upgrade from the MVP to true real-time streaming

The current MVP records one short utterance and uploads it after the user presses Stop. It is deliberately simpler to install and debug. It is not full-duplex streaming.

## Target architecture

1. Browser captures microphone PCM frames at the sample rate/format required by Sarvam's realtime STT endpoint.
2. Browser opens an authenticated application WebSocket to FastAPI. Do **not** send the Sarvam API key to the browser.
3. Backend opens/maintains Sarvam `speech-to-text-realtime` WebSocket and forwards audio frames. Forward partial transcripts to the browser as they arrive.
4. On end-of-turn, route the final transcript. For simple questions, skip search; for freshness-sensitive questions, use OpenAI web search.
5. As OpenAI emits coherent text segments (where supported by the selected API/model), send segments to Sarvam Bulbul WebSocket TTS. Follow Sarvam's required config/text/flush message sequence.
6. Forward audio chunks to the browser and play them incrementally. Include `turn_id` on all app-level events.
7. On user barge-in, cancel the current generation task, stop browser playback, flush/discard stale audio, and begin a new turn.

## Essential engineering details

- Read Sarvam's current realtime STT protocol before implementing: <https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-streaming>
- Read the current TTS WebSocket protocol and use the SDK's async API if available: <https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/streaming-api/web-socket>
- The browser Web Audio API commonly captures float samples; convert to the exact signed PCM format expected by the endpoint. Never label float bytes as PCM16.
- Keep audio transport, STT session, assistant turn, OpenAI generation, and TTS stream lifecycles separate.
- Apply bounded queues/backpressure so slow TTS or clients do not grow memory indefinitely.
- Do not speak a claim before enough evidence is available if the user requested researched information. A short “I’m checking current sources” acknowledgement may be spoken separately, clearly distinguished from the final answer.
- Add connection timeouts, cancellation, reconnect handling, heartbeat, per-session limits, and tests with mocked WebSocket events.
- Measure p50/p95 time to partial transcript, final transcript, first answer token, first audio byte, and complete response.

## Why not fake streaming in this MVP?

Sending a finished audio file as base64 after the full request is complete is not true streaming. The MVP uses HTTP-streaming TTS at the provider but buffers the chunks for a simpler response contract. The upgrade should stream real chunks end-to-end instead of merely changing the UI labels.
