// Speech Recognition Helper for Vocabestie
// Handles microphone input and Swedish STT

const Speech = {
    recognition: null,
    isRecording: false,
    hasFinalResult: false,
    lastInterim: '',
    retryCount: 0,

    init() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('Speech recognition not supported');
            return false;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        // Critical: Force Swedish language
        this.recognition.lang = 'sv-SE';

        // Settings
        this.recognition.continuous = false;
        this.recognition.interimResults = true; // Enabled for better sensitivity
        this.recognition.maxAlternatives = 1;

        this.setupListeners();
        return true;
    },

    setupListeners() {
        this.recognition.onstart = () => {
            Speech.isRecording = true;
            Speech.hasFinalResult = false;
            Speech.lastInterim = '';
            window.dispatchEvent(new Event('speech_start'));
        };

        this.recognition.onend = () => {
            Speech.isRecording = false;
            window.dispatchEvent(new Event('speech_end'));

            // Check results
            if (!Speech.hasFinalResult) {
                // If we have a lingering interim result, use it!
                if (Speech.lastInterim && Speech.lastInterim.trim().length > 0) {
                    console.log(`STT: Promoting interim "${Speech.lastInterim}" to final`);

                    window.dispatchEvent(new CustomEvent('speech_result', {
                        detail: {
                            transcript: Speech.lastInterim,
                            confidence: 0.6 // Lower confidence since it wasn't final
                        }
                    }));
                } else {
                    // Genuine silence
                    window.dispatchEvent(new CustomEvent('speech_no_result'));
                }
            }
        };

        this.recognition.onresult = (event) => {
            // Re-enforce language just in case
            // (Some browsers act weird)

            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (interimTranscript) {
                Speech.lastInterim = interimTranscript;
                console.log(`STT Interim: ${interimTranscript}`);
                window.dispatchEvent(new CustomEvent('speech_interim', {
                    detail: { transcript: interimTranscript }
                }));
            }

            if (finalTranscript) {
                Speech.hasFinalResult = true;
                console.log(`STT Final: "${finalTranscript}" (Confidence: High)`);

                window.dispatchEvent(new CustomEvent('speech_result', {
                    detail: {
                        transcript: finalTranscript,
                        confidence: event.results[0][0].confidence || 0.95
                    }
                }));
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            let message = 'Microphone error. Please try again.';

            if (event.error === 'no-speech') {
                message = 'No speech detected. Try speaking closer.';
            } else if (event.error === 'audio-capture') {
                message = 'No microphone found.';
            } else if (event.error === 'not-allowed') {
                message = 'Microphone permission denied.';
            }

            window.dispatchEvent(new CustomEvent('speech_error', {
                detail: { error: event.error, message: message }
            }));
        };
    },

    start() {
        if (!this.recognition) {
            if (!this.init()) {
                alert('Speech recognition is not supported in this browser. Please use Chrome.');
                return;
            }
        }

        // RE-ENFORCE LANGUAGE before every start
        this.recognition.lang = 'sv-SE';

        try {
            this.retryCount = 0; // Reset retries on manual start
            this.recognition.start();
        } catch (e) {
            console.error('Failed to start recognition:', e);
        }
    },

    stop() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
        }
    }
};

// Global helpers for inline HTML calls
window.startRecording = () => Speech.start();
window.stopRecording = () => Speech.stop();

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    Speech.init();
});
