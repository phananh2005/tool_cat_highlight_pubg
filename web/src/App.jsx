import { useState } from 'react';
import './App.css';

function App() {
  const [videoPath, setVideoPath] = useState('');

  return (
    <div style={{ background: '#1a1a1a', color: 'white', minHeight: '100vh', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '20px' }}>PUBG Highlight Cutter - Web</h1>
      
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
        <input 
          type="text" 
          placeholder="Đường dẫn file video local (ví dụ: D:\videos\stream.mp4)" 
          value={videoPath} 
          onChange={e => setVideoPath(e.target.value)} 
          style={{ width: '600px', padding: '10px', borderRadius: '4px', border: '1px solid #444', background: '#333', color: 'white' }}
        />
      </div>

      {videoPath && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '30px' }}>
          <video 
            controls 
            src={`http://localhost:8000/video?path=${encodeURIComponent(videoPath)}`} 
            style={{ width: '800px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
          >
            Trình duyệt không hỗ trợ thẻ video.
          </video>
        </div>
      )}
    </div>
  );
}

export default App;
