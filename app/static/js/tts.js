// Text-to-Speech Helper for Vocabestie

const TTS = {
    speaking: false,
    voices: [],
    voicesLoaded: false,

    // Initialize voices - must be called after page load
    init() {
        if (!window.speechSynthesis) {
            console.warn('Speech synthesis not supported');
            return;
        }

        // Load voices
        const loadVoices = () => {
            TTS.voices = window.speechSynthesis.getVoices();
            TTS.voicesLoaded = true;
            console.log('TTS: Loaded', TTS.voices.length, 'voices');

            // Log Swedish voices for debugging
            const swedishVoices = TTS.voices.filter(v => v.lang.startsWith('sv'));
            console.log('TTS: Swedish voices available:', swedishVoices.map(v => `${v.name} (${v.lang})`));
        };

        // Voices may already be loaded
        loadVoices();

        // Chrome loads voices asynchronously
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = loadVoices;
        }
    },

    // Find the best voice for a language
    findVoice(lang) {
        if (!TTS.voices.length) {
            TTS.voices = window.speechSynthesis.getVoices();
        }

        // Exact match first (e.g., 'sv-SE')
        let voice = TTS.voices.find(v => v.lang === lang);

        // Partial match (e.g., 'sv' matches 'sv-SE')
        if (!voice) {
            const langPrefix = lang.split('-')[0];
            voice = TTS.voices.find(v => v.lang.startsWith(langPrefix));
        }

        // Prefer native/local voices over remote ones
        if (!voice) {
            voice = TTS.voices.find(v => v.lang.startsWith(lang.split('-')[0]) && v.localService);
        }

        return voice;
    },

    speak(text, options = {}) {
        if (!window.speechSynthesis) {
            console.warn('Speech synthesis not supported');
            return Promise.reject('Speech synthesis not supported');
        }

        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            const lang = options.lang || 'en-US';
            utterance.lang = lang;
            utterance.rate = options.rate || 0.9;
            utterance.pitch = options.pitch || 1;
            utterance.volume = options.volume || 1;

            // Find and set the best voice for the language
            const voice = TTS.findVoice(lang);
            if (voice) {
                utterance.voice = voice;
                console.log('TTS: Using voice:', voice.name, voice.lang);
            } else {
                console.warn('TTS: No voice found for', lang, '- using default');
            }

            utterance.onstart = () => {
                TTS.speaking = true;
            };

            utterance.onend = () => {
                TTS.speaking = false;
                resolve();
            };

            utterance.onerror = (event) => {
                TTS.speaking = false;
                reject(event.error);
            };

            window.speechSynthesis.speak(utterance);
        });
    },

    speakWord(word, example = null) {
        // Speak the word, then optionally the example
        return TTS.speak(word).then(() => {
            if (example) {
                return new Promise(resolve => setTimeout(resolve, 500))
                    .then(() => TTS.speak(example, { rate: 0.85 }));
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

// Audio button click handler
function speakText(text, button = null) {
    if (button) {
        button.classList.add('speaking');
    }

    TTS.speak(text).finally(() => {
        if (button) {
            button.classList.remove('speaking');
        }
    });
}

function speakWordAndExample(word, example, button = null) {
    if (button) {
        button.classList.add('speaking');
    }

    TTS.speakWord(word, example).finally(() => {
        if (button) {
            button.classList.remove('speaking');
        }
    });
}

// Initialize TTS when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TTS.init());
} else {
    TTS.init();
}
