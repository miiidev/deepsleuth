import Typewriter from "../components/Typewriter";

export default function About() {
  return (
    <div className="w-full max-w-3xl mx-auto space-y-12">

      <div>
        <h1 className="text-2xl font-heading tracking-wider text-[#00FF41] min-h-[2rem] mb-4">
          <Typewriter text="ABOUT" />
        </h1>
        <p className="text-sm font-mono text-gray-500 leading-relaxed">
          DeepSleuth is an open-source forensic tool for detecting deepfake videos. It applies multiple independent analysis signals to determine whether a video has been synthetically manipulated.
        </p>
      </div>

      {/* Why it exists */}
      <section className="space-y-4">
        <h2 className="text-[11px] font-heading tracking-widest text-gray-500">WHY IT EXISTS</h2>
        <div className="cyber-card p-6 space-y-3">
          <p className="text-sm font-mono text-gray-400 leading-relaxed">
            Synthetic media is becoming indistinguishable from reality. Face-swap apps, voice clones, and generative video models produce increasingly convincing fakes. Journalists, investigators, and researchers need tools that can analyze video authenticity with transparent, explainable methods.
          </p>
          <p className="text-sm font-mono text-gray-400 leading-relaxed">
            DeepSleuth was built to fill this gap: a local, offline tool that gives you full visibility into how the analysis works — no cloud upload, no black box, no opaque AI verdict.
          </p>
        </div>
      </section>

      {/* Architecture */}
      <section className="space-y-4">
        <h2 className="text-[11px] font-heading tracking-widest text-gray-500">ARCHITECTURE</h2>
        <div className="cyber-card p-6 space-y-4">
          <p className="text-sm font-mono text-gray-400 leading-relaxed">
            DeepSleuth uses three independent forensic signals, each targeting a different category of manipulation artifact:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-[#0A0A0A] rounded-lg p-4 border border-[#1F1F1F]">
              <div className="text-xs font-heading tracking-widest text-[#00FF41] mb-2">SPATIAL</div>
              <p className="text-xs font-mono text-gray-600">XceptionNet CNN with Grad-CAM heatmaps. Detects pixel-level manipulation artifacts in face regions.</p>
              <div className="text-[10px] font-mono text-gray-700 mt-2">Weight: 55%</div>
            </div>
            <div className="bg-[#0A0A0A] rounded-lg p-4 border border-[#1F1F1F]">
              <div className="text-xs font-heading tracking-widest text-[#00FF41] mb-2">ARTIFACT</div>
              <p className="text-xs font-mono text-gray-600">Forensic artifact detection. Analyzes skin texture consistency, boundary seams, and noise patterns across face regions.</p>
              <div className="text-[10px] font-mono text-gray-700 mt-2">Weight: 15%</div>
            </div>
            <div className="bg-[#0A0A0A] rounded-lg p-4 border border-[#1F1F1F]">
              <div className="text-xs font-heading tracking-widest text-[#00FF41] mb-2">TEMPORAL</div>
              <p className="text-xs font-mono text-gray-600">Blink rate and head pose analysis. Deepfakes often have unnatural blink rates and erratic motion.</p>
              <div className="text-[10px] font-mono text-gray-700 mt-2">Weight: 30%</div>
            </div>
          </div>
          <p className="text-sm font-mono text-gray-400 leading-relaxed">
            Scores from all three signals are fused into a weighted composite score. No single signal is definitive — the combined result reflects agreement across independent detection methods.
          </p>
        </div>
      </section>

      {/* Open Methodology */}
      <section className="space-y-4">
        <h2 className="text-[11px] font-heading tracking-widest text-gray-500">OPEN METHODOLOGY</h2>
        <div className="cyber-card p-6">
          <p className="text-sm font-mono text-gray-400 leading-relaxed">
            Every signal, weight, and threshold in DeepSleuth is disclosed. The results page shows individual signal scores, per-region breakdowns, Grad-CAM heatmaps, and per-frame anomaly graphs. You can inspect exactly what the tool detected and why it reached its conclusion. See the <a href="/methodology" className="text-[#00FF41] hover:underline">Methodology</a> page for full technical details.
          </p>
        </div>
      </section>

      {/* Limitations */}
      <section className="space-y-4">
        <h2 className="text-[11px] font-heading tracking-widest text-[#F59E0B]">LIMITATIONS</h2>
        <div className="disclaimer-banner">
          <div className="space-y-3">
            <p className="text-sm font-mono text-gray-400 leading-relaxed">
              DeepSleuth is a research tool, not a substitute for human judgment. Key limitations:
            </p>
            <ul className="text-xs font-mono text-gray-500 space-y-2 list-none">
              <li className="flex gap-2"><span className="text-[#F59E0B]">-</span> No automated system achieves 100% accuracy. False positives and false negatives occur.</li>
              <li className="flex gap-2"><span className="text-[#F59E0B]">-</span> The model was trained on FaceForensics++ (c40 quality). Performance may vary on other manipulation methods.</li>
              <li className="flex gap-2"><span className="text-[#F59E0B]">-</span> Only one face per frame is analyzed. Multi-face scenarios use the primary detected face.</li>
              <li className="flex gap-2"><span className="text-[#F59E0B]">-</span> Videos longer than 3 minutes are not supported.</li>
              <li className="flex gap-2"><span className="text-[#F59E0B]">-</span> Results should be interpreted alongside other evidence and domain expertise.</li>
            </ul>
          </div>
        </div>
      </section>

    </div>
  );
}
