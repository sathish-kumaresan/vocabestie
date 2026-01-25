// Text-to-Speech Helper for Vocabestie

const TTS = {
    speaking: false,

    speak(text, options = {}) {
        if (!window.speechSynthesis) {
            console.warn('Speech synthesis not supported');
            return Promise.reject('Speech synthesis not supported');
        }

        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = options.lang || 'en-US';
            utterance.rate = options.rate || 0.9;
            utterance.pitch = options.pitch || 1;
            utterance.volume = options.volume || 1;

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
