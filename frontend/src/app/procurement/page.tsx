"use client";
import { useEffect, useState } from "react";
import { ShoppingCart, CheckCircle, XCircle, RefreshCw, Layers } from "lucide-react";

export default function Procurement() {
  const [recs, setRecs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchRecs = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/procurement/recommendations`);
      setRecs(await res.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRecs();
  }, []);

  const generateRecs = async () => {
    setGenerating(true);
    try {
      await fetch(`http://localhost:8000/api/procurement/generate`, { method: "POST" });
      await fetchRecs();
    } catch (e) {
      console.error(e);
    }
    setGenerating(false);
  };

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    try {
      await fetch(`http://localhost:8000/api/procurement/${id}/${action}`, { method: "PUT" });
      await fetchRecs();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            AI Procurement Recommendations
          </h2>
          <p className="text-slate-400 mt-1">Smart replenishment driven by demand vs supply gaps</p>
        </div>
        
        <button 
          onClick={generateRecs}
          disabled={generating}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
          {generating ? 'Analyzing Demand...' : 'Run Prediction Engine'}
        </button>
      </div>

      <div className="space-y-4">
        {loading ? (
          <div className="flex justify-center p-10"><RefreshCw className="w-6 h-6 animate-spin text-blue-500" /></div>
        ) : recs.length === 0 ? (
          <div className="glass-panel p-10 text-center text-slate-400">No pending recommendations. Run the engine to check stock.</div>
        ) : (
          recs.map(rec => (
            <div key={rec.rec_id} className={`glass-card p-5 border-l-4 ${
              rec.status !== 'pending' ? 'border-l-slate-600 opacity-60' :
              rec.priority === 'urgent' ? 'border-l-rose-500' : 'border-l-blue-500'
            }`}>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-bold text-white">{rec.item_name}</h3>
                    <span className="text-xs font-mono text-slate-500">{rec.sku}</span>
                    {rec.status === 'pending' && <span className={`badge ${rec.priority === 'urgent' ? 'badge-rose' : 'badge-blue'}`}>{rec.priority.toUpperCase()}</span>}
                    {rec.status !== 'pending' && <span className="badge badge-slate">{rec.status.toUpperCase()}</span>}
                  </div>
                  
                  <p className="text-slate-300 text-sm leading-relaxed mb-3">
                    <span className="font-semibold text-slate-400">AI Reason:</span> {rec.reason}
                  </p>
                  
                  <div className="flex flex-wrap gap-4 text-xs">
                    <div className="bg-slate-900/50 px-3 py-1.5 rounded-lg border border-slate-700">
                      <span className="text-slate-500 mr-1">Recommended Order:</span> 
                      <span className="font-bold text-emerald-400 text-sm block">{rec.recommended_qty_kg.toFixed(0)} kg</span>
                    </div>
                    <div className="bg-slate-900/50 px-3 py-1.5 rounded-lg border border-slate-700">
                      <span className="text-slate-500 mr-1">Order Deadline:</span> 
                      <span className="font-medium text-amber-400 text-sm block">{rec.order_by_date}</span>
                    </div>
                    <div className="bg-slate-900/50 px-3 py-1.5 rounded-lg border border-slate-700">
                      <span className="text-slate-500 mr-1">Expected Delivery:</span> 
                      <span className="font-medium text-slate-300 text-sm block">{rec.expected_delivery_date}</span>
                    </div>
                  </div>
                </div>

                {rec.status === 'pending' && (
                  <div className="flex md:flex-col gap-2 shrink-0 md:min-w-[140px]">
                    <button 
                      onClick={() => handleAction(rec.rec_id, 'approve')}
                      className="flex-1 flex items-center justify-center gap-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 px-4 py-2.5 rounded-lg transition-colors border border-emerald-500/30 font-medium text-sm"
                    >
                      <CheckCircle className="w-4 h-4" /> Approve
                    </button>
                    <button 
                      onClick={() => handleAction(rec.rec_id, 'reject')}
                      className="flex-1 flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 text-slate-300 px-4 py-2.5 rounded-lg transition-colors border border-slate-600 font-medium text-sm"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
