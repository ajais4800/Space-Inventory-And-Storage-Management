"use client";
import { useEffect, useState } from "react";
import { Search, Plus, Filter, ArrowUpDown } from "lucide-react";

export default function Inventory() {
  const [batches, setBatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterStr, setFilterStr] = useState("all");
  const [filterLocation, setFilterLocation] = useState("all");
  const [filterItem, setFilterItem] = useState("all");

  const fetchInventory = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/inventory`);
      const data = await res.json();
      setBatches(data.items || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchInventory();
    const ws = new WebSocket("ws://localhost:8000/ws/dashboard");
    ws.onmessage = () => fetchInventory();
    return () => ws.close();
  }, []);

  const uniqueLocations = Array.from(new Set(batches.map(b => b.container?.name))).filter(Boolean) as string[];
  const uniqueItems = Array.from(new Set(batches.map(b => b.item_name))).filter(Boolean) as string[];

  const filtered = batches.filter(b => {
    const matchesSearch = b.item_name.toLowerCase().includes(search.toLowerCase()) || 
                          (b.variety || '').toLowerCase().includes(search.toLowerCase()) ||
                          b.batch_id.toLowerCase().includes(search.toLowerCase());
    
    if (!matchesSearch) return false;
    
    if (filterLocation !== "all" && b.container?.name !== filterLocation) return false;
    if (filterItem !== "all" && b.item_name !== filterItem) return false;
    
    if (filterStr === "overripe") return b.status === 'overripe' || b.status === 'expired' || b.ripeness_score >= 1.5;
    if (filterStr === "peak") return (b.days_until_ripe === 0 || b.ripeness_score >= 1.0) && b.ripeness_score < 1.5;
    if (filterStr === "ripening") return b.days_until_ripe === 0 ? false : b.days_until_ripe <= 2 && b.ripeness_score < 1.0;
    
    return true; // "all"
  });

  return (
    <div className="max-w-7xl mx-auto pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            Inventory Management
          </h2>
          <p className="text-slate-400 mt-1">Live tracking of all perishable batches</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search batches..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input-field pl-9 w-64"
            />
          </div>
          <div className="flex bg-slate-800/50 rounded-full border border-slate-700/50 p-1">
            <select 
              className="appearance-none bg-transparent text-slate-300 rounded-l-full py-1.5 pl-3 pr-8 text-sm focus:outline-none cursor-pointer border-r border-slate-700 hover:text-white"
              value={filterLocation}
              onChange={e => setFilterLocation(e.target.value)}
            >
              <option value="all">Any Location</option>
              {uniqueLocations.map(name => <option key={name} value={name}>{name}</option>)}
            </select>
            <select 
              className="appearance-none bg-transparent text-slate-300 py-1.5 pl-3 pr-8 text-sm focus:outline-none cursor-pointer border-r border-slate-700 hover:text-white"
              value={filterItem}
              onChange={e => setFilterItem(e.target.value)}
            >
              <option value="all">Any Item</option>
              {uniqueItems.map(name => <option key={name} value={name}>{name}</option>)}
            </select>
            <select 
              className="appearance-none bg-transparent text-amber-400 font-medium rounded-r-full py-1.5 pl-3 pr-8 text-sm focus:outline-none cursor-pointer hover:text-amber-300"
              value={filterStr}
              onChange={e => setFilterStr(e.target.value)}
            >
              <option value="all" className="text-slate-200">Any Ripeness</option>
              <option value="overripe" className="text-rose-500">Overripe / Expired</option>
              <option value="peak" className="text-emerald-500">Peak Ripeness</option>
              <option value="ripening" className="text-amber-500">Ripening Soon</option>
            </select>
          </div>
          <button onClick={() => alert("The 'Add Batch' form requires full API write-access. This is locked in the demo view.")} className="btn-primary flex items-center gap-2 transition-transform active:scale-95">
            <Plus className="w-4 h-4" /> Add Batch
          </button>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-800/80 text-slate-300 border-b border-slate-700/50">
              <tr>
                <th className="px-6 py-4 font-medium flex items-center gap-1 cursor-pointer">Batch ID <ArrowUpDown className="w-3 h-3 text-slate-500" /></th>
                <th className="px-6 py-4 font-medium">Item & Variety</th>
                <th className="px-6 py-4 font-medium">Location</th>
                <th className="px-6 py-4 font-medium text-right">Qty (kg)</th>
                <th className="px-6 py-4 font-medium">Ripeness Status</th>
                <th className="px-6 py-4 font-medium">Expiry</th>
                <th className="px-6 py-4 font-medium text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {loading ? (
                <tr><td colSpan={7} className="px-6 py-8 text-center text-slate-400">Loading inventory...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-6 py-8 text-center text-slate-400">No batches found</td></tr>
              ) : (
                filtered.map((batch) => (
                  <tr key={batch.batch_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-mono text-blue-400">{batch.batch_id}</div>
                      <div className="text-xs text-slate-500 uppercase">{batch.status}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-white">{batch.item_name}</div>
                      <div className="text-xs text-slate-400">{batch.variety || 'Standard'}</div>
                    </td>
                    <td className="px-6 py-4">
                      {batch.container ? (
                        <div>
                          <span className="text-slate-300">{batch.container.name}</span>
                          <div className="text-xs text-slate-500">Pos: {batch.position?.index} (R{batch.position?.row} C{batch.position?.col} D{batch.position?.depth})</div>
                        </div>
                      ) : <span className="text-slate-500">Unassigned</span>}
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-slate-200">
                      {batch.quantity_kg?.toFixed(1)}
                    </td>
                    <td className="px-6 py-4">
                      <RipenessBadge status={batch.status} daysUntilRipe={batch.days_until_ripe} ripenessScore={batch.ripeness_score} />
                    </td>
                    <td className="px-6 py-4">
                      <ExpiryBadge days={batch.days_until_expiry} date={batch.expiry_date} />
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button 
                        onClick={() => alert(`Detailed inspection view for Batch ${batch.batch_id} is locked in the demo view. In production, this opens the full IoT tracking trace.`)}
                        className="text-blue-400 hover:text-blue-300 text-xs font-medium px-2 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 transition-colors"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function RipenessBadge({ status, daysUntilRipe, ripenessScore }: any) {
  if (status === 'overripe' || status === 'expired' || ripenessScore >= 1.5) {
    return <span className="badge badge-rose text-[11px] px-2 py-1">Overripe</span>;
  }
  if (daysUntilRipe === 0 || ripenessScore >= 1.0) {
    return <span className="badge badge-emerald text-[11px] px-2 py-1">Peak Ripeness</span>;
  }
  if (daysUntilRipe <= 2) {
    return <span className="badge badge-amber text-[11px] px-2 py-1">Ripening ({daysUntilRipe}d)</span>;
  }
  return <span className="badge badge-blue text-[11px] px-2 py-1">Unripe ({daysUntilRipe}d)</span>;
}

function ExpiryBadge({ days, date }: any) {
  if (days < 0) return <div className="text-rose-500 font-medium text-sm">Expired</div>;
  if (days <= 2) return <div className="text-amber-500 font-medium text-sm">In {days} days</div>;
  return <div className="text-slate-400 font-medium text-sm">{date}</div>;
}
