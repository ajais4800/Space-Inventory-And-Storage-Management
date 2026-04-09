"use client";
import { useEffect, useState } from "react";
import { Package, Layers, RefreshCw, AlertTriangle, Info } from "lucide-react";

export default function StorageMap() {
  const [layout, setLayout] = useState<any[]>([]);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);

  const fetchData = async () => {
    try {
      const [layRes, confRes] = await Promise.all([
        fetch(`http://localhost:8000/api/storage/layout`),
        fetch(`http://localhost:8000/api/storage/conflicts`)
      ]);
      setLayout(await layRes.json());
      setConflicts((await confRes.json()).conflicts || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
    const ws = new WebSocket("ws://localhost:8000/ws/storage");
    ws.onmessage = () => fetchData();
    return () => ws.close();
  }, []);

  const triggerOptimization = async () => {
    setOptimizing(true);
    try {
      const res = await fetch(`http://localhost:8000/api/storage/optimize`, { method: "POST" });
      const data = await res.json();
      alert(`Optimized! Re-sorted ${data.batches_repositioned} batches and resolved ${data.conflicts_resolved} conflicts.`);
      await fetchData();
    } catch (e) {
      console.error(e);
    }
    setOptimizing(false);
  };

  if (loading) return <div className="flex h-full items-center justify-center p-20"><RefreshCw className="w-8 h-8 text-blue-500 animate-spin" /></div>;

  return (
    <div className="max-w-7xl mx-auto pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            Storage Layout Map
          </h2>
          <p className="text-slate-400 mt-1">Live 3D-aware bin packing visualization</p>
        </div>
        
        <div className="flex gap-4">
          <div className="glass-panel px-4 py-2 flex items-center gap-3">
            <span className="text-sm text-slate-400">LIFO Conflicts:</span>
            <span className={`text-lg font-bold ${conflicts.length > 0 ? 'text-rose-400 animate-pulse' : 'text-emerald-400'}`}>
              {conflicts.length}
            </span>
          </div>
          <button 
            onClick={triggerOptimization}
            disabled={optimizing}
            className={`btn-primary flex items-center gap-2 ${optimizing ? 'opacity-50' : ''}`}
          >
            <RefreshCw className={`w-4 h-4 ${optimizing ? 'animate-spin' : ''}`} />
            {optimizing ? 'Optimizing...' : 'Run Optimize AI'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {layout.map((containerData: any) => (
          <ContainerView 
            key={containerData.container.container_id} 
            data={containerData} 
            hasConflicts={conflicts.some(c => c.container_id === containerData.container.container_id)}
          />
        ))}
      </div>
    </div>
  );
}

function ContainerView({ data, hasConflicts }: any) {
  const { container, placements } = data;
  const { rows, cols } = container.dimensions;
  
  // Create 2D grid matrix (showing the front-most depth layer as primary)
  const grid = Array(rows).fill(null).map(() => Array(cols).fill(null));
  
  placements.forEach((p: any) => {
    // We display the lowest depth item at each row/col coordinate for simplicity
    if (!grid[p.row][p.col] || p.depth < grid[p.row][p.col].depth) {
      grid[p.row][p.col] = p;
    }
  });

  return (
    <div className={`glass-panel p-5 ${hasConflicts ? 'ring-1 ring-rose-500/50' : ''}`}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
            {container.name}
            {hasConflicts && <AlertTriangle className="w-4 h-4 text-rose-400" />}
          </h3>
          <div className="flex gap-3 text-xs">
            <span className="badge badge-slate">{container.zone_type.toUpperCase()}</span>
            <span className="text-slate-400">{container.temp_c}°C</span>
            <span className="text-slate-400">{data.utilization_pct}% Used</span>
          </div>
        </div>
      </div>

      <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/50">
        <div 
          className="grid gap-2" 
          style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
        >
          {grid.map((row, rIdx) => 
            row.map((cell, cIdx) => (
              <div 
                key={`${rIdx}-${cIdx}`}
                className={`aspect-square rounded-lg border flex flex-col items-center justify-center p-2 text-center relative group ${
                  !cell ? 'border-dashed border-slate-700 bg-slate-800/30' : 
                   cell.ripeness_score >= 1.0 ? 'border-rose-500/50 bg-rose-500/20' :
                   cell.days_until_ripe <= 2 ? 'border-amber-500/50 bg-amber-500/20' :
                  'border-emerald-500/50 bg-emerald-500/20'
                }`}
              >
                {!cell ? (
                  <span className="text-xs text-slate-600">Empty</span>
                ) : (
                  <>
                    <Package className={`w-6 h-6 mb-1 ${
                      cell.ripeness_score >= 1.0 ? 'text-rose-400' :
                      cell.days_until_ripe <= 2 ? 'text-amber-400' : 'text-emerald-400'
                    }`} />
                    <span className="text-[10px] font-bold text-slate-200 truncate w-full">{cell.item_name}</span>
                    <span className="text-[9px] text-slate-400">{cell.quantity_kg.toFixed(0)}kg</span>
                    
                    {/* Tooltip */}
                    <div className={`absolute hidden group-hover:block z-20 w-48 bg-slate-800 border border-slate-600 p-3 rounded-lg shadow-xl shadow-black -top-2 ${
                      cIdx >= cols - 2 ? 'right-full mr-2' : 'left-full ml-2'
                    }`}>
                      <div className="font-bold text-white text-sm border-b border-slate-700 pb-1 mb-2">Batch {cell.batch_id}</div>
                      <div className="text-xs text-slate-300 space-y-1 text-left">
                        <div><strong className="text-slate-400">Ripe:</strong> {cell.days_until_ripe === 0 ? 'Today' : `in ${cell.days_until_ripe} days`}</div>
                        <div><strong className="text-slate-400">Expiry:</strong> {cell.expiry_date}</div>
                        <div><strong className="text-slate-400">Position 3D:</strong> R{cell.row}-C{cell.col}-D{cell.depth}</div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
      
      <div className="mt-4 flex justify-between items-center text-xs text-slate-400">
        <div>Total Positions: {container.dimensions.total_positions}</div>
        <div className="flex gap-4">
          <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-400"></div> Unripe</div>
          <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-amber-400"></div> Very Soon</div>
          <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-rose-400"></div> Ripe/Overripe</div>
        </div>
      </div>
    </div>
  );
}
