import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-7 bg-slate-200 rounded-xl w-1/3"></div>
      <div className="space-y-2.5">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-16 bg-white border border-slate-200/80 rounded-2xl w-full shadow-subtle"></div>
        ))}
      </div>
    </div>
  );
};
