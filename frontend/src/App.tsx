import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Upload from "./pages/Upload";
import Processing from "./pages/Processing";
import Results from "./pages/Results";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-gray-800 px-6 py-4">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-purple-500">Deep</span>Sleuth
          </h1>
          <p className="text-sm text-gray-500">Forensic video analysis</p>
        </header>
        <main className="flex-1 flex items-center justify-center p-6">
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/processing/:taskId" element={<Processing />} />
            <Route path="/results/:taskId" element={<Results />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
