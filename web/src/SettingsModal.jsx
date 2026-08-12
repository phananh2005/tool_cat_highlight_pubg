import React, { useState, useEffect } from 'react';

export default function SettingsModal({ isOpen, onClose, config, onSave }) {
  const [localConfig, setLocalConfig] = useState(config);

  useEffect(() => {
    setLocalConfig(config);
  }, [config, isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setLocalConfig(prev => ({ ...prev, [name]: parseFloat(value) || value }));
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden transition-all transform scale-100 opacity-100">
        <div className="p-5 border-b border-neutral-800 flex justify-between items-center bg-neutral-950/50">
          <h2 className="text-lg font-semibold text-neutral-200">Detect Settings</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-white transition-colors">✕</button>
        </div>
        <div className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">Audio Spike Threshold</label>
            <input type="number" step="0.1" name="audio_spike_threshold" value={localConfig.audio_spike_threshold} onChange={handleChange} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all" />
            <p className="text-[11px] text-neutral-500 mt-1">Độ nhạy âm thanh (0.0 - 1.0)</p>
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">Padding Trước (s)</label>
            <input type="number" step="0.5" name="highlight_pad_before" value={localConfig.highlight_pad_before} onChange={handleChange} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all" />
            <p className="text-[11px] text-neutral-500 mt-1">Thời gian cộng thêm trước highlight</p>
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">Padding Sau (s)</label>
            <input type="number" step="0.5" name="highlight_pad_after" value={localConfig.highlight_pad_after} onChange={handleChange} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all" />
            <p className="text-[11px] text-neutral-500 mt-1">Thời gian cộng thêm sau highlight</p>
          </div>
        </div>
        <div className="p-5 border-t border-neutral-800 flex justify-end gap-3 bg-neutral-950/50">
          <button onClick={onClose} className="px-5 py-2.5 text-sm font-medium text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-lg transition-colors">Hủy</button>
          <button onClick={() => onSave(localConfig)} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-blue-900/20">Lưu Cấu Hình</button>
        </div>
      </div>
    </div>
  );
}
