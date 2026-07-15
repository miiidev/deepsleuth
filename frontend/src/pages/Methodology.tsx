import { useEffect, useState } from "react";
import Typewriter from "../components/Typewriter";
import { getMetrics, type BenchmarkMetrics } from "../api/client";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-[11px] font-heading tracking-widest text-gray-500">{title}</h2>
      <div className="cyber-card p-6 space-y-3">{children}</div>
    </section>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-[#1F1F1F] last:border-0">
      <span className="text-xs font-mono text-gray-500">{label}</span>
      <span className="text-xs font-mono text-gray-300">{value}</span>
    </div>
  );
}

export default function Methodology() {
  const [metrics, setMetrics] = useState<BenchmarkMetrics | null>(null);

  useEffect(() => {
    getMetrics().then(setMetrics).catch(() => {});
  }, []);

  return (
    <div className="w-full max-w-3xl mx-auto space-y-12">

      <div>
        <h1 className="text-2xl font-heading tracking-wider text-[#00FF41] min-h-[2rem] mb-4">
          <Typewriter text="METHODOLOGY" />
        </h1>
        <p className="text-sm font-mono text-gray-500 leading-relaxed">
          A detailed technical breakdown of how DeepSleuth analyzes videos for deepfake manipulation.
        </p>
      </div>

      {/* Pipeline Overview */}
      <Section title="PIPELINE OVERVIEW">
        <div className="flex flex-wrap gap-2 items-center text-xs font-mono">
          <span className="px-2 py-1 bg-[#0A0A0A] border border-[#1F1F1F] rounded text-gray-400">Frame Extraction</span>
          <span className="text-gray-700">&rarr;</span>
          <span className="px-2 py-1 bg-[#0A0A0A] border border-[#1F1F1F] rounded text-gray-400">Face Detection</span>
          <span className="text-gray-700">&rarr;</span>
          <span className="px-2 py-1 bg-[#0A0A0A] border border-[#1F1F1F] rounded text-[#00FF41]">3 Signals</span>
          <span className="text-gray-700">&rarr;</span>
          <span className="px-2 py-1 bg-[#0A0A0A] border border-[#1F1F1F] rounded text-gray-400">Score Fusion</span>
          <span className="text-gray-700">&rarr;</span>
          <span className="px-2 py-1 bg-[#0A0A0A] border border-[#1F1F1F] rounded text-gray-400">Report</span>
        </div>
        <p className="text-xs font-mono text-gray-500 leading-relaxed">
          Videos are sampled every N-th frame (configurable). MediaPipe FaceLandmarker detects faces and extracts 478 facial landmarks. Three independent forensic signals analyze the detected faces, and their scores are fused into a final verdict.
        </p>
      </Section>

      {/* Spatial Analysis */}
      <Section title="SPATIAL ANALYSIS — XCEPTIONNET CNN">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-heading tracking-widest text-[#00FF41] bg-[#00FF4110] px-2 py-0.5 rounded">WEIGHT: 40%</span>
          </div>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">WHAT IT DOES</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            A binary classifier (real vs. fake) built on the Xception architecture. Each detected face crop is fed through the CNN, which outputs a manipulation probability score.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">HOW IT WORKS</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            The model uses depthwise separable convolutions to learn spatial features at multiple scales. Grad-CAM (Gradient-weighted Class Activation Mapping) produces heatmaps showing which pixels most influenced the classification decision. These heatmaps are overlaid on the video for visual inspection.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">WHAT IT CATCHES</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            Pixel-level artifacts from face-swap, facereenactment, and lip-sync manipulation methods. Inconsistencies in texture, lighting, and color that are invisible to the human eye.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">PER-REGION SCORING</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            The face is divided into 6 regions (eyes, nose, mouth, forehead, cheeks, jawline). Each region receives an independent anomaly score based on the Grad-CAM heatmap intensity, allowing localized identification of manipulated areas.
          </p>
        </div>
      </Section>

      {/* Frequency Analysis */}
      <Section title="FREQUENCY ANALYSIS — MULTI-FEATURE SPECTRAL">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-heading tracking-widest text-[#00FF41] bg-[#00FF4110] px-2 py-0.5 rounded">WEIGHT: 25%</span>
          </div>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">WHAT IT DOES</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            Analyzes three independent frequency-domain features of face images to detect spectral anomalies characteristic of synthetic generation.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">HOW IT WORKS</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            <strong>DCT Energy Ratio:</strong> A 2D Discrete Cosine Transform is applied to the grayscale face (224x224). Energy (sum of squared coefficients) is split into frequency bands. The ratio of high-frequency energy to total energy is computed — natural faces have a smooth spectral rolloff, while deepfakes exhibit unnatural high-frequency content.
          </p>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            <strong>Spectral Flatness (Wiener Entropy):</strong> Measures how flat or spiky the frequency spectrum is. Natural images have structured, non-flat spectra. GAN-generated faces often produce flatter or more periodic spectral profiles.
          </p>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            <strong>Laplacian Variance:</strong> Applies a Laplacian edge detector and measures the variance of the response. This captures sharpness characteristics — deepfakes may show unnatural blur or edge patterns compared to real camera-captured faces.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">WHAT IT CATCHES</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            GAN-generated faces introduce periodic spectral artifacts and unnatural frequency distributions. Face-swap boundaries create frequency discontinuities. The multi-feature approach reduces false positives from compression or noise by cross-referencing independent spectral indicators.
          </p>
        </div>
      </Section>

      {/* Temporal Analysis */}
      <Section title="TEMPORAL ANALYSIS — BLINK + FLICKERING + STABILITY">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-heading tracking-widest text-[#00FF41] bg-[#00FF4110] px-2 py-0.5 rounded">WEIGHT: 35%</span>
          </div>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">WHAT IT DOES</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            Analyzes three temporal signals across video frames — blink patterns, frame-to-frame spectral consistency, and facial landmark stability — to detect unnatural motion dynamics.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">HOW IT WORKS</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            <strong>Blink Detection:</strong> Eye Aspect Ratio (EAR) is computed from 6 facial landmarks around each eye across consecutive frames. A blink is detected when EAR drops below a threshold and recovers. Normal blink rate is approximately 15-20 blinks per minute.
          </p>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            <strong>Temporal Flickering:</strong> For each frame, the high-frequency DCT coefficients of the face region are extracted. The variance of these coefficients across consecutive frames measures spectral consistency. Deepfakes often exhibit frame-to-frame flickering due to independent per-frame generation.
          </p>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            <strong>Landmark Stability:</strong> Facial landmark positions are centered (mean-subtracted) to remove head movement, then their variance across frames is measured. Excessive jitter in centered landmarks indicates inconsistent facial geometry typical of synthetic faces.
          </p>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">WHAT IT CATCHES</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            Early deepfake methods produced videos with no blinking (0 blinks/min). Modern methods have improved but still often show rates significantly below the human average of ~17 blinks/min. Temporal flickering and landmark jitter are direct artifacts of frame-by-frame face synthesis rather than natural continuous capture.
          </p>
        </div>
      </Section>

      {/* Score Fusion */}
      <Section title="SCORE FUSION">
        <div className="space-y-3">
          <h3 className="text-xs font-heading tracking-widest text-gray-400">HOW SIGNALS ARE COMBINED</h3>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            The three signal scores (each 0.0 to 1.0) are combined using a weighted sum:
          </p>
          <div className="bg-[#0A0A0A] rounded-lg p-4 border border-[#1F1F1F] font-mono text-xs text-gray-400">
            fused_score = (spatial × 0.40) + (frequency × 0.25) + (temporal × 0.35)
          </div>
          <h3 className="text-xs font-heading tracking-widest text-gray-400">SUSPICION LEVELS</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="bg-[#0A0A0A] rounded p-3 border border-[#1F1F1F] text-center">
              <div className="text-[10px] font-heading tracking-widest text-[#00FF41] mb-1">NONE</div>
              <div className="text-[10px] font-mono text-gray-600">&lt; 0.3</div>
            </div>
            <div className="bg-[#0A0A0A] rounded p-3 border border-[#1F1F1F] text-center">
              <div className="text-[10px] font-heading tracking-widest text-[#10B981] mb-1">LOW</div>
              <div className="text-[10px] font-mono text-gray-600">0.3 — 0.5</div>
            </div>
            <div className="bg-[#0A0A0A] rounded p-3 border border-[#1F1F1F] text-center">
              <div className="text-[10px] font-heading tracking-widest text-[#F59E0B] mb-1">MODERATE</div>
              <div className="text-[10px] font-mono text-gray-600">0.5 — 0.7</div>
            </div>
            <div className="bg-[#0A0A0A] rounded p-3 border border-[#1F1F1F] text-center">
              <div className="text-[10px] font-heading tracking-widest text-[#FF3333] mb-1">HIGH</div>
              <div className="text-[10px] font-mono text-gray-600">&ge; 0.7</div>
            </div>
          </div>
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            No single signal is definitive. A high spatial score alone may indicate compression artifacts rather than manipulation. The fusion approach requires agreement across multiple independent detection methods to reduce false positives.
          </p>
        </div>
      </Section>

      {/* Benchmark Results */}
      <Section title="BENCHMARK RESULTS">
        <div className="space-y-4">
          <p className="text-xs font-mono text-gray-500 leading-relaxed">
            Performance evaluated on the FaceForensics++ dataset (c40 quality, 80/10/10 stratified split).
          </p>
          <div className="space-y-0">
            <MetricRow label="Dataset" value={metrics?.benchmark.dataset ?? "FaceForensics++"} />
            <MetricRow label="Quality" value={metrics?.benchmark.quality ?? "c40"} />
            <MetricRow label="Test Samples" value={metrics?.benchmark.test_samples.toLocaleString() ?? "3,809"} />
            <MetricRow label="Model" value={metrics?.benchmark.model ?? "XceptionNet"} />
            <MetricRow label="Training Epochs" value={String(metrics?.benchmark.epochs ?? 40)} />
            <MetricRow label="Split Ratio" value={metrics?.benchmark.split_ratio ?? "80/10/10"} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="benchmark-badge">
              <div className="text-2xl font-heading text-[#00FF41] neon-glow-sm">
                {metrics ? (metrics.benchmark.accuracy * 100).toFixed(1) : "92.6"}%
              </div>
              <div className="text-[10px] font-heading tracking-widest text-gray-500 mt-1">ACCURACY</div>
            </div>
            <div className="benchmark-badge">
              <div className="text-2xl font-heading text-[#00FF41] neon-glow-sm">
                {metrics ? (metrics.benchmark.f1 * 100).toFixed(1) : "93.2"}%
              </div>
              <div className="text-[10px] font-heading tracking-widest text-gray-500 mt-1">F1 SCORE</div>
            </div>
            <div className="benchmark-badge">
              <div className="text-2xl font-heading text-[#00FF41] neon-glow-sm">
                {metrics ? (metrics.benchmark.precision * 100).toFixed(1) : "92.8"}%
              </div>
              <div className="text-[10px] font-heading tracking-widest text-gray-500 mt-1">PRECISION</div>
            </div>
            <div className="benchmark-badge">
              <div className="text-2xl font-heading text-[#00FF41] neon-glow-sm">
                {metrics ? (metrics.benchmark.recall * 100).toFixed(1) : "93.6"}%
              </div>
              <div className="text-[10px] font-heading tracking-widest text-gray-500 mt-1">RECALL</div>
            </div>
          </div>
        </div>
      </Section>

    </div>
  );
}
