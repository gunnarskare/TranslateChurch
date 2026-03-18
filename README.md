# TranslateChurch

TranslateChurch is a production-minded MVP for live church translation. It captures Norwegian speech from a USB-connected mixer, uses simple voice activity detection to skip silence and short noises, transcribes speech with OpenAI, translates it to English and Ukrainian, and pushes the results to mobile browsers over WebSockets.

## Architecture summary

### Backend flow
1. `backend/services/audio_input.py` reads live mono audio from the selected USB input device with `sounddevice`.
2. `backend/services/vad.py` uses a simple energy threshold and timing rules to detect meaningful speech segments.
3. `backend/services/transcribe.py` sends valid WAV segments to OpenAI transcription.
4. `backend/services/translate.py` translates the Norwegian transcript into English and Ukrainian.
5. `backend/services/pipeline.py` coordinates the flow and publishes a unified live message.
6. `backend/services/broadcaster.py` pushes the latest text update to WebSocket clients grouped by language.

### Frontend flow
1. `frontend/index.html` serves a simple mobile-friendly page.
2. `frontend/app.js` connects to `/ws/{language}`, renders live text, and can trigger test-mode messages.
3. `frontend/styles.css` provides a clean layout for phone users in the church.

## Project structure

```text
backend/
  config.py
  main.py
  models/
    schemas.py
  routers/
    api.py
    websocket.py
  services/
    audio_input.py
    broadcaster.py
    pipeline.py
    transcribe.py
    translate.py
    vad.py
frontend/
  index.html
  app.js
  styles.css
requirements.txt
.env.example
README.md
```

## Features included in this MVP
- Live USB audio capture from the local machine.
- Simple, configurable VAD to avoid sending silence, bumps, and very short sounds.
- Speech segmentation that ends after about 1 second of silence.
- OpenAI-based Norwegian transcription.
- OpenAI-based translation to English and Ukrainian.
- WebSocket broadcasting to browsers.
- Mobile-friendly single-page frontend.
- Test mode for manual transcript injection without a mixer.
- Clear logging for device selection, speech start/end, ignored segments, transcripts, and outgoing translations.

## Requirements
- Python 3.11 or newer recommended.
- A local computer with access to the church USB mixer.
- An OpenAI API key.
- The correct audio driver for your operating system.

## Exact local run steps

### 1. Clone the project
```bash
git clone <your-repo-url>
cd TranslateChurch
```

### 2. Create and activate a virtual environment
#### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```

Then edit `.env` and set at least:
- `OPENAI_API_KEY`
- optionally `AUDIO_DEVICE_INDEX` or `AUDIO_DEVICE_NAME`
- optionally VAD tuning values such as `VAD_ENERGY_THRESHOLD`

### 5. Find the correct USB audio input device
Start a Python shell and run:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Find the mixer input device in the list. Then put either its index into `AUDIO_DEVICE_INDEX` or part of its name into `AUDIO_DEVICE_NAME`.

Tip: If the wrong device is selected, the backend logs the chosen input device on startup.

### 6. Start the backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Open the frontend
On the same PC, open:

```text
http://localhost:8000/
```

On phones connected to the same network, open:

```text
http://YOUR-PC-IP:8000/
```

## Test mode without live audio
If you want to test the browser flow before connecting the mixer:

1. Set `TEST_MODE=true` in `.env`.
2. Start the backend.
3. Open the frontend.
4. Enter a Norwegian sentence in the test box and send it.

This sends the manual transcript to `/api/test/segment`, runs translation, and broadcasts the result to connected browsers.

## API endpoints
- `GET /api/health` – application and audio status.
- `GET /api/audio/devices` – list available input devices.
- `POST /api/test/segment` – test-mode transcript injection.
- `WS /ws/en` – English stream.
- `WS /ws/uk` – Ukrainian stream.
- `WS /ws/no` – Norwegian source transcript stream.

## Tuning for a church environment
The first VAD implementation is intentionally simple and easy to understand.

### Main config values
- `VAD_ENERGY_THRESHOLD`: raises or lowers sensitivity to detected speech.
- `VAD_SILENCE_TIMEOUT_SECONDS`: how long silence must last before a speech segment ends.
- `VAD_MINIMUM_SPEECH_SECONDS`: the minimum detected speech duration before a segment is sent.
- `MAXIMUM_SEGMENT_SECONDS`: safety cap for very long segments.
- `MINIMUM_TRANSCRIPT_CHARACTERS`: ignores empty or tiny transcription results.

### Practical tuning advice
- If coughing or bumps are still being sent, increase `VAD_ENERGY_THRESHOLD` and/or `VAD_MINIMUM_SPEECH_SECONDS`.
- If soft speakers are being missed, reduce `VAD_ENERGY_THRESHOLD` slightly.
- If segments feel cut off too early, increase `VAD_SILENCE_TIMEOUT_SECONDS`.
- If latency is too high, lower `VAD_SILENCE_TIMEOUT_SECONDS` a bit, but be careful not to split natural pauses.

## Notes on service boundaries
- `transcribe.py` owns speech-to-text API calls only.
- `translate.py` owns translation API calls only.
- `pipeline.py` orchestrates the workflow and keeps OpenAI concerns out of routers and WebSockets.
- `broadcaster.py` is only responsible for connected client fan-out.

This separation makes it easier to swap models, add retries, or introduce background queues later.

## Simulated audio file mode later
This MVP includes a text-based test mode now because it is the lightest reliable option for local setup. A next step could add a file-based simulator that reads WAV audio in chunks and feeds the VAD service exactly like the live microphone stream.

## TODO markers already prepared
- Add OpenAI text-to-speech in `backend/services/translate.py` or a future dedicated `tts.py` service.
- Upgrade the VAD logic with WebRTC VAD for noisier rooms.
- Add admin controls for start/stop and status management.

## Short next improvements
1. **OpenAI text-to-speech**
   - Add a dedicated TTS service that turns translated text into low-latency audio streams per language.
   - Cache recent segments so late joiners can hear the current section.
2. **QR code join page**
   - Add a route that shows a QR code for `http://YOUR-PC-IP:8000/` for faster mobile onboarding.
3. **Admin start/stop controls**
   - Add a small admin page to start or pause the live translation pipeline without restarting the app.
4. **Better VAD**
   - Replace the current energy threshold with WebRTC VAD plus noise-floor calibration.
5. **Deployment to a remote server later**
   - Move static frontend hosting behind a reverse proxy and expose secure WebSockets over HTTPS/WSS.
   - Keep audio capture on the local machine or add a small local capture agent if the API server moves to the cloud.
