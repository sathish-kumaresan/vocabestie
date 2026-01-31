// Pronunciation Recording Module for Vocabestie
// Replaces Web Speech API with MediaRecorder for reliable audio capture

const Pronunciation = {
    mediaRecorder: null,
    audioChunks: [],
    audioContext: null,
    analyser: null,
    stream: null,
    isRecording: false,
    userAudioUrl: null,
    levelMeterInterval: null,

    // Initialize audio context
    async init() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext();
            return true;
        } catch (e) {
            console.error('AudioContext not supported:', e);
            return false;
        }
    },

    // Request microphone and start recording
    async startRecording(onLevelUpdate) {
        try {
            // Request microphone
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                }
            });

            // Setup analyser for level meter
            if (!this.audioContext) await this.init();
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            const source = this.audioContext.createMediaStreamSource(this.stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);

            // Setup MediaRecorder
            this.audioChunks = [];
            const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
            this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });

            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.audioChunks.push(e.data);
                }
            };

            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;

            // Start level meter updates
            if (onLevelUpdate) {
                this.levelMeterInterval = setInterval(() => {
                    const level = this.getAudioLevel();
                    onLevelUpdate(level);
                }, 50);
            }

            window.dispatchEvent(new Event('recording_start'));
            return true;

        } catch (err) {
            console.error('Failed to start recording:', err);
            let message = 'Microphone error';
            if (err.name === 'NotAllowedError') {
                message = 'Microphone permission denied';
            } else if (err.name === 'NotFoundError') {
                message = 'No microphone found';
            }
            window.dispatchEvent(new CustomEvent('recording_error', { detail: { message } }));
            return false;
        }
    },

    // Get current audio level (0-100)
    getAudioLevel() {
        if (!this.analyser) return 0;
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        return Math.min(100, Math.round(average * 1.5));
    },

    // Stop recording and return audio blob
    async stopRecording() {
        return new Promise((resolve) => {
            if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
                resolve(null);
                return;
            }

            // Clear level meter
            if (this.levelMeterInterval) {
                clearInterval(this.levelMeterInterval);
                this.levelMeterInterval = null;
            }

            this.mediaRecorder.onstop = () => {
                const mimeType = this.mediaRecorder.mimeType;
                const blob = new Blob(this.audioChunks, { type: mimeType });

                // Create URL for playback
                if (this.userAudioUrl) {
                    URL.revokeObjectURL(this.userAudioUrl);
                }
                this.userAudioUrl = URL.createObjectURL(blob);

                // Stop all tracks
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                }

                this.isRecording = false;
                window.dispatchEvent(new CustomEvent('recording_stop', {
                    detail: { blob, url: this.userAudioUrl }
                }));
                resolve(blob);
            };

            this.mediaRecorder.stop();
        });
    },

    // Check if audio has content (not silence)
    async hasAudioContent(blob) {
        if (!blob || blob.size < 1000) return false; // Less than 1KB is likely silence

        try {
            const arrayBuffer = await blob.arrayBuffer();
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            const data = audioBuffer.getChannelData(0);

            // Calculate RMS energy
            let sumSquares = 0;
            for (let i = 0; i < data.length; i++) {
                sumSquares += data[i] * data[i];
            }
            const rms = Math.sqrt(sumSquares / data.length);
            return rms > 0.01; // Threshold for speech vs silence
        } catch (e) {
            console.warn('Could not analyze audio:', e);
            return blob.size > 2000; // Fallback to size check
        }
    },

    // Play user's recording
    playUserRecording() {
        if (this.userAudioUrl) {
            const audio = new Audio(this.userAudioUrl);
            audio.play();
            return audio;
        }
        return null;
    },

    // Get the recorded blob for upload
    getRecordedBlob() {
        if (this.audioChunks.length === 0) return null;
        const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
        return new Blob(this.audioChunks, { type: mimeType });
    },

    // Feature detection
    isSupported() {
        return !!(navigator.mediaDevices &&
            navigator.mediaDevices.getUserMedia &&
            window.MediaRecorder);
    }
};

