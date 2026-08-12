import React, { useEffect } from 'react';

export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (toast.message) {
      const timer = setTimeout(() => onClose(), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast, onClose]);

  if (!toast.message) return null;

  const bgColors = {
    error: 'bg-red-500/90 border-red-500',
    success: 'bg-emerald-500/90 border-emerald-500',
    info: 'bg-blue-500/90 border-blue-500'
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 transition-all duration-300 transform translate-y-0 opacity-100">
      <div className={`${bgColors[toast.type || 'info']} text-white px-5 py-3 rounded-lg shadow-2xl border flex items-center gap-3`}>
        <span className="text-sm font-medium">{toast.message}</span>
        <button onClick={onClose} className="hover:text-black/50 ml-2 transition-colors">✕</button>
      </div>
    </div>
  );
}
