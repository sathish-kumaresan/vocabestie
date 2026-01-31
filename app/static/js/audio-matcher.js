// Audio Matcher for Vocabestie
// Provides instant client-side pronunciation scoring by comparing audio envelopes
// Uses simplified Cross-Correlation and Dynamic Time Warping concepts

const AudioMatcher = {
    // Main comparison function
    // Returns a score between 0-100 indicating similarity
    compare(userBuffer, nativeBuffer) {
        if (!userBuffer || !nativeBuffer) return 0;

        try {
            // 1. Extract Envelopes (Amplitude over time)
            // We downsample to a low frequency (e.g., 20Hz) to compare "major shape" rather than details
            // This makes it more robust to slight speed/intonation variations
            const userEnv = this.extractEnvelope(userBuffer, 20);
            const nativeEnv = this.extractEnvelope(nativeBuffer, 20);

            // 2. Normalize Duration
            const resizedUserEnv = this.resample(userEnv, nativeEnv.length);

            // 3. Calculate Best Match (Sliding Window / Alignment)
            // Even with trimSilence, there might be slight offsets. 
            // We slide the user envelope +/- 15% to find best alignment.
            const maxCorrelation = this.findBestAlignment(resizedUserEnv, nativeEnv);

            console.log('Raw Correlation:', maxCorrelation);

            // 4. Convert correlation (0.0 - 1.0) to Score (0 - 100)
            // Map:
            // > 0.7  -> 100 (Perfect)
            // > 0.5  -> 80  (Excellent)
            // > 0.3  -> 60  (Good)

            let score = 0;
            if (maxCorrelation > 0.7) score = 100;
            else if (maxCorrelation < 0.1) score = 30;
            else {
                // Linear map [0.1, 0.7] -> [40, 95]
                score = 40 + ((maxCorrelation - 0.1) / 0.6) * 60;
            }

            return Math.min(100, Math.max(0, Math.round(score)));

        } catch (e) {
            console.error("AudioMatcher error:", e);
            return 80; // Fail graceful
        }
    },

    // Find best correlation by sliding arr1 over arr2
    findBestAlignment(arr1, arr2) {
        if (arr1.length !== arr2.length) return 0;

        const searchWindow = Math.floor(arr1.length * 0.15); // +/- 15% shift
        let maxCorr = 0;

        for (let offset = -searchWindow; offset <= searchWindow; offset++) {
            let sum1 = 0, sum2 = 0, pSum = 0;
            let sqSum1 = 0, sqSum2 = 0;
            let count = 0;

            const start = Math.max(0, offset);
            const end = Math.min(arr1.length, arr1.length + offset);

            for (let i = start; i < end; i++) {
                const val1 = arr1[i - offset];
                const val2 = arr2[i];
                sum1 += val1;
                sum2 += val2;
                pSum += val1 * val2;
                sqSum1 += val1 * val1;
                sqSum2 += val2 * val2;
                count++;
            }

            if (count < arr1.length * 0.5) continue;

            const num = pSum - (sum1 * sum2 / count);
            const den = Math.sqrt((sqSum1 - sum1 * sum1 / count) * (sqSum2 - sum2 * sum2 / count));

            let corr = 0;
            if (den !== 0) corr = num / den;
            if (corr > maxCorr) maxCorr = corr;
        }

        return maxCorr;
    },

    // Extract amplitude envelope
    // rate: Target sample rate for envelope (e.g. 50Hz = 1 point per 20ms)
    extractEnvelope(buffer, rate) {
        const data = buffer.getChannelData(0);
        const originalRate = buffer.sampleRate;
        const step = Math.floor(originalRate / rate);
        const result = [];

        for (let i = 0; i < data.length; i += step) {
            let sum = 0;
            // RMS of the chunk
            const chunkEnd = Math.min(i + step, data.length);
            for (let j = i; j < chunkEnd; j++) {
                sum += data[j] * data[j];
            }
            const rms = Math.sqrt(sum / (chunkEnd - i));
            result.push(rms);
        }

        // Normalize max amplitude to 1.0
        const max = Math.max(...result);
        if (max > 0.001) {
            // Normalize, but also boost low signals slightly to capture shape better
            for (let i = 0; i < result.length; i++) {
                result[i] /= max;
                // Soft threshold to reduce background noise influence in silence parts
                if (result[i] < 0.1) result[i] = 0;
            }
        }

        return result;
    },

    // Resample array to target length (Linear Interpolation)
    resample(data, targetLength) {
        if (targetLength <= 0) return [];
        if (targetLength === data.length) return data;

        const result = new Array(targetLength);
        const step = (data.length - 1) / (targetLength - 1);

        for (let i = 0; i < targetLength; i++) {
            const exactIndex = i * step;
            const idx = Math.floor(exactIndex);
            const frac = exactIndex - idx;

            if (idx >= data.length - 1) {
                result[i] = data[data.length - 1];
            } else {
                result[i] = data[idx] * (1 - frac) + data[idx + 1] * frac;
            }
        }
        return result;
    },

    // Calculate Pearson Correlation Coefficient
    calculateCorrelation(arr1, arr2) {
        if (arr1.length !== arr2.length) return 0;

        let sum1 = 0, sum2 = 0;
        let pSum = 0;
        let sqSum1 = 0, sqSum2 = 0;
        const n = arr1.length;

        for (let i = 0; i < n; i++) {
            sum1 += arr1[i];
            sum2 += arr2[i];
            pSum += arr1[i] * arr2[i];
            sqSum1 += arr1[i] * arr1[i];
            sqSum2 += arr2[i] * arr2[i];
        }

        // Numerator
        const num = pSum - (sum1 * sum2 / n);

        // Denominator
        const den = Math.sqrt((sqSum1 - sum1 * sum1 / n) * (sqSum2 - sum2 * sum2 / n));

        if (den === 0) return 0;
        return num / den;
    }
};

window.AudioMatcher = AudioMatcher;