// ==========================================
// UI Orchestrator for Speaking Exercise
// ==========================================
const SpeakExerciseUI = {
    elements: {},
    state: {
        recordingStartTime: null,
        timerInterval: null,
        lastScore: 0,
        lastTranscript: '',
        wordId: null,
        expectedWord: ''
    },

    init(wordId, expectedWord) {
        this.state.wordId = wordId;
        this.state.expectedWord = expectedWord;
        this.bindElements();

        if (!Pronunciation.isSupported()) {
            if (this.elements.micStatus) this.elements.micStatus.textContent = 'Recording not supported';
            if (this.elements.micBtn) {
                this.elements.micBtn.disabled = true;
                this.elements.micBtn.classList.add('opacity-50');
            }
            return;
        }

        Pronunciation.init();

        // Attach listeners
        if (this.elements.micBtn) {
            // Remove old listeners by cloning
            const newBtn = this.elements.micBtn.cloneNode(true);
            this.elements.micBtn.parentNode.replaceChild(newBtn, this.elements.micBtn);
            this.elements.micBtn = newBtn;

            this.elements.micBtn.addEventListener('click', async () => {
                if (Pronunciation.isRecording) {
                    await this.stopAndAnalyze();
                } else {
                    await this.startRecording();
                }
            });
        }

        // Expose global actions for inline onclick handlers
        window.playNativeAudio = () => TTS.speak(this.state.expectedWord);
        window.playUserRecording = () => Pronunciation.playUserRecording();
        window.resetExercise = () => this.resetUI();
        window.submitAndContinue = () => this.submitResult();
        window.skipExercise = () => this.skip();
    },

    bindElements() {
        this.elements = {
            micBtn: document.getElementById('mic-btn'),
            micRipple: document.getElementById('mic-ripple'),
            micStatus: document.getElementById('mic-status'),
            levelSection: document.getElementById('level-meter-section'),
            levelBar: document.getElementById('level-bar'),
            recordingTime: document.getElementById('recording-time'),
            scoreSection: document.getElementById('score-section'),
            playbackSection: document.getElementById('playback-section'),
            resultSection: document.getElementById('result-section'),
            resultText: document.getElementById('result-text'),
            heardText: document.getElementById('heard-text'),
            actionSection: document.getElementById('action-section'),
            syllablesContainer: document.getElementById('syllables-container')
        };
    },

    async startRecording() {
        this.resetUI();

        const success = await Pronunciation.startRecording((level) => {
            if (this.elements.levelBar) this.elements.levelBar.style.width = `${level}%`;
        });

        if (success) {
            this.elements.micBtn.classList.remove('bg-swedish-blue', 'hover:bg-blue-600');
            this.elements.micBtn.classList.add('bg-red-600', 'hover:bg-red-700');
            this.elements.micRipple.classList.remove('hidden');
            this.elements.micStatus.textContent = 'Recording... Tap to stop';
            this.elements.micStatus.className = 'text-red-400 text-sm mt-3 font-medium';
            this.elements.levelSection.classList.remove('hidden');

            this.state.recordingStartTime = Date.now();
            this.state.timerInterval = setInterval(() => {
                const elapsed = ((Date.now() - this.state.recordingStartTime) / 1000).toFixed(1);
                if (this.elements.recordingTime) this.elements.recordingTime.textContent = elapsed;
            }, 100);
        }
    },

    async stopAndAnalyze() {
        if (this.state.timerInterval) {
            clearInterval(this.state.timerInterval);
            this.state.timerInterval = null;
        }

        this.elements.micBtn.classList.add('bg-swedish-blue', 'hover:bg-blue-600');
        this.elements.micBtn.classList.remove('bg-red-600', 'hover:bg-red-700');
        this.elements.micRipple.classList.add('hidden');
        this.elements.levelSection.classList.add('hidden');
        this.elements.micStatus.textContent = 'Analyzing...';
        this.elements.micStatus.className = 'text-gray-400 text-sm mt-3 font-medium';

        const blob = await Pronunciation.stopRecording();

        if (!blob || !await Pronunciation.hasAudioContent(blob)) {
            this.showResult(0, '', 'No speech detected. Try speaking louder.');
            return;
        }

        this.elements.playbackSection.classList.remove('hidden');

        // Analyze
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        formData.append('word_id', this.state.wordId);

        try {
            const response = await fetch('/api/speech/analyze', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.showResult(data.score, data.transcription, data.feedback, data.syllables);
            } else {
                this.showResult(50, '', 'Analysis error. Good effort!');
            }
        } catch (e) {
            console.error(e);
            this.showResult(50, '', 'Connection error. Good effort!');
        }
    },

    showResult(score, transcript, feedback, syllables) {
        this.state.lastScore = score;
        this.state.lastTranscript = transcript;

        AudioVisualizer.updateScoreGauge(score);

        if (syllables && this.elements.syllablesContainer) {
            AudioVisualizer.displaySyllables('syllables-container', syllables);
        }

        this.elements.scoreSection.classList.remove('hidden');

        if (score >= 70) {
            this.elements.resultText.textContent = feedback || 'Good job!';
            this.elements.resultText.className = 'text-lg font-medium text-green-400';
        } else if (score >= 40) {
            this.elements.resultText.textContent = feedback || 'Keep practicing';
            this.elements.resultText.className = 'text-lg font-medium text-yellow-400';
        } else {
            this.elements.resultText.textContent = feedback || 'Try again';
            this.elements.resultText.className = 'text-lg font-medium text-red-400';
        }

        if (transcript) {
            this.elements.heardText.textContent = `Heard: "${transcript}"`;
            this.elements.heardText.classList.remove('hidden');
        } else {
            this.elements.heardText.classList.add('hidden');
        }

        this.elements.resultSection.classList.remove('hidden');
        this.elements.actionSection.classList.remove('hidden');
        this.elements.micStatus.textContent = 'Tap to try again';
    },

    resetUI() {
        this.elements.scoreSection.classList.add('hidden');
        this.elements.playbackSection.classList.add('hidden');
        this.elements.resultSection.classList.add('hidden');
        this.elements.actionSection.classList.add('hidden');
        this.elements.micStatus.textContent = 'Tap to record';
    },

    submitResult() {
        fetch('/learn/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word_id: parseInt(this.state.wordId),
                skill_type: 'speak',
                answer: this.state.lastTranscript || this.state.expectedWord
            })
        })
            .then(() => window.location.reload())
            .catch(() => window.location.reload());
    },

    skip() {
        fetch('/learn/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word_id: parseInt(this.state.wordId),
                skill_type: 'speak',
                answer: ''
            })
        }).finally(() => window.location.reload());
    }
};

window.Pronunciation = Pronunciation;
window.SpeakExerciseUI = SpeakExerciseUI;
