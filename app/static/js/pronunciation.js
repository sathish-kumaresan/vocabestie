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

            // Start level meter & silence detection
            let silenceStart = null;
            let speechDetected = false;
            const SILENCE_THRESHOLD = 5; // Level below this is silence
            const AUTO_STOP_DELAY = 1500; // Stop after 1.5s of silence
            const MIN_SPEECH_DURATION = 500; // Must speak for 0.5s to arm auto-stop
            let speechStartTime = null;

            if (onLevelUpdate) {
                this.levelMeterInterval = setInterval(() => {
                    const level = this.getAudioLevel();
                    onLevelUpdate(level);

                    // Auto-stop logic
                    if (level > SILENCE_THRESHOLD) {
                        silenceStart = null;
                        if (!speechDetected) {
                            speechStartTime = Date.now();
                        }
                        if (Date.now() - speechStartTime > MIN_SPEECH_DURATION) {
                            speechDetected = true;
                        }
                    } else {
                        if (speechDetected) {
                            if (!silenceStart) silenceStart = Date.now();
                            else if (Date.now() - silenceStart > AUTO_STOP_DELAY) {
                                // Auto-stop!
                                console.log('Auto-stopping due to silence');
                                if (this.isRecording) {
                                    // Dispatch event or callback (we'll emit a custom event to UI)
                                    window.dispatchEvent(new Event('autostop_trigger'));
                                }
                            }
                        }
                    }
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

    // Decode blob to AudioBuffer
    async decodeAudio(blob) {
        if (!blob) return null;
        try {
            const arrayBuffer = await blob.arrayBuffer();
            return await this.audioContext.decodeAudioData(arrayBuffer);
        } catch (e) {
            console.error('Failed to decode audio:', e);
            return null;
        }
    },

    // Check if audio has content (not silence)
    async hasAudioContent(blob) {
        if (!blob || blob.size < 1000) return false; // Less than 1KB is likely silence

        try {
            const audioBuffer = await this.decodeAudio(blob);
            if (!audioBuffer) return blob.size > 2000;

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

    init(wordId, expectedWord, onComplete) {
        this.state.wordId = wordId;
        this.state.expectedWord = expectedWord;
        this.state.nativeBuffer = null; // Store native audio buffer
        this.onComplete = onComplete || (() => window.location.reload());
        this.bindElements();

        // Pre-fetch native audio for comparison
        this.prefetchNativeAudio();

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

            // Listen for auto-stop
            window.addEventListener('autostop_trigger', async () => {
                if (Pronunciation.isRecording) {
                    await this.stopAndAnalyze();
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

    async prefetchNativeAudio() {
        if (!this.state.expectedWord) return;
        try {
            const encodedText = encodeURIComponent(this.state.expectedWord);
            const res = await fetch(`/api/audio/tts?text=${encodedText}`);
            if (res.ok) {
                const data = await res.json();
                if (data.audio_url) {
                    const audioRes = await fetch(data.audio_url);
                    const blob = await audioRes.blob();
                    this.state.nativeBuffer = await Pronunciation.decodeAudio(blob);
                }
            }
        } catch (e) {
            console.warn('Native audio prefetch failed:', e);
        }
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

        // Draw Waveform immediately (updated with native buffer when analysis completes)
        try {
            const audioBuffer = await Pronunciation.decodeAudio(blob);

            // --- INSTANT CLIENT-SIDE SCORING (Seamless) ---
            let instantScore = 0;
            if (audioBuffer && this.state.nativeBuffer) {
                // 1. Calculate matching score (0-100)
                instantScore = AudioMatcher.compare(audioBuffer, this.state.nativeBuffer);
                console.log('Instant Client Score:', instantScore);

                // 2. Show result IMMEDIATELY
                AudioVisualizer.drawDualWaveform('waveform-canvas', audioBuffer, this.state.nativeBuffer, instantScore);
                this.showResult(instantScore, '...', 'Verifying...', null);

                // Show "Checking..." state without blocking
                this.elements.micStatus.textContent = 'Verifying...';
            } else if (audioBuffer) {
                // No native audio to compare? Default to green/100 for now.
                AudioVisualizer.drawDualWaveform('waveform-canvas', audioBuffer, null, 100);
            }

            this.elements.playbackSection.classList.remove('hidden');

            // --- BACKGROUND SERVER VERIFICATION ---
            const formData = new FormData();
            formData.append('audio', blob, 'recording.webm');
            formData.append('word_id', this.state.wordId);

            // Fire and adjust (non-blocking feel)
            fetch('/api/speech/analyze', {
                method: 'POST',
                body: formData
            }).then(async (res) => {
                if (res.ok) {
                    const data = await res.json();

                    // Reconciliation Strategy:
                    // 1. Trust client match for "How close it sounds"
                    // 2. Trust server Whisper for "Did they say the right word?"

                    if (data.score === 0) {
                        // Whisper says: "Wrong word" or "Silence" -> Overwrite instant score
                        this.showResult(0, data.transcription, data.feedback, data.syllables);
                        if (audioBuffer) AudioVisualizer.drawDualWaveform('waveform-canvas', audioBuffer, this.state.nativeBuffer, 0);
                    } else {
                        // Whisper agrees it's the right word.
                        // STRATEGY: Base Score (80) + Waveform Bonus (0-20)
                        // This guarantees that if you say the correct word, you get at least "Excellent" (80%),
                        // and a perfect waveform match bumps you to 100%.

                        const bonus = Math.round(instantScore * 0.2);
                        const hybridScore = 80 + bonus;

                        console.log(`Hybrid Score: ${hybridScore} (Base: 80 + Bonus: ${bonus} [from client ${instantScore}])`);

                        // Generate new feedback based on the FINAL score
                        let finalFeedback = '';
                        if (hybridScore >= 95) finalFeedback = 'Perfect pronunciation!';
                        else if (hybridScore >= 80) finalFeedback = 'Excellent!';
                        else if (hybridScore >= 60) finalFeedback = 'Good job!';
                        else finalFeedback = 'Try again.';

                        // Use hybridScore and our derived feedback
                        this.showResult(hybridScore, data.transcription, finalFeedback, data.syllables);

                        // Subtle update to waveform color if category changed
                        if (audioBuffer) AudioVisualizer.drawDualWaveform('waveform-canvas', audioBuffer, this.state.nativeBuffer, hybridScore);
                    }
                }
            }).catch(e => console.error("Background verification failed:", e));

        } catch (e) {
            console.error('Analysis flow error:', e);
            this.showResult(50, '', 'Error. Please try again.');
        }
    },

    showResult(score, transcript, feedback, syllables) {
        this.state.lastScore = score;
        this.state.lastTranscript = transcript;

        AudioVisualizer.updateScoreGauge(score);

        // Hide the generic label under the gauge since we show specific feedback below
        const scoreLabel = document.getElementById('score-label');
        if (scoreLabel) scoreLabel.textContent = '';

        if (scoreLabel) scoreLabel.textContent = '';

        this.elements.scoreSection.classList.remove('hidden');

        if (score >= 80) {
            this.elements.resultText.textContent = feedback || 'Excellent!';
            this.elements.resultText.className = 'text-lg font-medium text-green-400';
        } else if (score >= 60) {
            this.elements.resultText.textContent = feedback || 'Good job!';
            this.elements.resultText.className = 'text-lg font-medium text-teal-400';
        } else if (score >= 40) {
            this.elements.resultText.textContent = feedback || 'Keep practicing';
            this.elements.resultText.className = 'text-lg font-medium text-yellow-400';
        } else {
            this.elements.resultText.textContent = feedback || 'Try again';
            this.elements.resultText.className = 'text-lg font-medium text-red-400';
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
            .then(() => this.onComplete())
            .catch(() => this.onComplete());
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
        }).finally(() => this.onComplete());
    }
};

window.Pronunciation = Pronunciation;
window.SpeakExerciseUI = SpeakExerciseUI;
