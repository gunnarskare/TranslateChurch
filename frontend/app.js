const state = {
  currentLanguage: 'en',
  socket: null,
  reconnectTimer: null,
  latestPayload: null,
  testMode: false,
};

const languageNames = {
  en: 'English',
  uk: 'Українська',
  no: 'Norsk',
};

const elements = {
  tabs: document.getElementById('language-tabs'),
  liveText: document.getElementById('live-text'),
  statusDot: document.getElementById('status-dot'),
  statusText: document.getElementById('status-text'),
  currentLanguageLabel: document.getElementById('current-language-label'),
  timestampLabel: document.getElementById('timestamp-label'),
  textNo: document.getElementById('text-no'),
  textEn: document.getElementById('text-en'),
  textUk: document.getElementById('text-uk'),
  testCard: document.getElementById('test-card'),
  testTranscript: document.getElementById('test-transcript'),
  sendTestButton: document.getElementById('send-test-button'),
  testResult: document.getElementById('test-result'),
};

function setStatus(kind, label) {
  elements.statusDot.className = `status-dot ${kind}`.trim();
  elements.statusText.textContent = label;
}

function setLiveText(text) {
  elements.liveText.textContent = text;
  elements.liveText.classList.toggle('empty', !text);
}

function updateDisplayFromPayload(payload) {
  state.latestPayload = payload;
  const selectedText = payload.translations[state.currentLanguage] || payload.text || '';
  setLiveText(selectedText);
  elements.currentLanguageLabel.textContent = languageNames[state.currentLanguage] || state.currentLanguage;
  elements.timestampLabel.textContent = new Date(payload.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  elements.textNo.textContent = payload.translations.no || '—';
  elements.textEn.textContent = payload.translations.en || '—';
  elements.textUk.textContent = payload.translations.uk || '—';
}

function connectWebSocket() {
  if (state.socket) {
    state.socket.onclose = null;
    state.socket.close();
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${protocol}://${window.location.host}/ws/${state.currentLanguage}`;

  setStatus('', `Connecting to ${languageNames[state.currentLanguage]}…`);
  const socket = new WebSocket(url);
  state.socket = socket;

  socket.onopen = () => {
    setStatus('connected', `Connected: ${languageNames[state.currentLanguage]}`);
  };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      updateDisplayFromPayload(payload);
    } catch (error) {
      console.error('Failed to parse websocket payload', error);
      setStatus('error', 'Received invalid update');
    }
  };

  socket.onerror = () => {
    setStatus('error', 'WebSocket error');
  };

  socket.onclose = () => {
    setStatus('error', 'Disconnected. Retrying…');
    window.clearTimeout(state.reconnectTimer);
    state.reconnectTimer = window.setTimeout(connectWebSocket, 3000);
  };
}

function selectLanguage(language) {
  state.currentLanguage = language;
  elements.tabs.querySelectorAll('.language-tab').forEach((button) => {
    button.classList.toggle('active', button.dataset.language === language);
  });
  elements.currentLanguageLabel.textContent = languageNames[language] || language;

  if (state.latestPayload) {
    updateDisplayFromPayload(state.latestPayload);
  } else {
    setLiveText('Waiting for the next translated segment…');
    elements.liveText.classList.add('empty');
  }

  connectWebSocket();
}

async function loadHealth() {
  try {
    const response = await fetch('/api/health');
    const payload = await response.json();
    state.testMode = Boolean(payload.audio?.test_mode);
    elements.testCard.hidden = !state.testMode;
  } catch (error) {
    console.error('Failed to load health state', error);
  }
}

async function sendTestTranscript() {
  const transcript = elements.testTranscript.value.trim();
  if (!transcript) {
    elements.testResult.textContent = 'Enter a Norwegian sentence first.';
    return;
  }

  elements.sendTestButton.disabled = true;
  elements.testResult.textContent = 'Sending…';

  try {
    const response = await fetch('/api/test/segment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || 'Request failed');
    }

    elements.testTranscript.value = '';
    elements.testResult.textContent = `Published segment ${payload.segment_id}`;
  } catch (error) {
    elements.testResult.textContent = error.message;
  } finally {
    elements.sendTestButton.disabled = false;
  }
}

elements.tabs.addEventListener('click', (event) => {
  const button = event.target.closest('.language-tab');
  if (!button) return;
  selectLanguage(button.dataset.language);
});

elements.sendTestButton.addEventListener('click', sendTestTranscript);

window.addEventListener('beforeunload', () => {
  if (state.socket) {
    state.socket.onclose = null;
    state.socket.close();
  }
});

loadHealth();
selectLanguage(state.currentLanguage);
