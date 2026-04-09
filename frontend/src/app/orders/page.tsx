"use client";
import { useEffect, useState } from "react";
import { ShoppingBag, Truck, CheckCircle2, Clock, MapPin } from "lucide-react";

export default function Orders() {
  const [orders, setOrders] = useState<any[]>([]);

  const fetchOrders = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/orders/upcoming`);
      setOrders(await res.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchOrders();
    const ws = new WebSocket("ws://localhost:8000/ws/dashboard");
    ws.onmessage = () => fetchOrders();
    return () => ws.close();
  }, []);

  return (
    <div className="max-w-7xl mx-auto pb-10">
      <div className="mb-6">
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          Delivery Orders
        </h2>
        <p className="text-slate-400 mt-1">Upcoming fulfilling commitments within 7 days</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {orders.map(order => (
          <div key={order.order_id} className="glass-panel p-5">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShoppingBag className="w-5 h-5 text-blue-400" />
                  {order.client_name}
                </h3>
                <div className="flex items-center gap-3 mt-1 text-sm text-slate-400">
                  <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {order.city}</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {order.delivery_date} ({order.days_until_delivery}d)</span>
                  <span className={`badge ${order.priority === 'urgent' ? 'badge-rose' : 'badge-slate'}`}>{order.priority.toUpperCase()}</span>
                </div>
              </div>
              <span className={`badge ${order.status === 'confirmed' ? 'badge-emerald' : 'badge-amber'}`}>
                {order.status.toUpperCase()}
              </span>
            </div>
            
            <div className="space-y-2 mt-4">
              {order.items.map((item: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-sm bg-slate-900/50 p-2 rounded border border-slate-700/50">
                  <span className="text-slate-200">{item.item_name} <span className="text-slate-500">[{item.sku}]</span></span>
                  <div className="flex gap-4 font-medium">
                    <span className="text-slate-400">Ordered: {item.quantity_kg.toFixed(0)}kg</span>
                    <span className={item.gap_kg > 0 ? 'text-amber-400' : 'text-emerald-400'}>
                      {item.gap_kg > 0 ? `Gap: ${item.gap_kg.toFixed(0)}kg` : 'Fulfilled'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        {orders.length === 0 && <div className="col-span-2 text-center p-10 text-slate-500">No upcoming orders found.</div>}
      </div>
    </div>
  );
}
