# SISM — Smart Inventory & Storage Management 

Welcome to the newly built **SISM API & Next.js Dashboard**. This application is an advanced concept demonstrating high-complexity real-time capabilities with predictive AI and logic constraints for perishable goods logistics.

## 🚀 How to Run the App
I have created a simple startup script. 
1. Open PowerShell and run: `.\run_sism.bat`
2. This will automatically open two terminal windows, start the FastAPI Python server (indexing data & seeding DB), and start the Next.js Frontend.
3. Once running, go to **[http://localhost:3000](http://localhost:3000)** to view the live dashboard!

---

## 🌟 Key Features Demystified

### 1. Dynamic Execution & Event Bus
The entire backend uses an async Event Bus (`engine/event_bus.py`). If you add a new batch of Bananas to Storage Container A via the API, the system instantly publishes a `BATCH_ADDED` event.
- **Result:** This single action triggers the ChromaDB vector index to update, triggers the LIFO Storage Optimizer to re-calculate container conflicts, and pushes a real-time WebSocket payload to the Next.js frontend causing the UI to live-reload without refreshing the page!

### 2. Time-Travel Simulation
On the main Dashboard, there is a slider that lets you preview the **future state** of the warehouse. As you drag the slider, the Demand vs. Supply charts update intelligently, predicting supply quantities by calculating precisely what items will be ripe vs. overripe vs. expired on those specific days based on their biological curves.

### 3. Smart LIFO Storage Optimizer
Go to the **Storage Map** tab to see a visual 2D projection of the 3D storage bins. 
Because storage is a container, it operates on deeply constrained LIFO logic (Last In, First Out). The `storage_optimizer.py` automatically detects when "unripe" goods are physically trapping "ripe" goods deep within the container. 
- You can click the **Run Optimize AI** button to automatically re-sort matrices, swapping coordinates to resolve constraints.

### 4. Agentic Procurement Recommendations
Go to the **Procurement** tab to see recommendations. Instead of simple reorder points, the `procurement_engine.py` compares future delivery order commitments (Demand) against predicted usable inventory (Supply minus expected spoilage). If a deficit is detected, it auto-generates a Purchase Recommendation complete with the required "Order By Date" adjusting for supplier lead times.

### 5. Gemini-Powered Contextual Chat & Insights
Go to the **AI Assistant** tab to interact with the system.
- **RAG Chat**: Uses Google Gemini and ChromaDB to search the actual LIVE database. You can ask: *"Are any of the avocados expiring soon?"* and it will check the vectors, verify the current SQL DB, and generate a precise answer.
- **Agentic Insights**: Click 'Refresh' on the sidebar panel. The backend runs a background evaluation task that analyzes overall metrics and generates urgent text insights (e.g., *"Warning: Storage utilization is over 90% and you have 300kg of goods arriving tomorrow."*).

## Stack Breakdown
- **Frontend**: Next.js 14, Tailwind CSS, Recharts, Framer Motion, Lucide Icons.
- **Backend API**: FastAPI, Uvicorn, Python 3.12, WebSockets.
- **Database**: SQLite (SQLAlchemy ORM) w/ 9 relational models.
- **AI/ML Layer**: ChromaDB (Vector Store), `sentence-transformers`, `google-generativeai`.


