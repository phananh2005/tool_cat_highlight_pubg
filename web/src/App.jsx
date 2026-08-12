import { useState } from 'react';
import Timeline from './Timeline';
import './App.css';

function App() {
  const [videoPath, setVideoPath] = useState('');
  const [matches, setMatches] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [duration, setDuration] = useState(0);

  const updateHighlight = (index, edge, time) => {
    setHighlights(prev => {
      const next = [...prev];
      const h = { ...next[index] };
      if (edge === 'start') {
        h.start_time = Math.min(time, h.end_time - 0.5); // min 0.5s duration
      } else {
        h.end_time = Math.max(time, h.start_time + 0.5);
      }
      next[index] = h;
      return next;
    });
  };

  const detectMatches = async () => {
    if (!videoPath) return alert('Nhập đường dẫn video');
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/detect/matches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath })
      });
      const data = await res.json();
      if (data.error) alert('Lỗi: ' + data.error);
      else setMatches(data);
    } catch (e) {
      alert('Lỗi kết nối: ' + e.message);
    }
    setLoading(false);
  };

  const detectHighlights = async () => {
    if (!videoPath || matches.length === 0) return alert('Cần video và detect matches trước');
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/detect/highlights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, matches: matches, player_name: '' })
      });
      const data = await res.json();
      if (data.error) alert('Lỗi: ' + data.error);
      else setHighlights(data);
    } catch (e) {
      alert('Lỗi kết nối: ' + e.message);
    }
    setLoading(false);
  };

  const exportHighlights = async () => {
    if (highlights.length === 0) return alert('Chưa có highlights để export');
    setExporting(true);
    try {
      const res = await fetch('http://localhost:8000/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, highlights: highlights, output_dir: 'exports' })
      });
      const data = await res.json();
      if (data.error) alert('Lỗi: ' + data.error);
      else alert(`Export thành công ${data.files.length} clips vào thư mục exports/`);
    } catch (e) {
      alert('Lỗi kết nối: ' + e.message);
    }
    setExporting(false);
  };

  const seekTo = (seconds) => {
    const video = document.getElementById('videoPlayer');
    if (video) {
      video.currentTime = seconds;
      video.play();
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans p-6 selection:bg-blue-500/30">
      <header className="max-w-[1400px] mx-auto flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 bg-clip-text text-transparent">
          PUBG Highlight Cutter
        </h1>
        <div className="flex gap-4">
          <button className="px-5 py-2 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-sm font-medium transition-colors border border-neutral-700 shadow-sm">
            ⚙️ Settings
          </button>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Video & Controls */}
        <div className="lg:col-span-3 flex flex-col gap-6">
          <div className="bg-neutral-900 p-4 rounded-xl border border-neutral-800/60 shadow-xl flex gap-3 items-center">
            <input 
              type="text" 
              placeholder="Đường dẫn file video local (C:\videos\stream.mp4)..." 
              value={videoPath} 
              onChange={e => setVideoPath(e.target.value)} 
              className="flex-1 bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500/50 transition-colors shadow-inner"
            />
            <button 
              onClick={detectMatches} 
              disabled={loading} 
              className="px-6 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-emerald-400 border border-emerald-900/50 rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : '1. Detect Matches'}
            </button>
            <button 
              onClick={detectHighlights} 
              disabled={loading || matches.length===0} 
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-900/20"
            >
              2. Detect Highlights
            </button>
          </div>

          <div className="bg-neutral-900 rounded-xl overflow-hidden border border-neutral-800/60 shadow-2xl aspect-video flex items-center justify-center relative">
            {videoPath ? (
              <video 
                id="videoPlayer"
                controls 
                onLoadedMetadata={(e) => setDuration(e.target.duration)}
                src={`http://localhost:8000/video?path=${encodeURIComponent(videoPath)}`} 
                className="w-full h-full object-contain bg-black"
              />
            ) : (
              <div className="flex flex-col items-center gap-3 text-neutral-600">
                <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p className="text-sm">Chưa tải video</p>
              </div>
            )}
          </div>
          
          {videoPath && duration > 0 && (
            <Timeline 
              duration={duration} 
              matches={matches} 
              highlights={highlights} 
              onSeek={seekTo} 
              onUpdateHighlight={updateHighlight} 
            />
          )}
        </div>

        {/* Right Column: Sidebar */}
        <div className="bg-neutral-900 rounded-xl border border-neutral-800/60 shadow-xl flex flex-col h-[calc(100vh-9rem)]">
          <div className="p-5 border-b border-neutral-800/60 flex justify-between items-center bg-neutral-900/50">
            <h2 className="text-lg font-semibold text-neutral-200">Danh sách</h2>
            <button 
              onClick={exportHighlights}
              disabled={exporting || highlights.length === 0}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-amber-950 rounded-lg text-sm font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-amber-900/20"
            >
              {exporting ? 'Đang xuất...' : '3. Export Clips'}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-8 custom-scrollbar">
            {/* Highlights Section */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-4 flex items-center gap-2">
                Highlights <span className="bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded-full">{highlights.length}</span>
              </h3>
              <div className="space-y-2.5">
                {highlights.map((h, i) => (
                  <div key={i} onClick={() => seekTo(h.start_time)} className="group cursor-pointer p-3 bg-neutral-950/50 border border-neutral-800 hover:border-neutral-600 hover:bg-neutral-800/50 rounded-lg transition-all flex justify-between items-center">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2 h-2 rounded-full shadow-sm ${h.highlight_type === 'kill' ? 'bg-red-500 shadow-red-500/50' : 'bg-amber-500 shadow-amber-500/50'}`}></span>
                        <strong className="text-sm text-neutral-300">{h.highlight_type.toUpperCase()}</strong>
                      </div>
                      <span className="text-[11px] font-mono text-neutral-500">{h.start_time.toFixed(1)}s - {h.end_time.toFixed(1)}s</span>
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-600 group-hover:text-blue-400 transition-colors">▶ Seek</span>
                  </div>
                ))}
                {highlights.length === 0 && <div className="text-sm text-neutral-600 p-4 text-center border border-dashed border-neutral-800 rounded-lg">Chưa có dữ liệu</div>}
              </div>
            </div>

            {/* Matches Section */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-4 flex items-center gap-2">
                Matches <span className="bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded-full">{matches.length}</span>
              </h3>
              <div className="space-y-2.5">
                {matches.map((m, i) => (
                  <div key={i} onClick={() => seekTo(m.start_time)} className="cursor-pointer p-3 bg-neutral-950/50 border border-neutral-800 hover:border-neutral-600 hover:bg-neutral-800/50 rounded-lg transition-all">
                    <strong className="text-sm text-neutral-300 block mb-1">{m.label}</strong>
                    <span className="text-[11px] font-mono text-neutral-500">{m.start_time.toFixed(1)}s - {m.end_time.toFixed(1)}s</span>
                  </div>
                ))}
                {matches.length === 0 && <div className="text-sm text-neutral-600 p-4 text-center border border-dashed border-neutral-800 rounded-lg">Chưa có dữ liệu</div>}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
