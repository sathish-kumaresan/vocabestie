// Text-to-Speech Helper for Vocabestie - v6.6 Improved
// Implements strict Swedish voice selection and Cloud TTS fallback support

const TTS = {
    speaking: false,
    voices: [],
    voicesLoaded: false,
    preferredVoiceURI: localStorage.getItem('vocabestie_preferred_voice'), // Persist user choice

    // Initialize voices
    init() {
        if (!window.speechSynthesis) {
            console.error('Speech synthesis not supported');
            return;
        }

        const loadVoices = () => {
            TTS.voices = window.speechSynthesis.getVoices();
            TTS.voicesLoaded = true;
            console.log(`TTS: Loaded ${TTS.voices.length} voices`);

            // Debug available Swedish voices
            const swedish = TTS.voices.filter(v => v.lang.startsWith('sv'));
            console.log('TTS: Available Swedish voices:', swedish.map(v => `${v.name} (${v.lang})`));

            // Dispatch event for UI updates
            window.dispatchEvent(new CustomEvent('voices_loaded', { detail: { voices: TTS.voices } }));
        };

        loadVoices();

        // Chrome loads voices asynchronously
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = loadVoices;
        }
    },

    // Strict Swedish Voice Finder
    getSwedishVoice() {
        if (!TTS.voices.length) {
            TTS.voices = window.speechSynthesis.getVoices();
        }

        // 1. User Preferred Voice (if valid and is Swedish)
        if (TTS.preferredVoiceURI) {
            const preferred = TTS.voices.find(v => v.voiceURI === TTS.preferredVoiceURI);
            if (preferred && preferred.lang.startsWith('sv')) {
                return preferred;
            }
        }

        // 2. High-Quality "Google" Swedish Voice (Chrome/Android)
        // Usually named "Google Svenska" or similar
        const googleSv = TTS.voices.find(v => v.name.includes('Google') && v.lang.startsWith('sv'));
        if (googleSv) return googleSv;

        // 3. Exact Region Match (sv-SE)
        const exactSv = TTS.voices.find(v => v.lang === 'sv-SE');
        if (exactSv) return exactSv;

        // 4. Any Swedish Voice (sv, sv-FI, etc.)
        const anySv = TTS.voices.find(v => v.lang.startsWith('sv'));
        if (anySv) return anySv;

        return null; // Strict mode: Fail if no Swedish voice
    },

    // Retrieve all Swedish voices for the picker UI
    getAllSwedishVoices() {
        if (!TTS.voices.length) TTS.voices = window.speechSynthesis.getVoices();
        return TTS.voices.filter(v => v.lang.startsWith('sv'));
    },

    // Set user preference
    setPreferredVoice(voiceURI) {
        TTS.preferredVoiceURI = voiceURI;
        localStorage.setItem('vocabestie_preferred_voice', voiceURI);
        console.log('TTS: Preference saved:', voiceURI);
    },

    // Core Speak Function
    // Supports static audioUrl (Cloud TTS) check in future
    // Core Speak Function
    // Tries Server cached audio (gTTS) first, falls back to Web Speech
    speak(text, options = {}) {
        return new Promise((resolve, reject) => {
            const stopPrevious = () => {
                window.speechSynthesis.cancel();
                TTS.speaking = false;
            };

            stopPrevious();
            TTS.speaking = true;

            // STRATEGY: Try Server Audio First
            const encodedText = encodeURIComponent(text);
            fetch(`/api/audio/tts?text=${encodedText}`)
                .then(res => {
                    if (!res.ok) throw new Error('Server TTS failed');
                    return res.json();
                })
                .then(data => {
                    // Play Audio File
                    const audio = new Audio(data.audio_url);
                    audio.playbackRate = options.rate || 1.0;

                    audio.onended = () => {
                        TTS.speaking = false;
                        resolve();
                    };

                    audio.onerror = (e) => {
                        console.warn('Audio file playback failed, falling back:', e);
                        // Fallback to Web Speech if file fails
                        TTS.speakWebSpeech(text, options).then(resolve).catch(reject);
                    };

                    console.log(`TTS: Playing server audio for "${text}"`);
                    audio.play().catch(e => {
                        console.warn('Autoplay prevented or error:', e);
                        TTS.speakWebSpeech(text, options).then(resolve).catch(reject);
                    });
                })
                .catch(err => {
                    console.warn(`TTS: Server audio skipped (${err.message}), using Web Speech fallback.`);
                    TTS.speakWebSpeech(text, options).then(resolve).catch(reject);
                });
        });
    },

    // Fallback Web Speech Implementation (Legacy/Backup)
    speakWebSpeech(text, options = {}) {
        return new Promise((resolve, reject) => {
            const voice = TTS.getSwedishVoice();

            // FALLBACK WARNING
            if (!voice) {
                console.warn('TTS: No Swedish voice detected.');
                window.dispatchEvent(new CustomEvent('tts_error', {
                    detail: { message: 'No Swedish voice detected. Please install a Swedish language pack.' }
                }));
                TTS.speaking = false;
                reject('No Swedish voice found');
                return;
            }

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.voice = voice;
            utterance.lang = voice.lang;
            utterance.rate = options.rate || 0.9;
            utterance.pitch = options.pitch || 1.0;
            utterance.volume = 1.0;

            utterance.onstart = () => { TTS.speaking = true; };
            utterance.onend = () => {
                TTS.speaking = false;
                resolve();
            };
            utterance.onerror = (e) => {
                TTS.speaking = false;
                if (e.error !== 'interrupted' && e.error !== 'canceled') {
                    reject(e.error);
                } else {
                    resolve();
                }
            };

            console.log(`TTS: Speaking "${text}" using Web Speech ${voice.name}`);
            window.speechSynthesis.speak(utterance);
        });
    },

    speakWord(word, example = null, audioUrl = null) {
        return TTS.speak(word, { audioUrl }).then(() => {
            if (example) {
                // Pause slightly before example
                return new Promise(r => setTimeout(r, 500))
                    .then(() => TTS.speak(example, { rate: 0.85 })); // Slower for sentences
            }
        });
    },

    stop() {
        window.speechSynthesis.cancel();
        TTS.speaking = false;
    },

    isSpeaking() {
        return TTS.speaking || window.speechSynthesis.speaking;
    }
};

// UI Helper: Visual Feedback on Buttons
function speakText(text, button = null) {
    if (button) button.classList.add('speaking', 'animate-pulse');

    TTS.speak(text)
        .catch(err => console.warn('Speak failed:', err))
        .finally(() => {
            if (button) button.classList.remove('speaking', 'animate-pulse');
        });
}

function speakWordAndExample(word, example, button = null) {
    if (button) button.classList.add('speaking', 'animate-pulse');

    TTS.speakWord(word, example)
        .catch(err => console.warn('Speak sequence failed:', err))
        .finally(() => {
            if (button) button.classList.remove('speaking', 'animate-pulse');
        });
}


// Initialization
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TTS.init());
} else {
    TTS.init();
}

// Global Error Handler for TTS (to show toasts)
window.addEventListener('tts_error', (e) => {
    // User requested to remove this alert.
    console.warn("TTS Error suppressed:", e.detail.message);
});
