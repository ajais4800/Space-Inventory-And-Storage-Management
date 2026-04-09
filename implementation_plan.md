# SISM — Smart Inventory & Storage Management
### AI-Powered Perishable Goods Platform · **Fully Dynamic & Event-Driven**

A full-stack, AI-augmented web application for managing storage, perishable inventory, and smart delivery logistics — with live adaptation when conditions change.

---

## ⚡ Dynamic Execution Model

The system is **never static**. Every change triggers a cascade of intelligent reactions:

```
  📦 New Batch Added
        │
        ▼
  [Event Bus] ─────────────────────────────────────────────┐
        │                                                   │
        ▼                                                   ▼
  🧠 AI Re-evaluates            📊 Dashboard KPIs      🔴 Alerts
  Storage Layout                 Update Live             Fire if
  (LIFO re-sort)                (WebSocket push)        threshold hit
        │
        ▼
  ⚠️  Conflict Detected?         ✅ All Good?
  (wrong order, expiry risk)     Confirm placement
        │                              │
        ▼                              ▼
  🤖 Agentic AI proposes        📦 Batch placed,
  corrective action             orders auto-adjusted
```

**Dynamic Triggers:**

| Trigger | System Response |
|---|---|
| New batch logged | Re-run storage optimizer, push updated layout to UI via WebSocket |
| Delivery date changes | Recalculate which batches fulfill order, flag gaps |
| Item falls below reorder point | Auto-generate procurement recommendation with quantity + timing |
| Batch approaching expiry | Alert + suggest early use, demote in storage order |
| Storage container full | Warn, suggest overflow container, block conflicting placement |
| Temperature deviation logged | Ripeness timeline recalculated for affected batches |
| Client demand changes | Demand forecast re-runs, order quantities adjusted |
| AI chat input | RAG searches live inventory state — always current |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Next.js Frontend (Real-Time UI)               │
│  Dashboard · Inventory · Storage · Orders ·             │
│  Procurement · AI Chat · Reports                        │
└──────────────────┬──────────────────────────────────────┘
                   │  REST API + WebSocket (live push)
┌──────────────────▼──────────────────────────────────────┐
│               FastAPI Backend + Event Bus                │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Inventory  │  │  AI Engine   │  │  Event Engine    │  │
│  │ Storage    │  │ (RAG+Agentic)│  │ (Triggers)       │  │
│  │ Orders     │  │  Optimizer   │  │  WebSocket Hub   │  │
│  │ Reports    │  │  Ripeness    │  │  Audit Logger    │  │
│  │ Procurement│  │  Forecaster  │  └──────────────────┘  │
│  └─────┬──────┘  └──────┬───────┘                        │
└────────┼────────────────┼───────────────────────────────┘
         │                │
┌────────▼──────┐  ┌──────▼──────────┐  ┌────────────────┐
│   SQLite DB   │  │   ChromaDB      │  │  Audit / Event │
│  (Live state) │  │  (Embeddings)   │  │  Log (SQLite)  │
└───────────────┘  └─────────────────┘  └────────────────┘
                          │
                   ┌──────▼──────────┐
                   │  Gemini LLM API │
                   └─────────────────┘
