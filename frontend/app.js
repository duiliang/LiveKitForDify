/* global LiveKit */

const dom = {
  connectBtn: document.getElementById('connect-btn'),
  disconnectBtn: document.getElementById('disconnect-btn'),
  connectionState: document.getElementById('connection-state'),
  assistantState: document.getElementById('assistant-state'),
  ambientLevel: document.getElementById('ambient-level'),
  conversationLog: document.getElementById('conversation-log'),
  messageTemplate: document.getElementById('message-template'),
  manualInput: document.getElementById('manual-input'),
  manualSend: document.getElementById('manual-send'),
  room: document.getElementById('room'),
  identity: document.getElementById('identity'),
  audio: document.getElementById('assistant-audio'),
};

dom.identity.value += Math.floor(Math.random() * 10000);

const conversationHistory = [];
let thinkingTimer = null;
let currentRoom = null;
let localStream = null;
let analyserInterval = null;

function appendMessage(role, text) {
  const node = dom.messageTemplate.content.cloneNode(true);
  const root = node.querySelector('.message');
  root.classList.add(role);
  root.querySelector('.meta').textContent = `${role === 'user' ? '🧑 用户' : '🤖 助手'} · ${new Date().toLocaleTimeString()}`;
  root.querySelector('.content').textContent = text;
  dom.conversationLog.appendChild(node);
  dom.conversationLog.scrollTop = dom.conversationLog.scrollHeight;
}

function setAssistantState(stateText) {
  dom.assistantState.textContent = stateText;
}

function setConnectionState(stateText) {
  dom.connectionState.textContent = stateText;
}

function setAmbientLevel(value) {
  dom.ambientLevel.textContent = value;
}

function resetThinkingTimer() {
  if (thinkingTimer) {
    clearTimeout(thinkingTimer);
    thinkingTimer = null;
  }
}

function startThinkingTimer() {
  resetThinkingTimer();
  thinkingTimer = setTimeout(() => {
    setAssistantState('助手正在深入思考…');
  }, 3000);
}

async function updateAmbientMonitor(stream) {
  if (!stream) return;
  if (analyserInterval) clearInterval(analyserInterval);

  const audioCtx = new AudioContext();
  const source = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);

  analyserInterval = setInterval(() => {
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (const value of data) {
      const centred = value - 128;
      sum += centred * centred;
    }
    const rms = Math.sqrt(sum / data.length);
    const db = (20 * Math.log10(rms / 128 + 1e-5)).toFixed(1);
    const label = rms > 18 ? `${db} dB（噪声较高）` : `${db} dB`;
    setAmbientLevel(label);
  }, 500);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `请求失败: ${response.status}`);
  }
  return response.json();
}

async function connectLiveKit() {
  if (currentRoom) return;
  const identity = dom.identity.value.trim();
  const roomName = dom.room.value.trim();
  if (!identity || !roomName) {
    alert('请填写房间 ID 和用户标识');
    return;
  }

  try {
    setConnectionState('获取令牌…');
    const tokenData = await fetchJson('/livekit/token', {
      method: 'POST',
      body: JSON.stringify({ identity, room: roomName }),
    });
    const health = await fetchJson('/health');

    const room = new LiveKit.Room();
    currentRoom = room;

    room.on(LiveKit.RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === LiveKit.Track.Kind.Audio) {
        dom.audio.srcObject = new MediaStream([track.mediaStreamTrack]);
        setAssistantState('收到语音回复');
        appendMessage('assistant', '🔊 语音回复正在播放');
      }
    });

    room.on(LiveKit.RoomEvent.AudioPlaybackStatusChanged, () => {
      if (room.canPlaybackAudio) {
        dom.audio.muted = false;
      }
    });

    room.on(LiveKit.RoomEvent.TrackUnsubscribed, () => {
      setAssistantState('等待下一轮对话');
    });

    room.on(LiveKit.RoomEvent.ConnectionQualityChanged, (quality) => {
      console.debug('Connection quality changed', quality);
    });

    room.on(LiveKit.RoomEvent.ParticipantDisconnected, () => {
      appendMessage('assistant', '对话结束。');
    });

    setConnectionState('连接 LiveKit…');

    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    await updateAmbientMonitor(localStream);

    const livekitUrl = health.livekit.replace(/^http/, 'ws');
    await room.connect(livekitUrl, tokenData.token);
    setConnectionState('已连接');
    dom.disconnectBtn.disabled = false;
    dom.connectBtn.disabled = true;

    const localTrack = await LiveKit.createLocalAudioTrack({
      microphoneCaptureDefaults: {
        noiseSuppression: true,
        echoCancellation: true,
        autoGainControl: true,
      },
    });
    await room.localParticipant.publishTrack(localTrack);

    room.on(LiveKit.RoomEvent.ActiveSpeakersChanged, (speakers) => {
      if (speakers.some((s) => s.identity === identity)) {
        setAssistantState('检测到你的声音，准备打断上一轮回复');
      }
    });
  } catch (error) {
    console.error(error);
    alert(error.message);
    await disconnectLiveKit();
  }
}

async function disconnectLiveKit() {
  if (currentRoom) {
    await currentRoom.disconnect();
    currentRoom = null;
  }
  if (localStream) {
    localStream.getTracks().forEach((track) => track.stop());
    localStream = null;
  }
  if (analyserInterval) {
    clearInterval(analyserInterval);
    analyserInterval = null;
  }
  dom.audio.srcObject = null;
  dom.connectBtn.disabled = false;
  dom.disconnectBtn.disabled = true;
  setConnectionState('未连接');
  setAssistantState('空闲');
}

async function sendManualText() {
  const text = dom.manualInput.value.trim();
  if (!text) return;

  appendMessage('user', text);
  conversationHistory.push({ role: 'user', content: text });
  dom.manualInput.value = '';
  setAssistantState('正在调用 Dify');
  startThinkingTimer();

  try {
    const chatResp = await fetchJson('/chat', {
      method: 'POST',
      body: JSON.stringify({ messages: conversationHistory }),
    });
    resetThinkingTimer();
    setAssistantState(`响应完成（耗时 ${chatResp.latency_ms} ms）`);
    conversationHistory.push({ role: 'assistant', content: chatResp.reply });
    appendMessage('assistant', chatResp.reply);

    const ttsResp = await fetchJson('/text-to-speech', {
      method: 'POST',
      body: JSON.stringify({ text: chatResp.reply, format: 'mp3' }),
    });
    dom.audio.src = `data:audio/mp3;base64,${ttsResp.audio_base64}`;
  } catch (error) {
    resetThinkingTimer();
    setAssistantState('出错了');
    appendMessage('assistant', `⚠️ 错误: ${error.message}`);
  }
}

async function init() {
  dom.connectBtn.addEventListener('click', connectLiveKit);
  dom.disconnectBtn.addEventListener('click', disconnectLiveKit);
  dom.manualSend.addEventListener('click', sendManualText);
  dom.manualInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      sendManualText();
    }
  });

  appendMessage('assistant', '你好！点击“连接助手”即可开始语音对话，或在下方以文本形式体验。');
}

init();
