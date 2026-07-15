import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { getMetrics } from "../api/client";

export default function Footer() {
  const [version, setVersion] = useState("v0.1.0");

  useEffect(() => {
    getMetrics().then((m) => setVersion(`v${m.version}`)).catch(() => {});
  }, []);

  return (
    <footer className="border-t border-[#1F1F1F] px-6 py-4 flex items-center justify-between">
      <span className="text-xs font-mono text-gray-600">DeepSleuth {version}</span>
      <div className="flex gap-4">
        <Link to="/about" className="text-xs font-mono text-gray-600 hover:text-[#00FF41] transition-colors">About</Link>
        <Link to="/methodology" className="text-xs font-mono text-gray-600 hover:text-[#00FF41] transition-colors">Methodology</Link>
      </div>
    </footer>
  );
}
