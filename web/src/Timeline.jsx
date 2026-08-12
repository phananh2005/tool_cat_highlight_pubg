import React, { useRef, useState, useEffect } from 'react';

export default function Timeline({ duration, currentTime, zoom, matches, highlights, onSeek, onUpdateHighlight, onToggleHighlight }) {
  const containerRef = useRef(null);
  const scrollRef = useRef(null);
  const [dragging, setDragging] = useState(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!dragging || !containerRef.current || duration === 0) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
      const time = (x / rect.width) * duration;
      onUpdateHighlight(dragging.index, dragging.edge, time);
    };
    const handleMouseUp = () => setDragging(null);

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
    <div className="flex flex-col gap-2">
      <div ref={scrollRef} className="w-full overflow-x-auto pb-4 custom-scrollbar">
        <div 
          ref={containerRef}
          className="relative h-24 bg-neutral-950 border border-neutral-700/50 rounded-xl overflow-hidden cursor-crosshair shadow-inner"
          style={{ width: `${100 * zoom}%`, minWidth: '100%' }}
          onMouseDown={(e) => {
            if (e.target === containerRef.current) {
              const rect = containerRef.current.getBoundingClientRect();
              const time = ((e.clientX - rect.left) / rect.width) * duration;
              onSeek(time);
            }
          }}
        >
          {matches.map((m, i) => {
            const left = (m.start_time / duration) * 100;
            const width = ((m.end_time - m.start_time) / duration) * 100;
            return (
              <div 
                key={`m-${i}`}
                className="absolute top-0 h-full bg-neutral-800/40 border-l border-r border-neutral-700/50 hover:bg-neutral-700/40 transition-colors"
                style={{ left: `${left}%`, width: `${width}%` }}
                title={m.label}
                onMouseDown={(e) => { e.stopPropagation(); onSeek(m.start_time); }}
              />
            );
          })}

          {highlights.map((h, i) => {
            const left = (h.start_time / duration) * 100;
            const width = Math.max(((h.end_time - h.start_time) / duration) * 100, 0.2);
            const isEnabled = h.enabled !== false;
            let color = 'bg-neutral-600/80 border-neutral-500 opacity-50';
            if (isEnabled) {
               color = h.highlight_type === 'kill' ? 'bg-red-500/80 border-red-500' : (h.highlight_type === 'manual' ? 'bg-emerald-500/80 border-emerald-500' : 'bg-amber-500/80 border-amber-500');
            }
            
            return (
              <div 
                key={`h-${i}`}
                className={`absolute top-4 bottom-4 border-l-[3px] border-r-[3px] ${color} rounded-sm shadow-md hover:brightness-125 transition-all`}
                style={{ left: `${left}%`, width: `${width}%`, minWidth: '6px' }}
                title={`[${h.highlight_type}] ${h.start_time.toFixed(1)}s (Click đúp để Bật/Tắt)`}
                onDoubleClick={(e) => { e.stopPropagation(); onToggleHighlight(i); }}
              >
                <div 
                  className="absolute left-0 top-0 bottom-0 w-3 -ml-[1.5px] cursor-ew-resize hover:bg-white/40 z-10 transition-colors"
                  onMouseDown={(e) => { e.stopPropagation(); setDragging({ index: i, edge: 'start' }); }}
                />
                <div 
                  className="absolute right-0 top-0 bottom-0 w-3 -mr-[1.5px] cursor-ew-resize hover:bg-white/40 z-10 transition-colors"
                  onMouseDown={(e) => { e.stopPropagation(); setDragging({ index: i, edge: 'end' }); }}
                />
                <div className="w-full h-full cursor-pointer" onMouseDown={(e) => { e.stopPropagation(); onSeek(h.start_time); }} />
              </div>
            );
          })}

          {/* Playhead */}
          <div 
            className="absolute top-0 bottom-0 w-[2px] bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)] z-20 pointer-events-none"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          >
            <div className="absolute -top-1 -left-1.5 w-3 h-3 rounded-full bg-blue-500" />
          </div>
        </div>
      </div>
      <div className="flex justify-between text-[11px] font-mono text-neutral-500">
        <span>00:00:00</span>
        <span className="italic">Kéo thả viền 2 bên để chỉnh độ dài. Click đúp vào Highlight để Bật/Tắt.</span>
        <span>{Math.floor(duration/3600).toString().padStart(2,'0')}:{Math.floor((duration%3600)/60).toString().padStart(2,'0')}:{(duration%60).toFixed(0).padStart(2,'0')}</span>
      </div>
    </div>
  );
}
