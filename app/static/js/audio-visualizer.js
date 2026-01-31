// Audio Visualizer for Vocabestie Speaking Exercises
// Provides level meter and simple waveform display

const AudioVisualizer = {
    // Update level meter bar (0-100)
    updateLevelMeter(elementId, level) {
        const bar = document.getElementById(elementId);
        if (bar) {
            bar.style.width = `${level}%`;
            // Color based on level
            if (level > 70) {
                bar.className = bar.className.replace(/from-\w+-500/g, 'from-red-500');
            } else if (level > 40) {
                bar.className = bar.className.replace(/from-\w+-500/g, 'from-yellow-500');
            } else {
                bar.className = bar.className.replace(/from-\w+-500/g, 'from-green-500');
            }
        }
    },

    // Update circular score gauge (0-100)
    updateScoreGauge(score, arcId = 'score-arc', valueId = 'score-value', labelId = 'score-label') {
        const arc = document.getElementById(arcId);
        const value = document.getElementById(valueId);
        const label = document.getElementById(labelId);

        if (arc) {
            // Circle circumference = 2 * PI * r = 2 * 3.14159 * 45 ≈ 283
            const circumference = 283;
            const offset = circumference - (score / 100) * circumference;
            arc.style.strokeDashoffset = offset;

            // Color based on score
            let color = '#ef4444'; // red
            if (score >= 90) color = '#10b981'; // green
            else if (score >= 70) color = '#14b8a6'; // teal
            else if (score >= 50) color = '#eab308'; // yellow
            else if (score >= 30) color = '#f97316'; // orange
            arc.style.stroke = color;
        }

        if (value) {
            value.textContent = score;
        }

        if (label) {
            if (score >= 100) label.textContent = 'Perfect!';
            else if (score >= 80) label.textContent = 'Excellent!';
            else if (score >= 60) label.textContent = 'Good job!';
            else if (score >= 40) label.textContent = 'Getting closer';
            else label.textContent = 'Try again';
        }
    },

    // Display syllable breakdown with color coding
    displaySyllables(containerId, syllables) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';
        syllables.forEach(s => {
            const chip = document.createElement('span');
            chip.className = 'px-3 py-1 rounded-full text-sm font-medium ';

            // Color based on score
            if (s.score >= 80) {
                chip.className += 'bg-green-500/20 text-green-400';
            } else if (s.score >= 60) {
                chip.className += 'bg-teal-500/20 text-teal-400';
            } else if (s.score >= 40) {
                chip.className += 'bg-yellow-500/20 text-yellow-400';
            } else {
                chip.className += 'bg-red-500/20 text-red-400';
            }

            chip.textContent = `${s.syllable} (${s.score}%)`;
            container.appendChild(chip);
        });
    },

    // Trim silence from AudioBuffer
    trimSilence(audioBuffer) {
        if (!audioBuffer) return null;
        const data = audioBuffer.getChannelData(0);
        const threshold = 0.02; // Silence threshold

        let start = 0;
        let end = data.length - 1;

        // Find start
        while (start < end && Math.abs(data[start]) < threshold) start++;

        // Find end
        while (end > start && Math.abs(data[end]) < threshold) end--;

        if (start >= end) return audioBuffer; // Return original if all silence (or empty)

        const trimmedLength = end - start + 1;

        // Use an OfflineAudioContext to create the buffer synchronously if possible,
        // or just use window.AudioContext if available but DO NOT initialize a real context for just creating a buffer if not needed.
        // Actually, AudioContext.createBuffer is just a factory method. We can reuse a single dummy context or just reuse the source context if passed.
        // To be safe and avoid context limits, we use a cached offline context for buffer creation.
        if (!this._offlineCtx) {
            this._offlineCtx = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(1, 44100, 44100);
        }

        const trimmed = this._offlineCtx.createBuffer(1, trimmedLength, audioBuffer.sampleRate);
        trimmed.copyToChannel(data.subarray(start, end + 1), 0);
        return trimmed;
    },

    // Dual-color waveform comparison
    // userBuffer: Top (Green/Orange based on score/correctness)
    // nativeBuffer: Bottom (Always Green)
    drawDualWaveform(canvasId, userBuffer, nativeBuffer = null, score = 100) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !userBuffer) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const mid = height / 2;

        // Trim buffers for accurate comparison
        const userTrimmed = this.trimSilence(userBuffer);
        const nativeTrimmed = nativeBuffer ? this.trimSilence(nativeBuffer) : null;

        const userData = userTrimmed.getChannelData(0);
        const nativeData = nativeTrimmed ? nativeTrimmed.getChannelData(0) : null;

        ctx.clearRect(0, 0, width, height);

        // Configuration
        const barWidth = 3;
        const gap = 1;

        // Calculate total bars based on canvas size
        const totalBars = Math.floor(width / (barWidth + gap));

        // User Step (Top)
        const userStep = Math.floor(userData.length / totalBars);
        // Native Step (Bottom) - normalize to width so they align visually in duration
        const nativeStep = nativeData ? Math.floor(nativeData.length / totalBars) : 0;

        // Colors
        // User color based on score (Green if >= 70, Orange if < 70)
        const userColorStart = score >= 70 ? '#22c55e' : '#f97316'; // Green-500 : Orange-500
        const userColorEnd = score >= 70 ? '#86efac' : '#fdba74';   // Green-300 : Orange-300

        const gradUser = ctx.createLinearGradient(0, mid, 0, 0);
        gradUser.addColorStop(0, userColorStart);
        gradUser.addColorStop(1, userColorEnd);

        const gradNative = ctx.createLinearGradient(0, mid, 0, height);
        gradNative.addColorStop(0, '#22c55e'); // Green-500 (Always green for native)
        gradNative.addColorStop(1, '#86efac'); // Green-300

        // Draw separator line
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.moveTo(0, mid);
        ctx.lineTo(width, mid);
        ctx.stroke();

        for (let i = 0; i < totalBars; i++) {
            const x = i * (barWidth + gap);

            // --- Draw User (Top) ---
            let userSum = 0;
            const userStart = i * userStep;
            // Prevent OOB
            if (userStep > 0) {
                for (let j = 0; j < userStep; j++) {
                    if (userStart + j < userData.length) userSum += Math.abs(userData[userStart + j]);
                }
                const userAvg = userSum / userStep;
                const userAmp = Math.min(1.0, userAvg * 3);
                const userHeight = userAmp * (mid * 0.9);

                if (userHeight > 1) {
                    ctx.fillStyle = gradUser;
                    ctx.fillRect(x, mid - userHeight, barWidth, userHeight);
                } else {
                    ctx.fillStyle = '#333';
                    ctx.fillRect(x, mid - 0.5, barWidth, 1);
                }
            }


            // --- Draw Native (Bottom) ---
            if (nativeData && nativeStep > 0) {
                let nativeSum = 0;
                const nativeStart = i * nativeStep;
                for (let j = 0; j < nativeStep; j++) {
                    if (nativeStart + j < nativeData.length) nativeSum += Math.abs(nativeData[nativeStart + j]);
                }
                const nativeAvg = nativeSum / nativeStep;
                const nativeAmp = Math.min(1.0, nativeAvg * 3);
                const nativeHeight = nativeAmp * (mid * 0.9);

                if (nativeHeight > 1) {
                    ctx.fillStyle = gradNative;
                    ctx.fillRect(x, mid, barWidth, nativeHeight);
                } else {
                    ctx.fillStyle = '#333';
                    ctx.fillRect(x, mid, barWidth, 1);
                }
            } else {
                // If no native audio, show mirrored user audio as placeholder (old behavior fallback-ish)
                // But strictly speaking, if missing native, we should probably output nothing or grey.
                // Let's output nothing on bottom to be clear it's missing comparison.
                // Or actually, let's just mirror the top like before so it looks "balanced" but maybe grey?
                // No, let's keep it clean. If no native data, bottom is empty.
                // Actually, if I leave it empty, it might look broken.
                // Let's mirror it but using the user gradient for symmetry if native is missing.
                if (!nativeData && userStep > 0) {
                    // Recalculate user height for loop
                    let uSum = 0;
                    for (let j = 0; j < userStep; j++) {
                        if (userStart + j < userData.length) uSum += Math.abs(userData[userStart + j]);
                    }
                    const uAvg = uSum / userStep;
                    const uAmp = Math.min(1.0, uAvg * 3);
                    const uHeight = uAmp * (mid * 0.9);

                    ctx.fillStyle = gradUser;
                    ctx.fillRect(x, mid, barWidth, uHeight > 1 ? uHeight : 1);
                }
            }
        }
    },

    // Show/hide elements
    show(elementId) {
        const el = document.getElementById(elementId);
        if (el) el.classList.remove('hidden');
    },

    hide(elementId) {
        const el = document.getElementById(elementId);
        if (el) el.classList.add('hidden');
    }
};

window.AudioVisualizer = AudioVisualizer;
