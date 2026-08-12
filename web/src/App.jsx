import { useState } from 'react';
import './App.css';

function App() {
  const [videoPath, setVideoPath] = useState('');
  const [matches, setMatches] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(false);

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

  const seekTo = (seconds) => {
    const video = document.getElementById('videoPlayer');
    if (video) {
      video.currentTime = seconds;
      video.play();
    }
  };

  return (
    <div style={{ background: '#1a1a1a', color: 'white', minHeight: '100vh', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '20px' }}>PUBG Highlight Cutter - Web</h1>
      
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px', gap: '10px' }}>
        <input 
          type="text" 
          placeholder="Đường dẫn file video local (ví dụ: D:\videos\stream.mp4)" 
          value={videoPath} 
          onChange={e => setVideoPath(e.target.value)} 
          style={{ width: '600px', padding: '10px', borderRadius: '4px', border: '1px solid #444', background: '#333', color: 'white' }}
        />
        <button onClick={detectMatches} disabled={loading} style={{ padding: '10px 20px', background: '#4CAF50', border: 'none', borderRadius: '4px', color: 'white', cursor: loading ? 'wait' : 'pointer' }}>
          {loading ? 'Đang xử lý...' : 'Detect Matches'}
        </button>
        <button onClick={detectHighlights} disabled={loading || matches.length === 0} style={{ padding: '10px 20px', background: '#2196F3', border: 'none', borderRadius: '4px', color: 'white', cursor: (loading || matches.length === 0) ? 'not-allowed' : 'pointer' }}>
          Detect Highlights
        </button>
      </div>

      {videoPath && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '20px', marginBottom: '20px' }}>
          <video 
            id="videoPlayer"
            controls 
            src={`http://localhost:8000/video?path=${encodeURIComponent(videoPath)}`} 
            style={{ width: '800px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
          />
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', paddingBottom: '50px' }}>
        <div style={{ width: '350px' }}>
          <h3 style={{ borderBottom: '1px solid #444', paddingBottom: '10px' }}>Matches ({matches.length})</h3>
          {matches.map((m, i) => (
            <div key={i} onClick={() => seekTo(m.start_time)} style={{ cursor: 'pointer', padding: '10px', background: '#2c2c2c', marginBottom: '8px', borderRadius: '4px', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background = '#444'} onMouseOut={e => e.currentTarget.style.background = '#2c2c2c'}>
              <strong>{m.label}</strong> <br/>
              <span style={{ fontSize: '0.9em', color: '#aaa' }}>{m.start_time.toFixed(1)}s - {m.end_time.toFixed(1)}s</span>
            </div>
          ))}
        </div>
        <div style={{ width: '350px' }}>
          <h3 style={{ borderBottom: '1px solid #444', paddingBottom: '10px' }}>Highlights ({highlights.length})</h3>
          {highlights.map((h, i) => (
            <div key={i} onClick={() => seekTo(h.start_time)} style={{ cursor: 'pointer', padding: '10px', background: '#2c2c2c', marginBottom: '8px', borderRadius: '4px', borderLeft: h.highlight_type === 'kill' ? '4px solid #f44336' : '4px solid #ff9800', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background = '#444'} onMouseOut={e => e.currentTarget.style.background = '#2c2c2c'}>
              <strong>[{h.highlight_type.toUpperCase()}]</strong> <br/>
              <span style={{ fontSize: '0.9em', color: '#aaa' }}>{h.start_time.toFixed(1)}s - {h.end_time.toFixed(1)}s (Conf: {h.confidence.toFixed(2)})</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
