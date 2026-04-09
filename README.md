# SISM - Smart Inventory & Storage Management 🍎🥑📦

**SISM** is an AI-powered perishable supply chain optimization system designed to eliminate food waste, prevent LIFO conflicts, and automate procurement decisions. It combines mathematical algorithms for physical 3D optimization with cognitive AI for real-time monitoring and chat.

---

## 🎯 Overview

Warehouses handling perishable goods often rely on static expiry dates and manual spreadsheets. This leads to LIFO (Last-In, First-Out) conflicts where older items get trapped behind new stock, expiring silently. 

SISM actively addresses this by:
- **Predicting Spoilage Physically:** Using mathematical Sigmoid curves based on real-world IoT temperature data to determine exact ripeness progression.
- **Optimizing 3D Storage Space:** A bin-packing chronological algorithm mathematically determines physical matrix positions (Row, Col, Depth) for every incoming batch to ensure older goods are dispatched first.
- **Automating Procurement:** The AI watches live inventory vs upcoming delivery orders and autonomously suggests what to order exactly relative to supplier lead times.
- **Answering Natural Language Questions:** A Retrieval-Augmented Generation (RAG) loop leverages local Vector Search to pass specific warehouse records to Gemini, allowing warehouse managers to query their inventory conversationally.

---

## 💻 Technologies Used

**Architecture:** Event-driven microservice pattern.

### Frontend
- **Framework:** Next.js 14, React
- **Styling:** Tailwind CSS (Glassmorphism design)
- **Real-Time Integration:** WebSocket API
- **Charts:** Recharts

### Backend
- **Framework:** FastAPI (Python)
- **Database (Relational):** SQLite + SQLAlchemy ORM (12,000+ synthetic records)
- **Database (Vector):** ChromaDB (Local persistent vector store for RAG)
- **AI / LLM:** Google Gemini Pro
- **Embedding Model:** `sentence-transformers` (`all-MiniLM-L6-v2`)

---

## ⚙️ How It Works

1. **Ripeness Prediction Engine:** Applies biologically accurate Sigmoid degradation functions. For example, if zone temperatures rise above optimal by 1°C, a 5% acceleration penalty is applied to the ripeness score in real-time.
2. **3D Storage Optimizer:** When a batch is received, it triggers the Event Bus. The optimizer scans all batches in the container, orders them chronologically by expected ripeness date, and recalculates coordinates (`pos = index // depth`, etc.) to prevent physical LIFO blockages.
3. **AI Procurement Engine:** Identifies confirmed future delivery orders and cross-references them with *usable* stock (excluding expired/at-risk items). Factoring in the specific item's `lead_days`, it auto-generates a purchase recommendation with an urgent "Order By" deadline if the threshold is near.
4. **Vector RAG Chatbot:** When users submit prompts, the backend embeds the query using a local model, finds the Top 8 most mathematically similar inventory instances in ChromaDB, injects them into the Gemini System Prompt, and returns accurate, data-backed insights.

---

## 🚀 How to Run the Project

The workspace includes an automated startup script for Windows environments.

1. Clone this repository.
2. Ensure you have Python and Node.js installed.
3. Ensure you have your `GEMINI_API_KEY` defined in the `.env` file at the root.
4. Double click the **`run_sism.bat`** file from the root configuration directory.

This script will automatically:
- Launch a new terminal, activate the Python virtual environment, and start the FastAPI Backend Server on port `8000`.
- Launch a second terminal and start the Next.js Frontend Server on port `3000`.

**Endpoints:**
- Dashboard: `http://localhost:3000`
- API Documentation: `http://localhost:8000/docs`