```

**Tech Stack:**

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript |
| Styling | TailwindCSS + Framer Motion |
| Charts | Recharts |
| Backend | FastAPI (Python) + SQLAlchemy |
| Primary DB | SQLite |
| Vector DB | ChromaDB |
| AI/LLM | Google Gemini 1.5 Flash |
| Embeddings | `sentence-transformers` (local) |
| Real-Time | WebSocket (FastAPI native) |
| Simulation | Time-travel slider (future state preview) |
| Data Volume | 500+ synthetic records, 15+ perishable types |

---

## User Review Required

> [!IMPORTANT]
> Requires `GEMINI_API_KEY` environment variable for AI Chat & Recommendations. App remains functional without it — AI features fall back to a rules-based engine.

> [!NOTE]
> Fully self-contained with SQLite — no external DB setup. All data auto-seeded on first run.

---

## Proposed Changes

### Backend (FastAPI)

#### [NEW] `backend/main.py`
FastAPI app with CORS, all routers, WebSocket hub, and startup data seeding + ChromaDB indexing.

---

#### [NEW] `backend/database.py`
SQLAlchemy models for SQLite:

| Model | Key Fields |
|---|---|
| `PerishableItem` | SKU, category, weight_kg, reorder_point, lead_days, ripeness_curve |
| `InventoryBatch` | batch_id, item_id, qty_kg, received_date, expected_ripeness_date, expiry_date, storage_zone, **position_index**, **row, col, depth** (3D) |
| `StorageContainer` | container_id, name, capacity_kg, zone_type, current_load_kg |
| `StoragePlacement` | placement_id, batch_id, container_id, position, assigned_at, conflict_flag |
| `DeliveryOrder` | order_id, client_name, delivery_date, city, status |
| `OrderItem` | order_id, item_id, qty_kg |
| `ProcurementRecommendation` | rec_id, item_id, recommended_qty, order_by_date, reason, ai_generated |
| `AIInsight` | insight_id, type, message, severity, resolved |
| `AuditLog` | log_id, entity_type, entity_id, action, old_value, new_value, timestamp |

---

#### [NEW] `backend/routers/inventory.py`
- `GET /api/inventory` — all items with current stock levels
- `POST /api/inventory/batch` — add new batch → triggers event bus
- `GET /api/inventory/alerts` — below reorder point or expiring soon
- `GET /api/inventory/expiry` — batches expiring in next N days

#### [NEW] `backend/routers/storage.py`
- `GET /api/storage/containers` — all containers with load %
- `GET /api/storage/layout` — full 3D layout (row/col/depth) of all batches
- `POST /api/storage/optimize` — trigger LIFO re-sort → pushes update via WebSocket
- `GET /api/storage/placement/{batch_id}` — recommended 3D position for a batch
- `GET /api/storage/conflicts` — batches placed in wrong order (early-expiry behind late-expiry)

#### [NEW] `backend/routers/orders.py`
- `GET /api/orders` — all delivery orders
- `POST /api/orders` — create order → triggers demand recalculation
- `GET /api/orders/fulfillment/{order_id}` — which batches fulfill this order
- `GET /api/orders/recommendations` — AI order quantity recommendations

#### [NEW] `backend/routers/procurement.py`
- `GET /api/procurement/recommendations` — all current procurement recommendations
- `POST /api/procurement/generate` — run agentic AI to generate new recommendations
- `PUT /api/procurement/{rec_id}/approve` — approve a recommendation
- `GET /api/procurement/history` — past procurement actions

#### [NEW] `backend/routers/ai.py`
- `POST /api/ai/chat` — RAG-powered natural language chat
- `GET /api/ai/insights` — agentic AI proactive alerts
- `POST /api/ai/storage-advice` — LLM explains optimal placement
- `GET /api/ai/forecast/{item_id}` — demand forecast with AI commentary

#### [NEW] `backend/routers/reports.py`
- `GET /api/reports/dashboard` — KPIs + summary stats
- `GET /api/reports/wastage` — expired/over-ripe analysis
- `GET /api/reports/demand` — demand vs supply trend data
- `GET /api/reports/storage-efficiency` — utilization over time
- `GET /api/reports/ripeness-timeline` — all batches on a ripeness timeline

#### [NEW] `backend/routers/websocket.py`
- `WS /ws/dashboard` — push live KPI updates
- `WS /ws/alerts` — push real-time alert notifications
- `WS /ws/storage` — push storage layout changes

---

#### [NEW] `backend/engine/storage_optimizer.py`
**LIFO-aware 3D storage placement:**
- Sort batches by `expected_ripeness_date` ascending (earliest = closest to exit)
- Assign 3D coordinates: `(row, col, depth)` in container grid
- Bin-packing respects weight capacity per zone
- Detect conflicts: early-expiry batch behind late-expiry batch
- Return placement map + conflict warnings

#### [NEW] `backend/engine/ripeness_predictor.py`
- Sigmoid ripeness curve per category (bananas, avocados, tomatoes, etc.)
- Inputs: `received_date`, `variety`, `storage_temp_c`
- Output: `predicted_ripeness_date`, `confidence`, `days_until_ripe`
- Temperature deviation correction (adjusts prediction when temp changes)

#### [NEW] `backend/engine/demand_forecaster.py`
- Moving average over historical order data
- Per-item, per-city demand patterns
- Output: projected demand for next 7/14/30 days

#### [NEW] `backend/engine/procurement_engine.py`
- Compare projected demand vs usable stock (ripeness-adjusted)
- Factor in supplier lead times
- Output: `item`, `order_qty_kg`, `order_by_date`, `rationale`

#### [NEW] `backend/engine/rag_engine.py`
- Index inventory, orders, batches into **ChromaDB** using `sentence-transformers`
- On chat query: embed question → retrieve top-k context chunks → Gemini LLM response
- Re-index on every inventory mutation (triggered by event bus)

#### [NEW] `backend/engine/event_bus.py`
- In-memory async event bus (FastAPI `asyncio`)
- Event types: `BATCH_ADDED`, `ORDER_CHANGED`, `EXPIRY_ALERT`, `STOCK_LOW`, `TEMP_DEVIATION`
- Each event → subscribing handlers (optimizer, RAG re-index, WebSocket push, alert generator)

---

#### [NEW] `backend/seed_data.py`
Generates rich synthetic data on first run:
- **15 perishable categories**: bananas, avocados, mangoes, tomatoes, strawberries, lettuce, milk, cheese, fish, chicken, apples, oranges, grapes, spinach, broccoli
- **8 storage containers**: 3 refrigerated, 2 ambient, 2 cold-chain, 1 freezer
- **50 clients** across 10 cities
- **200 delivery orders** spanning next 60 days
- **300 inventory batches** at varying ripeness stages
- **Historical data**: 90 days of past orders and consumption

#### [NEW] `backend/data/perishables_catalog.json`
Master catalog with ripeness curves, storage temperature ranges, and lead times per category.

---

### Frontend (Next.js)

#### [NEW] `frontend/` — Next.js 14 App
7-page mobile-first dashboard with dark glassmorphism design.

**Pages:**

| Route | Description |
|---|---|
| `/` | Dashboard — KPI cards, live alerts, quick stats |
| `/inventory` | Inventory table, batch entry form, ripeness timeline |
| `/storage` | 2D/3D visual storage map (color = ripeness stage) |
| `/orders` | Order management + fulfillment tracker |
| `/procurement` | AI procurement recommendations + approve/reject |
| `/reports` | Rich charts: wastage, demand, storage efficiency, trends |
| `/ai-assistant` | RAG chat + agentic insights panel |

**Simulation Mode** — time-travel slider on dashboard: drag to any future date → see predicted inventory state, which batches are ripe, and what orders are at risk.

**Key Components:**

| Component | Function |
|---|---|
| `StorageMap` | Container grid — color-coded by ripeness (green→yellow→red) |
| `RipenessTimeline` | Gantt-like chart: batch ripeness windows vs delivery dates |
| `AIInsightsPanel` | Live AI alert feed with severity badges |
| `ProcurementCard` | Recommendation cards with approve/reject actions |
| `BatchScanner` | Batch intake form with AI ripeness auto-prediction |
| `DemandChart` | Projected vs actual demand per item |
| `SimulationSlider` | Time-travel to preview any future date |
| `LiveAlertBanner` | WebSocket-driven real-time alert bar |

---

### Configuration & Scripts

#### [NEW] `.env.example`
```
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./sism.db
CHROMA_PERSIST_DIR=./chroma_db
```

#### [NEW] `start.ps1`
One-command Windows startup: activates venv, seeds DB, starts backend + frontend.

#### [NEW] `README.md`
Full setup, architecture, and feature documentation.

---

## AI/ML Innovation Summary

| Feature | Technology | Judging Criterion |
|---|---|---|
| RAG Chat Assistant | ChromaDB + sentence-transformers + Gemini | AI Technologies |
| Agentic Procurement | Event bus + LLM auto-recommendations | Agentic AI |
| Ripeness Prediction | Sigmoid curves + temp correction | Innovative Design |
| LIFO 3D Optimizer | Custom bin-packing + conflict detection | Complexity |
| Demand Forecasting | Moving average + AI explanation | Dynamic Execution |
| WebSocket Live Push | Real-time event-driven UI updates | Dynamic Execution |
| Time-Travel Simulation | Future state preview with slider | Innovative Thinking |
| Audit Trail | Full change log on every mutation | Complexity |

---

## Verification Plan

### Backend
```powershell
cd backend
py -m uvicorn main:app --reload --port 8000
# Seed data runs automatically on startup
```

Key endpoints to verify:
```
GET  http://localhost:8000/api/reports/dashboard
GET  http://localhost:8000/api/storage/layout
GET  http://localhost:8000/api/procurement/recommendations
GET  http://localhost:8000/api/ai/insights
POST http://localhost:8000/api/ai/chat  {"message": "How many bananas will be ripe tomorrow?"}
```

### Frontend
```powershell
cd frontend
npm run dev
# Open http://localhost:3000
```

### Browser Walkthrough
1. Dashboard — verify KPI cards and live alert banner
2. Storage page — verify color-coded container grid
3. AI Assistant — test: *"Which batches expire before Friday's delivery?"*
4. Procurement — verify AI recommendations with quantities and dates
5. Simulation slider — drag to +7 days, verify ripeness state updates
6. Mobile viewport (375px) — verify responsive layout
