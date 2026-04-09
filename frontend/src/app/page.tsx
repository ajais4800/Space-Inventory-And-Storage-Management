"use client";
import { useEffect, useState } from "react";
import { 
  TrendingUp, AlertTriangle, PackageSearch, PackageOpen, LayoutTemplate, Box, RefreshCw
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [simDays, setSimDays] = useState(0);

  const fetchDashboard = async (days: number = 0) => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/reports/dashboard?sim_days=${days}`);
      const dashData = await res.json();
      
      const demandRes = await fetch(`http://localhost:8000/api/reports/demand?days=7&sim_days=${days}`);
      const demandData = await demandRes.json();
      
      setData({ ...dashData, demandData });
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDashboard(simDays);
    // Real-time update listener via WebSocket
    const ws = new WebSocket("ws://localhost:8000/ws/dashboard");
    ws.onmessage = () => fetchDashboard(simDays);
    return () => ws.close();
  }, [simDays]);

  if (loading && !data) return (
    <div className="flex h-full items-center justify-center">
      <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
    </div>
  );
  if (!data) return <div>Failed to load data</div>;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Operations Center
            <span className="badge badge-emerald py-1 px-3">Live</span>
          </h2>
          <p className="text-slate-400 mt-1 mb-2">Smart Inventory & Storage Management</p>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs font-semibold px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700 flex items-center gap-1.5">
              <Box className="w-3.5 h-3.5 text-blue-400" />
              Total Batches: {data.total_batches_all?.toLocaleString()}
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700 flex items-center gap-1.5">
              <PackageOpen className="w-3.5 h-3.5 text-emerald-400" />
              Total Orders: {data.total_delivery_orders_all?.toLocaleString()}
            </span>
          </div>
        </div>
        
        {/* Time-Travel Simulation Slider */}
        <div className="glass-panel p-3 px-5 flex items-center gap-4">
          <div className="text-sm font-medium text-slate-300">
            Preview Future State: <span className="text-white font-bold">{simDays === 0 ? "Today" : `Day +${simDays}`}</span>
          </div>
          <input 
            type="range" min="0" max="14" step="1" 
            value={simDays} 
            onChange={(e) => setSimDays(parseInt(e.target.value))}
            className="w-32 md:w-48 accent-blue-500"
          />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard 
          title="Total Usable Stock" 
          value={`${data.total_stock_kg?.toLocaleString()} kg`} 
          icon={Box} 
          trend="+2.4% from yesterday"
          color="blue" 
        />
        <KPICard 
          title="Expiring Soon (48h)" 
          value={`${data.expiring_soon_batches} batches`} 
          subValue={`(${data.expiring_soon_kg} kg)`}
          icon={AlertTriangle} 
          trend="Requires action"
          color="rose"
        />
        <KPICard 
          title="Pending Orders (7d)" 
          value={data.pending_orders_7d} 
          icon={PackageOpen} 
          trend="Delivery schedule optimized"
          color="amber"
        />
        <KPICard 
          title="Storage Utilization" 
          value={`${data.storage_utilization_pct}%`} 
          subValue={`${data.current_load_kg?.toLocaleString()} / ${data.total_capacity_kg?.toLocaleString()} kg`}
          icon={LayoutTemplate} 
          trend={`${data.total_containers} Active Containers`}
          color="emerald"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Demand vs Supply Chart */}
        <div className="lg:col-span-2 glass-panel p-6">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            7-Day Demand vs Ripe Supply Forecast
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.demandData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="day_label" stroke="#94a3b8" fontSize={12} tickMargin={10} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                  itemStyle={{ color: '#f8fafc' }}
                />
                <Line type="monotone" name="Total Demand (kg)" dataKey="total_demand_kg" stroke="#3b82f6" strokeWidth={3} dot={{r:4}} activeDot={{r:6}} />
                <Line type="monotone" name="Ripe Supply (kg)" dataKey="ripe_supply_kg" stroke="#10b981" strokeWidth={3} dot={{r:4}} activeDot={{r:6}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Action Panel */}
        <div className="glass-panel p-6 flex flex-col">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <PackageSearch className="w-5 h-5 text-purple-400" />
            Procurement Tasks
          </h3>
          <div className="flex-1 flex flex-col justify-center space-y-4">
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
              <div className="text-sm text-slate-400 mb-1">Pending AI Buy Orders</div>
              <div className="text-3xl font-bold text-white">{data.pending_procurement_recs}</div>
            </div>
            <div className="bg-rose-500/10 rounded-xl p-4 border border-rose-500/20">
              <div className="text-sm text-rose-300 mb-1">Urgent Restock Needed</div>
              <div className="text-3xl font-bold text-rose-400">{data.urgent_procurement_recs}</div>
            </div>
            <button 
              className="btn-primary w-full mt-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 border-none"
              onClick={() => window.location.href = '/procurement'}
            >
              Review Recommendations
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICard({ title, value, subValue, icon: Icon, trend, color }: any) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-400 bg-blue-400/10",
    emerald: "text-emerald-400 bg-emerald-400/10",
    rose: "text-rose-400 bg-rose-400/10",
    amber: "text-amber-400 bg-amber-400/10",
  };
  
  return (
    <div className="glass-card p-5 flex flex-col">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-slate-400 font-medium text-sm">{title}</h3>
        <div className={`p-2 rounded-lg ${colorMap[color] || colorMap.blue}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div>
        <div className="text-2xl font-bold text-white mb-1 flex items-baseline gap-2">
          {value}
          {subValue && <span className="text-sm font-medium text-slate-400">{subValue}</span>}
        </div>
        <p className="text-xs text-slate-500">{trend}</p>
      </div>
    </div>
  );
}
