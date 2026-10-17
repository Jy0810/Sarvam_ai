const $ = (id) => document.getElementById(id);
const recordButton = $('record');
const stopButton = $('stop');
let recorder = null;
let chunks = [];
let stream = null;
let recordingTimer = null;

function setStatus(message, kind = '') {
  const status = $('status');
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}
function setBusy(busy, message = 'Working…') {
  $('sendText').disabled = busy;
  recordButton.disabled = busy;
  stopButton.disabled = busy || !recorder || recorder.state !== 'recording';
  if (busy) setStatus(message, 'busy');
}
function languageValue() { return $('language').value || ''; }
function researchValue() { return $('research').value; }

async function requestJSON(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.message || `Request failed (${response.status})`);
  return payload;
}
function renderResult(data) {
  $('result').hidden = false;
  $('transcript').textContent = data.transcript || '';
  $('answer').textContent = data.answer || '';
  $('timing').textContent = `${data.timings_ms?.total ?? '?'} ms total`;
  $('timings').textContent = JSON.stringify(data.timings_ms || {}, null, 2);
  const list = $('sources'); list.replaceChildren();
  for (const source of data.sources || []) {
    const li = document.createElement('li'); const a = document.createElement('a');
    a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = source.title || source.url;
    li.appendChild(a); list.appendChild(li);
  }
  $('sourcesWrap').hidden = !(data.sources || []).length;
  const player = $('player');
  if (data.audio_base64) {
    const bytes = Uint8Array.from(atob(data.audio_base64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: data.audio_mime_type || 'audio/mpeg' });
    if (player.dataset.objectUrl) URL.revokeObjectURL(player.dataset.objectUrl);
    const objectUrl = URL.createObjectURL(blob); player.src = objectUrl; player.dataset.objectUrl = objectUrl;
    player.play().catch(() => {});
  } else { player.removeAttribute('src'); }
}
async function submitText(event) {
  event?.preventDefault();
  const query = $('query').value.trim();
  if (!query) return;
  setBusy(true, 'Thinking and preparing the answer…');
  try {
    const data = await requestJSON('/api/text', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,response_language:languageValue() || null,research:researchValue()==='auto'?null:researchValue()==='true'})});
    renderResult(data); setStatus('Answer ready. Sources are listed when web grounding returned them.');
  } catch (error) { setStatus(error.message, 'error'); }
  finally { setBusy(false); }
}
$('textForm').addEventListener('submit', submitText);

recordButton.addEventListener('click', async () => {
  try {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw new Error('This browser does not support microphone recording. Try a current Chrome or Edge browser over localhost/HTTPS.');
    stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1, echoCancellation:true, noiseSuppression:true, autoGainControl:true}});
    chunks = [];
    const options = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? {mimeType:'audio/webm;codecs=opus'} : {};
    recorder = new MediaRecorder(stream, options);
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onstop = async () => {
      stream?.getTracks().forEach(track => track.stop()); stream = null;
      const blob = new Blob(chunks, {type:recorder.mimeType || 'audio/webm'});
      recorder = null;
      if (!blob.size) { setStatus('No audio captured. Please try again.', 'error'); setBusy(false); return; }
      const form = new FormData(); form.append('audio', blob, blob.type.includes('mp4') ? 'recording.mp4' : 'recording.webm');
      if (languageValue()) form.append('response_language', languageValue());
      form.append('research', researchValue());
      setBusy(true, 'Transcribing, researching, and generating speech…');
      try { const data = await requestJSON('/api/voice', {method:'POST',body:form}); renderResult(data); setStatus('Answer ready.'); }
      catch (error) { setStatus(error.message, 'error'); }
      finally { setBusy(false); }
    };
    recorder.start(250); recordButton.disabled = true; stopButton.disabled = false;
    $('recordLabel').textContent = 'Recording…'; setStatus('Listening. Ask one short question, then press Stop & ask (max 28 seconds).', 'busy');
    clearTimeout(recordingTimer);
    recordingTimer = setTimeout(() => {
      if (recorder && recorder.state === 'recording') {
        setStatus('Reached the 28-second recording limit. Processing your question…', 'busy');
        stopButton.disabled = true; $('recordLabel').textContent = 'Start recording'; recorder.stop();
      }
    }, 28000);
  } catch (error) { setStatus(error.message, 'error'); stream?.getTracks().forEach(track=>track.stop()); stream=null; setBusy(false); }
});
stopButton.addEventListener('click', () => {
  clearTimeout(recordingTimer);
  if (recorder && recorder.state === 'recording') {
    stopButton.disabled = true; $('recordLabel').textContent = 'Start recording';
    setStatus('Uploading audio…', 'busy'); recorder.stop();
  }
});
