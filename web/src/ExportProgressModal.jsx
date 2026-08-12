import React from 'react';

export default function ExportProgressModal({ isOpen, status, onClose }) {
  if (!isOpen) return null;
  
  const percentage = Math.round(status.progress * 100);
  const isError = !!status.error;
  
  return (
    <div className="fixed inset-0 bg-black/80 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="p-5 border-b border-neutral-800 flex justify-between items-center bg-neutral-950/50">
          <h2 className="text-lg font-semibold text-neutral-200">
            {isError ? 'Lỗi xuất video' : (status.done ? 'Hoàn tất!' : 'Đang xử lý...')}
          </h2>
          {status.done && (
            <button onClick={onClose} className="text-neutral-500 hover:text-white transition-colors">✕</button>
          )}
        </div>
        <div className="p-8 space-y-6">
          <div className="w-full bg-neutral-950 rounded-full h-4 border border-neutral-800 overflow-hidden relative">
            <div 
              className={`${isError ? 'bg-red-500' : (status.done ? 'bg-emerald-500' : 'bg-blue-500')} h-full transition-all duration-300 ease-out`}
              style={{ width: `${percentage}%` }}
            >
            </div>
          </div>
          <div className="text-center">
            <div className={`text-3xl font-bold mb-2 ${isError ? 'text-red-500' : 'text-white'}`}>{percentage}%</div>
            <p className="text-sm text-neutral-400 break-words">{isError ? status.error : status.message || "Đang khởi tạo..."}</p>
          </div>
        </div>
        {status.done && (
          <div className="p-5 border-t border-neutral-800 flex justify-center bg-neutral-950/50">
            <button onClick={onClose} className="px-6 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-sm font-medium transition-all shadow-lg">Đóng</button>
          </div>
        )}
      </div>
    </div>
  );
}
