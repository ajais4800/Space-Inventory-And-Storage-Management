"use client";
import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

export default function Reports() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const [dash, waste] = await Promise.all([
          fetch(`http://localhost:8000/api/reports/dashboard`).then(r => r.json()),
          fetch(`http://localhost:8000/api/reports/wastage`).then(r => r.json())
        ]);
        setData({ dash, waste });
      } catch (e) { console.error(e); }
    };
    fetchReports();
  }, []);

  if (!data) return <div className="p-10 text-center text-slate-400">Loading comprehensive reports...</div>;

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#0ea5e9'];

  return (
    <div className="max-w-7xl mx-auto pb-10 space-y-6">
      <div className="mb-6">
        <h2 className="text-3xl font-bold tracking-tight text-white">Analytics & Reports</h2>
        <p className="text-slate-400 mt-1">Deep insights into business performance</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6">
          <h3 className="text-lg font-bold text-white mb-6">Stock Distribution by Item</h3>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 20, right: 30, left: 30, bottom: 20 }}>
                <Pie data={data.dash.stock_by_item} dataKey="kg" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {data.dash.stock_by_item.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel p-6">
          <h3 className="text-lg font-bold text-white mb-6 flex justify-between">
            <span>30-Day Spoilage/Wastage Analysis</span>
            <span className="text-rose-400 font-bold">{data.waste.total_wasted_kg.toFixed(0)} kg lost</span>
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.waste.by_item.slice(0, 5)} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                <XAxis type="number" stroke="#94a3b8" />
                <YAxis dataKey="item" type="category" stroke="#94a3b8" width={80} fontSize={12} />
                <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Bar dataKey="kg" name="Wasted Kg" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
