"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  BarChart3, 
  Box, 
  LayoutGrid, 
  MessageSquare, 
  Package, 
  ShoppingCart,
  Bell
} from "lucide-react";
import { useEffect, useState } from "react";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutGrid },
  { name: "Inventory", href: "/inventory", icon: Box },
  { name: "Storage Map", href: "/storage", icon: Package },
  { name: "Orders", href: "/orders", icon: ShoppingCart },
  { name: "Procurement", href: "/procurement", icon: ShoppingCart },
  { name: "Reports", href: "/reports", icon: BarChart3 },
  { name: "AI Assistant", href: "/ai-assistant", icon: MessageSquare },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [alerts, setAlerts] = useState<any[]>([]);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    // Setup WebSocket for live alerts
    const ws = new WebSocket("ws://localhost:8000/ws/alerts");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === "EXPIRY_ALERT" || data.event === "STOCK_LOW" || data.event === "PLACEMENT_CONFLICT") {
        setAlerts(prev => [data.payload, ...prev].slice(0, 3));
        setShowBanner(true);
        setTimeout(() => setShowBanner(false), 8000);
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 glass-panel m-4 flex flex-col hidden md:flex border-r border-slate-700/50">
        <div className="p-6">
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
            SISM AI
          </h1>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider">Storage Management</p>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link key={item.name} href={item.href} className={`nav-link ${isActive ? 'active' : ''}`}>
                <Icon className="w-5 h-5" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
        
        <div className="p-4 mx-4 mb-4 rounded-xl bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30">
          <div className="flex items-center space-x-2 text-blue-300 font-medium mb-1">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-sm">System Live</span>
          </div>
          <p className="text-xs text-slate-400">AI engines active</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Dynamic Alert Banner */}
        <div className={`absolute top-0 inset-x-0 z-50 transition-all duration-500 transform ${showBanner ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'}`}>
          <div className="mx-4 mt-4 p-3 bg-red-500/10 border border-red-500/30 backdrop-blur-md rounded-lg flex items-center shadow-lg">
            <Bell className="w-5 h-5 text-red-400 mr-3 animate-bounce" />
            <div className="flex-1 text-sm font-medium text-red-200">
              {alerts.length > 0 ? (
                <span>⚠️ <strong className="text-white">Alert:</strong> {alerts[0]?.message || 'Critical system event detected'}</span>
              ) : ''}
            </div>
            <button onClick={() => setShowBanner(false)} className="text-red-400 hover:text-white px-2">✕</button>
          </div>
        </div>

        <main className="flex-1 overflow-auto p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
