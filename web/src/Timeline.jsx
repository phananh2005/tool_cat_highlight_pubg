import React, { useRef, useState, useEffect } from 'react';

export default function Timeline({ duration, matches, highlights, onSeek, onUpdateHighlight }) {
  const containerRef = useRef(null);
  const [dragging, setDragging] = useState(null); // { index, edge: 'start'|'end' }

  // Dragging logic
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!dragging || !containerRef.current || duration === 0) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
      const time = (x / rect.width) * duration;
      
      onUpdateHighlight(dragging.index, dragging.edge, time);
    };

    const handleMouseUp = () => {
      setDragging(null);
    };

    if (dragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragging, duration, onUpdateHighlight]);

  if (duration === 0) return null;

  return (
    <div className="mt-6 flex flex-col gap-2">
      <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest flex items-center gap-2">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
        </svg>
        Interactive Timeline Editor
      </h3>
      <div 
        ref={containerRef}
        className="relative w-full h-24 bg-neutral-900 border border-neutral-700/50 rounded-xl overflow-hidden cursor-crosshair shadow-inner"
        onMouseDown={(e) => {
          if (e.target === containerRef.current) {
            const rect = containerRef.current.getBoundingClientRect();
            const time = ((e.clientX - rect.left) / rect.width) * duration;
            onSeek(time);
          }
        }}
      >
        {/* Draw Matches as background gray blocks */}
        {matches.map((m, i) => {
          const left = (m.start_time / duration) * 100;
          const width = ((m.end_time - m.start_time) / duration) * 100;
          return (
            <div 
              key={`m-${i}`}
              className="absolute top-0 h-full bg-neutral-800/40 border-l border-r border-neutral-700/50 hover:bg-neutral-700/40 transition-colors"
              style={{ left: `${left}%`, width: `${width}%` }}
              title={m.label}
              onMouseDown={(e) => {
                e.stopPropagation();
                onSeek(m.start_time);
              }}
            />
          );
        })}

        {/* Draw Highlights as colored blocks */}
        {highlights.map((h, i) => {
          const left = (h.start_time / duration) * 100;
          const width = Math.max(((h.end_time - h.start_time) / duration) * 100, 0.5); // min width for visibility
          const isKill = h.highlight_type === 'kill';
          const color = isKill ? 'bg-red-500/80 border-red-500' : 'bg-amber-500/80 border-amber-500';
          
          return (
            <div 
              key={`h-${i}`}
              className={`absolute top-4 bottom-4 border-l-[3px] border-r-[3px] ${color} rounded-sm shadow-md hover:brightness-125 transition-brightness`}
              style={{ left: `${left}%`, width: `${width}%`, minWidth: '8px' }}
              title={`[${h.highlight_type}] ${h.start_time.toFixed(1)}s`}
            >
              {/* Left Handle */}
              <div 
                className="absolute left-0 top-0 bottom-0 w-3 -ml-[1.5px] cursor-ew-resize hover:bg-white/40 z-10 transition-colors"
                onMouseDown={(e) => { e.stopPropagation(); setDragging({ index: i, edge: 'start' }); }}
              />
              {/* Right Handle */}
              <div 
                className="absolute right-0 top-0 bottom-0 w-3 -mr-[1.5px] cursor-ew-resize hover:bg-white/40 z-10 transition-colors"
                onMouseDown={(e) => { e.stopPropagation(); setDragging({ index: i, edge: 'end' }); }}
              />
              {/* Center Body */}
              <div 
                className="w-full h-full cursor-pointer" 
                onMouseDown={(e) => { e.stopPropagation(); onSeek(h.start_time); }} 
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[11px] font-mono text-neutral-500">
        <span>00:00:00</span>
        <span className="italic">Kéo thả viền 2 bên của block để chỉnh sửa độ dài highlight</span>
        <span>{Math.floor(duration/3600).toString().padStart(2,'0')}:{Math.floor((duration%3600)/60).toString().padStart(2,'0')}:{(duration%60).toFixed(0).padStart(2,'0')}</span>
      </div>
    </div>
  );
}
