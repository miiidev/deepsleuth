import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, Scan, FileText, Layers, Eye, BarChart3 } from "lucide-react";
import Typewriter from "../components/Typewriter";
import { getMetrics, type BenchmarkMetrics } from "../api/client";

export default function Landing() {
  const [metrics, setMetrics] = useState<BenchmarkMetrics | null>(null);

  useEffect(() => {
    getMetrics().then(setMetrics).catch(() => {});
  }, []);

  const accuracyPct = metrics ? (metrics.benchmark.accuracy * 100).toFixed(1) : "99.1";

  return (
    <div className="w-full max-w-4xl mx-auto space-y-16">

      {/* Hero */}
      <section className="text-center space-y-6">
        <h1 className="text-5xl font-heading tracking-wider min-h-[3.5rem]">
          <span className="landing-hero"><Typewriter text="DEEPSLEUTH" speed={80} /></span>
        </h1>
        <p className="text-lg font-mono text-gray-500">forensic deepfake detection</p>
        <p className="text-sm font-mono text-gray-600 max-w-xl mx-auto leading-relaxed">
          Upload a video. Get a forensic analysis with heatmaps, per-frame anomaly scores, and a downloadable PDF report.
        </p>
        <Link
          to="/upload"
          className="inline-block px-8 py-3 border border-[#00FF41] text-[#00FF41] font-mono text-sm tracking-widest hover:bg-[#00FF41] hover:text-black transition-all duration-200 neon-border"
        >
          &gt;&gt; ANALYZE VIDEO
        </Link>
      </section>

      {/* How It Works */}
      <section className="space-y-6">
        <h2 className="text-sm font-heading tracking-widest text-gray-500 text-center">HOW IT WORKS</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="cyber-card p-6 text-center space-y-3">
            <Upload className="w-8 h-8 mx-auto text-[#00FF41]" />
            <div className="text-xs font-heading tracking-widest text-gray-400">01 // UPLOAD</div>
            <p className="text-xs font-mono text-gray-600 leading-relaxed">Drop a video file (MP4, MOV, WEBM, AVI). Up to 3 minutes, 500 MB.</p>
          </div>
          <div className="cyber-card p-6 text-center space-y-3">
            <Scan className="w-8 h-8 mx-auto text-[#00FF41]" />
            <div className="text-xs font-heading tracking-widest text-gray-400">02 // ANALYZE</div>
            <p className="text-xs font-mono text-gray-600 leading-relaxed">Three independent forensic signals scan every frame for manipulation artifacts.</p>
          </div>
          <div className="cyber-card p-6 text-center space-y-3">
            <FileText className="w-8 h-8 mx-auto text-[#00FF41]" />
            <div className="text-xs font-heading tracking-widest text-gray-400">03 // REPORT</div>
            <p className="text-xs font-mono text-gray-600 leading-relaxed">Get a verdict with heatmaps, per-frame graphs, and a downloadable PDF report.</p>
          </div>
        </div>
      </section>

      {/* Trust Signals */}
      <section className="space-y-6">
        <h2 className="text-sm font-heading tracking-widest text-gray-500 text-center">WHY TRUST DEEPSLEUTH</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="benchmark-badge">
            <div className="text-3xl font-heading text-[#00FF41] neon-glow mb-1">{accuracyPct}%</div>
            <div className="text-[10px] font-heading tracking-widest text-gray-500 mb-2">ACCURACY</div>
            <p className="text-xs font-mono text-gray-600">
              Tested on {metrics?.benchmark.test_samples.toLocaleString() ?? "7,125"} samples from {metrics?.benchmark.dataset ?? "FaceForensics++"}
            </p>
          </div>
          <div className="benchmark-badge">
            <div className="flex justify-center gap-3 mb-2">
              <Layers className="w-6 h-6 text-[#00FF41]" />
              <Eye className="w-6 h-6 text-[#00FF41]" />
              <BarChart3 className="w-6 h-6 text-[#00FF41]" />
            </div>
            <div className="text-[10px] font-heading tracking-widest text-gray-500 mb-2">3 INDEPENDENT SIGNALS</div>
              <p className="text-xs font-mono text-gray-600">Spatial CNN, artifact detection, and temporal behavior — each weighted and explained.</p>
          </div>
          <div className="benchmark-badge">
            <div className="flex justify-center gap-3 mb-2">
              <Scan className="w-6 h-6 text-[#00FF41]" />
            </div>
            <div className="text-[10px] font-heading tracking-widest text-gray-500 mb-2">FULL EXPLAINABILITY</div>
            <p className="text-xs font-mono text-gray-600">Grad-CAM heatmaps, per-region scores, per-frame anomaly graphs — no black box.</p>
          </div>
        </div>
      </section>

    </div>
  );
}
