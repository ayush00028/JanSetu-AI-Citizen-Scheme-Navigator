let isListening = false;
let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];
let voiceEnabled = localStorage.getItem('csn_voice_enabled') !== 'false';

function setVoiceEnabled(enabled) {
  voiceEnabled = enabled;
  localStorage.setItem('csn_voice_enabled', String(enabled));
  const mic = document.getElementById('micBtn');
  if (mic) { mic.disabled = !enabled; mic.setAttribute('aria-disabled', String(!enabled)); }
  if (!enabled && isListening) stopListening();
}
function resetRecorder() {
  isListening = false;
  document.getElementById('micBtn')?.classList.remove('listening');
  mediaStream?.getTracks().forEach(track => track.stop());
  mediaStream = null; mediaRecorder = null;
}
function stopListening() { if (mediaRecorder?.state === 'recording') mediaRecorder.stop(); }
async function toggleListening(onResult) {
  if (!voiceEnabled || currentLang !== 'hi') { alert('Choose हिन्दी to use Hindi voice input.'); return; }
  const micBtn = document.getElementById('micBtn');
  if (isListening) { stopListening(); return; }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { alert('Voice input is not supported in this browser.'); return; }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = 'audio/webm;codecs=opus';
    mediaRecorder = new MediaRecorder(mediaStream, MediaRecorder.isTypeSupported(mimeType) ? { mimeType } : undefined);
    audioChunks = [];
    mediaRecorder.ondataavailable = event => { if (event.data.size) audioChunks.push(event.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      resetRecorder();
      const formData = new FormData(); formData.append('audio', blob, 'hindi-voice.webm');
      try {
        const response = await fetch('/api/chat/transcribe', { method: 'POST', body: formData, credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Voice transcription failed.');
        onResult(data.transcript);
      } catch (error) { alert(error.message || 'Voice transcription failed.'); }
    };
    mediaRecorder.start(); isListening = true; micBtn?.classList.add('listening');
    window.setTimeout(() => { if (isListening) stopListening(); }, 55000);
  } catch (_) { resetRecorder(); alert('Microphone permission is required for Hindi voice input.'); }
}
function speakText(text, lang = 'en') {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-IN'; utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
}
function speakSteps(steps, lang = 'en') { speakText(steps.map((s, i) => `Step ${i + 1}: ${s.title}. ${s.description}`).join('. '), lang); }
