import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory, deleteHistory, type HistoryEntry } from "../api/client";
import Typewriter from "../components/Typewriter";

const LEVEL_STYLES: Record<string, { dot: string; label: string; text: string }> = {
  high: { dot: "bg-[#FF3333] shadow-[0_0_6px_#FF3333]", label: "HIGH", text: "text-[#FF3333]" },
  moderate: { dot: "bg-[#F59E0B] shadow-[0_0_6px_#F59E0B]", label: "MOD", text: "text-[#F59E0B]" },
  low: { dot: "bg-[#10B981] shadow-[0_0_6px_#10B981]", label: "LOW", text: "text-[#10B981]" },
  none: { dot: "bg-[#00FF41] shadow-[0_0_6px_#00FF41]", label: "OK", text: "text-[#00FF41]" },
};

const PER_PAGE = 20;

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TrashIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  );
}

function HistoryRow({ entry, onDelete }: { entry: HistoryEntry; onDelete: (id: string) => void }) {
  const navigate = useNavigate();
  const level = LEVEL_STYLES[entry.suspicion_level] ?? LEVEL_STYLES.none;
  const score = entry.fused_score;

  return (
    <div
      onClick={() => navigate(`/results/${entry.id}`)}
      className="cyber-card px-5 py-3 flex items-center gap-4 cursor-pointer group transition-all"
    >
      <span className="font-mono text-sm text-gray-300 flex-1 truncate min-w-0">
        {entry.filename}
      </span>

      <div className="flex items-center gap-2 shrink-0 w-20">
        <span className={`w-1.5 h-1.5 rounded-full ${level.dot}`} />
        <span className={`text-[11px] font-heading tracking-widest ${level.text}`}>
          {level.label}
        </span>
      </div>

      <span className={`font-mono text-sm font-bold w-14 text-right shrink-0 ${
        score >= 0.7 ? "text-[#FF3333]" : score >= 0.4 ? "text-[#F59E0B]" : "text-[#00FF41]"
      }`}>
        {score.toFixed(2)}
      </span>

      <span className="font-mono text-[11px] text-gray-600 w-36 text-right shrink-0 hidden sm:block">
        {formatDate(entry.created_at)}
      </span>

      <button
        onClick={(e) => { e.stopPropagation(); onDelete(entry.id); }}
        className="shrink-0 text-gray-700 hover:text-[#FF3333] transition-colors opacity-0 group-hover:opacity-100 p-1"
        title="Delete"
      >
        <TrashIcon />
      </button>
    </div>
  );
}

export default function History() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [clearing, setClearing] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const fetchPage = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await getHistory(p, PER_PAGE);
      setEntries((prev) => (p === 1 ? res.items : [...prev, ...res.items]));
      setTotal(res.total);
      setHasMore(res.items.length === PER_PAGE);
      setPage(p);
    } catch {
      // silent
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => { fetchPage(1); }, [fetchPage]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting && hasMore && !loading) fetchPage(page + 1); },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, loading, page, fetchPage]);

  async function handleDelete(id: string) {
    try {
      await deleteHistory(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch { /* silent */ }
  }

  async function handleClearAll() {
    if (clearing || entries.length === 0) return;
    if (!window.confirm("Clear all loaded history entries? This cannot be undone.")) return;
    setClearing(true);
    for (const e of [...entries]) {
      try { await deleteHistory(e.id); } catch { /* skip */ }
    }
    setEntries([]);
    setTotal(0);
    setHasMore(false);
    setClearing(false);
    fetchPage(1);
  }

  const flaggedCount = entries.filter((e) => e.suspicion_level === "high" || e.suspicion_level === "moderate").length;
  const avgScore = entries.length > 0 ? entries.reduce((s, e) => s + e.fused_score, 0) / entries.length : 0;

  if (initialLoading) {
    return (
      <div className="flex flex-col items-center gap-4">
        <div className="w-6 h-6 border-2 border-[#00FF41] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-gray-600 font-mono neon-glow-sm">LOADING HISTORY...</span>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="w-full max-w-lg mx-auto text-center">
        <div className="cyber-card p-10">
          <div className="text-3xl mb-4 text-gray-600 font-mono">{'//'} NO HISTORY</div>
          <p className="text-gray-500 font-mono text-sm mb-2">Upload your first video to begin</p>
          <p className="text-gray-600 font-mono text-sm mb-8">forensic analysis tracking.</p>
          <button
            onClick={() => navigate("/upload")}
            className="px-8 py-3 border border-[#00FF41] text-[#00FF41] font-mono text-sm tracking-widest hover:bg-[#00FF41] hover:text-black transition-all duration-200 neon-border"
          >
            &gt;&gt; UPLOAD VIDEO
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-heading tracking-wider text-[#00FF41] min-h-[2rem]"><Typewriter text="█ HISTRY LOG" /></h1>
          <p className="text-sm text-gray-600 font-mono mt-1">{total} record{total !== 1 ? "s" : ""} on file</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate("/upload")}
            className="px-4 py-1.5 border border-[#00FF41] text-[#00FF41] font-mono text-xs tracking-widest hover:bg-[#00FF41] hover:text-black transition-all duration-200 neon-border"
          >
            &gt;&gt; NEW SCAN
          </button>
          <button
            onClick={handleClearAll}
            disabled={clearing || entries.length === 0}
            className="px-4 py-1.5 border border-gray-700 text-gray-500 font-mono text-xs tracking-widest hover:border-[#FF3333] hover:text-[#FF3333] transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {clearing ? "CLEARING..." : "CLEAR ALL"}
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex gap-6 text-xs font-mono text-gray-600 px-1">
        <span>total: <span className="text-gray-300">{total}</span></span>
        <span>flagged: <span className="text-[#FF3333]">{flaggedCount} ({total > 0 ? Math.round((flaggedCount / total) * 100) : 0}%)</span></span>
        <span>avg score: <span className="text-[#00FF41]">{avgScore.toFixed(3)}</span></span>
      </div>

      {/* Column Headers */}
      <div className="flex items-center gap-4 px-5 py-1 text-[10px] font-mono text-gray-700 tracking-widest border-b border-[#1F1F1F]">
        <span className="flex-1">FILENAME</span>
        <span className="w-20">LEVEL</span>
        <span className="w-14 text-right">SCORE</span>
        <span className="w-36 text-right hidden sm:block">DATE</span>
        <span className="w-5" />
      </div>

      {/* Rows */}
      <div className="space-y-1">
        {entries.map((entry) => (
          <HistoryRow key={entry.id} entry={entry} onDelete={handleDelete} />
        ))}
      </div>

      {/* Infinite Scroll Sentinel */}
      <div ref={sentinelRef} className="flex justify-center py-4">
        {loading && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 border-2 border-[#00FF41] border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-mono text-gray-600 neon-glow-sm">LOADING...</span>
          </div>
        )}
        {!hasMore && entries.length > 0 && (
          <span className="text-xs font-mono text-gray-700">// END OF RECORDS</span>
        )}
      </div>
    </div>
  );
}
