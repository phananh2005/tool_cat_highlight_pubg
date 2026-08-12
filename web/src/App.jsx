import { useState, useRef, useEffect } from 'react';
import Timeline from './Timeline';
import Toast from './Toast';
import SettingsModal from './SettingsModal';
import ExportProgressModal from './ExportProgressModal';
import './App.css';

function App() {
  const [videoPath, setVideoPath] = useState('');
  const [matches, setMatches] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [zoom, setZoom] = useState(1);
  
  const [toast, setToast] = useState({ message: '', type: 'info' });
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState({
    audio_spike_threshold: 0.8,
    highlight_pad_before: 2.0,
    highlight_pad_after: 2.0
  });

  const [exportStatus, setExportStatus] = useState({ progress: 0, message: '', done: false, error: '' });
  const [showExportModal, setShowExportModal] = useState(false);

  const videoRef = useRef(null);

  const showMsg = (message, type = 'info') => setToast({ message, type });

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code === 'Space') {
        e.preventDefault();
        if (videoRef.current) {
          if (videoRef.current.paused) videoRef.current.play();
          else videoRef.current.pause();
        }
      } else if (e.code === 'ArrowLeft') {
        if (videoRef.current) videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - 5);
      } else if (e.code === 'ArrowRight') {
        if (videoRef.current && duration) videoRef.current.currentTime = Math.min(duration, videoRef.current.currentTime + 5);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [duration]);

  // Project Save/Load
  const saveProject = () => {
    const data = { videoPath, matches, highlights, config };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pubg_project.json';
    a.click();
    URL.revokeObjectURL(url);
    showMsg('Đã lưu project.json', 'success');
  };

  const loadProject = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result);
        if(data.videoPath) setVideoPath(data.videoPath);
        if(data.matches) setMatches(data.matches);
        if(data.highlights) setHighlights(data.highlights);
        if(data.config) setConfig(data.config);
        showMsg('Đã tải project thành công', 'success');
      } catch (err) {
        showMsg('Lỗi đọc file project (định dạng không đúng)', 'error');
      }
    };
    reader.readAsText(file);
    e.target.value = null;
  };

  const updateHighlight = (index, edge, time) => {
    setHighlights(prev => {
      const next = [...prev];
      const h = { ...next[index] };
      if (edge === 'start') {
        h.start_time = Math.min(time, h.end_time - 0.5);
      } else {
        h.end_time = Math.max(time, h.start_time + 0.5);
      }
      next[index] = h;
      return next;
    });
  };

  const toggleHighlight = (index) => {
    setHighlights(prev => {
      const next = [...prev];
      next[index] = { ...next[index], enabled: next[index].enabled === false ? true : false };
      return next;
    });
  };

  const addManualHighlight = () => {
    if (duration === 0) return showMsg('Vui lòng load video trước', 'error');
    const start = currentTime;
    const end = Math.min(start + 10, duration);
    setHighlights(prev => [...prev, {
      start_time: start,
      end_time: end,
      highlight_type: 'manual',
      confidence: 1.0,
      enabled: true,
      label: 'Manual Clip'
    }].sort((a, b) => a.start_time - b.start_time));
    showMsg(`Đã thêm clip tại ${start.toFixed(1)}s`, 'success');
  };

  const detectMatches = async () => {
    if (!videoPath) return showMsg('Nhập đường dẫn video', 'error');
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/detect/matches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath })
      });
      const data = await res.json();
      if (data.error) showMsg('Lỗi: ' + data.error, 'error');
      else {
        setMatches(data);
        showMsg(`Tìm thấy ${data.length} matches`, 'success');
      }
    } catch (e) {
      showMsg('Lỗi kết nối: ' + e.message, 'error');
    }
    setLoading(false);
  };

  const detectHighlights = async () => {
    if (!videoPath || matches.length === 0) return showMsg('Cần video và detect matches trước', 'error');
    setLoading(true);
    showMsg('Đang phân tích highlights (có thể mất vài phút)...', 'info');
    try {
      const res = await fetch('http://localhost:8000/api/detect/highlights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, matches: matches, player_name: '', config: config })
      });
      const data = await res.json();
      if (data.error) showMsg('Lỗi: ' + data.error, 'error');
      else {
        setHighlights(data);
        showMsg(`Đã detect ${data.length} highlights`, 'success');
      }
    } catch (e) {
      showMsg('Lỗi kết nối: ' + e.message, 'error');
    }
    setLoading(false);
  };

  const exportHighlights = async () => {
    const active = highlights.filter(h => h.enabled !== false);
    if (active.length === 0) return showMsg('Chưa có highlights nào được bật', 'error');
    
    setExportStatus({ progress: 0, message: 'Đang gửi yêu cầu...', done: false, error: '' });
    setShowExportModal(true);

    try {
      const res = await fetch('http://localhost:8000/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, highlights: active, output_dir: 'exports' })
      });
      const data = await res.json();
      if (data.error) {
         setExportStatus({ progress: 0, message: 'Lỗi: ' + data.error, done: true, error: data.error });
         return;
      }
      
      const poll = setInterval(async () => {
        try {
          const sRes = await fetch('http://localhost:8000/api/export/status');
          const statusData = await sRes.json();
          setExportStatus(statusData);
          if (statusData.done) {
            clearInterval(poll);
            if (statusData.error) showMsg('Lỗi xuất video!', 'error');
            else showMsg(`Export thành công ${statusData.files?.length || 0} clips!`, 'success');
          }
        } catch (e) {
          // ignore network temp error
        }
      }, 500);

    } catch (e) {
      setExportStatus({ progress: 0, message: 'Lỗi kết nối: ' + e.message, done: true, error: e.message });
    }
  };

  const seekTo = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans p-6 selection:bg-blue-500/30 pb-20">
      <header className="max-w-[1400px] mx-auto flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 bg-clip-text text-transparent">
          PUBG Highlight Cutter
        </h1>
        <div className="flex gap-4 items-center">
          <input type="file" id="loadProj" accept=".json" className="hidden" onChange={loadProject} />
          <button onClick={() => document.getElementById('loadProj').click()} className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 rounded-lg text-sm text-neutral-300 border border-neutral-700 transition" title="Mở file project.json">
            📂 Mở Project
          </button>
          <button onClick={saveProject} className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 rounded-lg text-sm text-neutral-300 border border-neutral-700 transition" title="Lưu state hiện tại">
            💾 Lưu Project
          </button>
          <button onClick={() => setShowSettings(true)} className="px-5 py-2 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-sm font-medium transition-colors border border-neutral-700 shadow-sm flex items-center gap-2" title="Cấu hình">
            <span>⚙️</span> Settings
          </button>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Video & Controls */}
        <div className="lg:col-span-3 flex flex-col gap-6">
          <div className="bg-neutral-900 p-4 rounded-xl border border-neutral-800/60 shadow-xl flex gap-3 items-center flex-wrap">
            <input 
              type="text" 
              placeholder="Đường dẫn file video local (C:\videos\stream.mp4)..." 
              value={videoPath} 
              onChange={e => setVideoPath(e.target.value)} 
              className="flex-1 min-w-[200px] bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500/50 transition-colors shadow-inner"
            />
            <button onClick={detectMatches} disabled={loading} className="px-6 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-emerald-400 border border-emerald-900/50 rounded-lg text-sm font-medium transition-all disabled:opacity-50">
              {loading ? 'Processing...' : '1. Detect Matches'}
            </button>
            <button onClick={detectHighlights} disabled={loading || matches.length===0} className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 shadow-lg shadow-blue-900/20">
              2. Detect Highlights
            </button>
          </div>

          <div className="bg-neutral-900 rounded-xl overflow-hidden border border-neutral-800/60 shadow-2xl aspect-video flex items-center justify-center relative">
            {videoPath ? (
              <video 
                ref={videoRef}
                controls 
                onLoadedMetadata={(e) => setDuration(e.target.duration)}
                onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
                src={`http://localhost:8000/video?path=${encodeURIComponent(videoPath)}`} 
                className="w-full h-full object-contain bg-black"
              />
            ) : (
              <div className="flex flex-col items-center gap-3 text-neutral-600">
                <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                <p className="text-sm">Chưa tải video</p>
              </div>
            )}
          </div>
          
          {videoPath && duration > 0 && (
            <div className="bg-neutral-900 rounded-xl border border-neutral-800/60 shadow-xl p-4">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" /></svg>
                    Timeline Editor
                  </h3>
                  <button onClick={addManualHighlight} className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded text-xs border border-neutral-700 transition">
                    + Thêm Clip Tại Đây
                  </button>
                  <span className="text-[10px] text-neutral-600 hidden sm:inline ml-2">(Phím tắt: Space để Play, Mũi tên để tua)</span>
                </div>
                <div className="flex items-center gap-3 bg-neutral-950 px-3 py-1.5 rounded-lg border border-neutral-800">
                  <span className="text-xs text-neutral-500 font-medium">Zoom</span>
                  <input type="range" min="1" max="10" step="0.5" value={zoom} onChange={(e) => setZoom(parseFloat(e.target.value))} className="w-24 accent-blue-500" />
                  <span className="text-xs text-neutral-400 font-mono w-6">{zoom}x</span>
                </div>
              </div>
              <Timeline 
                duration={duration} 
                currentTime={currentTime}
                zoom={zoom}
                matches={matches} 
                highlights={highlights} 
                onSeek={seekTo} 
                onUpdateHighlight={updateHighlight}
                onToggleHighlight={toggleHighlight}
              />
            </div>
          )}
        </div>

        {/* Right Column: Sidebar */}
        <div className="bg-neutral-900 rounded-xl border border-neutral-800/60 shadow-xl flex flex-col h-[calc(100vh-9rem)]">
          <div className="p-5 border-b border-neutral-800/60 flex justify-between items-center bg-neutral-900/50">
            <h2 className="text-lg font-semibold text-neutral-200">Danh sách</h2>
            <button onClick={exportHighlights} disabled={showExportModal || highlights.length === 0} className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-amber-950 rounded-lg text-sm font-bold transition-all disabled:opacity-50 shadow-lg shadow-amber-900/20">
              3. Export Clips
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-8 custom-scrollbar">
            {/* Highlights Section */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-4 flex items-center gap-2">
                Highlights <span className="bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded-full">{highlights.length}</span>
              </h3>
              <div className="space-y-2.5">
                {highlights.map((h, i) => {
                  const isEnabled = h.enabled !== false;
                  return (
                    <div key={i} className={`group p-3 bg-neutral-950/50 border ${isEnabled ? 'border-neutral-800 hover:border-neutral-600' : 'border-neutral-900 opacity-40'} rounded-lg transition-all flex justify-between items-center`}>
                      <div className="flex-1 cursor-pointer" onClick={() => seekTo(h.start_time)}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`w-2 h-2 rounded-full shadow-sm ${!isEnabled ? 'bg-neutral-600' : (h.highlight_type === 'kill' ? 'bg-red-500 shadow-red-500/50' : (h.highlight_type === 'manual' ? 'bg-emerald-500 shadow-emerald-500/50' : 'bg-amber-500 shadow-amber-500/50'))}`}></span>
                          <strong className={`text-sm ${isEnabled ? 'text-neutral-300' : 'text-neutral-500 line-through'}`}>{h.highlight_type.toUpperCase()}</strong>
                        </div>
                        <span className="text-[11px] font-mono text-neutral-500">{h.start_time.toFixed(1)}s - {h.end_time.toFixed(1)}s</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <button onClick={() => toggleHighlight(i)} className="text-neutral-500 hover:text-white transition-colors" title={isEnabled ? "Tắt clip này" : "Bật lại clip"}>
                          {isEnabled ? '👁️' : '❌'}
                        </button>
                      </div>
                    </div>
                  )
                })}
                {highlights.length === 0 && <div className="text-sm text-neutral-600 p-4 text-center border border-dashed border-neutral-800 rounded-lg">Chưa có dữ liệu</div>}
              </div>
            </div>
          </div>
        </div>
      </main>

      <Toast toast={toast} onClose={() => setToast({ message: '' })} />
      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} config={config} onSave={(cfg) => { setConfig(cfg); setShowSettings(false); showMsg('Đã lưu cấu hình', 'success'); }} />
      <ExportProgressModal isOpen={showExportModal} status={exportStatus} onClose={() => setShowExportModal(false)} />
    </div>
  );
}

export default App;
