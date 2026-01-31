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
            if (score >= 90) label.textContent = 'Excellent!';
            else if (score >= 70) label.textContent = 'Good job!';
            else if (score >= 50) label.textContent = 'Keep practicing';
            else if (score >= 30) label.textContent = 'Needs work';
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
            if (s.score >= 90) {
                chip.className += 'bg-green-500/20 text-green-400';
            } else if (s.score >= 70) {
                chip.className += 'bg-teal-500/20 text-teal-400';
            } else if (s.score >= 50) {
                chip.className += 'bg-yellow-500/20 text-yellow-400';
            } else {
                chip.className += 'bg-red-500/20 text-red-400';
            }

            chip.textContent = `${s.syllable} (${s.score}%)`;
            container.appendChild(chip);
        });
    },

    // Simple waveform using canvas (lightweight alternative to Wavesurfer)
    drawWaveform(canvasId, audioBuffer) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !audioBuffer) return;

        const ctx = canvas.getContext('2d');
        const data = audioBuffer.getChannelData(0);
        const width = canvas.width;
        const height = canvas.height;
        const step = Math.ceil(data.length / width);

        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(0, 0, width, height);

        ctx.strokeStyle = '#006AA7'; // Swedish blue
        ctx.lineWidth = 1;
        ctx.beginPath();

        const mid = height / 2;
        for (let i = 0; i < width; i++) {
            let min = 1.0, max = -1.0;
            for (let j = 0; j < step; j++) {
                const idx = (i * step) + j;
                if (idx < data.length) {
                    if (data[idx] < min) min = data[idx];
                    if (data[idx] > max) max = data[idx];
                }
            }
            ctx.moveTo(i, mid + min * mid);
            ctx.lineTo(i, mid + max * mid);
        }
        ctx.stroke();
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
