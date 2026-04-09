"""
RAG Engine — ChromaDB vector store + Gemini LLM for natural language inventory queries.
Embeds inventory, batches, and orders into ChromaDB.
On query: embed question → retrieve top-k context → Gemini response.
"""
import os
import uuid
import json
from datetime import date
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# Lazy imports to avoid startup errors if packages not available
_chroma_client = None
_collection = None
_gemini_model = None
_embedder = None


def _get_chroma():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name="sism_inventory",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_gemini():
    global _gemini_model
    if _gemini_model is None and GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    return _gemini_model


def _embed(texts: List[str]) -> List[List[float]]:
    embedder = _get_embedder()
    return embedder.encode(texts, convert_to_numpy=True).tolist()


def index_inventory(batches: List[Any], orders: List[Any], items: List[Any]):
    """Index all inventory data into ChromaDB for RAG queries."""
    try:
        collection = _get_chroma()
        docs, ids, metadatas = [], [], []

        # Index inventory batches
        for b in batches:
            item_name = b.item.name if hasattr(b, 'item') and b.item else "Unknown"
            text = (
                f"Batch {b.batch_id}: {item_name} ({b.variety or 'standard variety'}), "
                f"{b.quantity_kg}kg, received {b.received_date}, "
                f"expected ripe {b.expected_ripeness_date}, expires {b.expiry_date}, "
                f"status: {b.status}, ripeness score: {b.ripeness_score:.2f}"
            )
            docs.append(text)
            ids.append(f"batch_{b.batch_id}")
            metadatas.append({
                "type": "batch", "batch_id": b.batch_id,
                "item": item_name, "status": b.status,
                "ripeness_date": b.expected_ripeness_date.isoformat()
                if hasattr(b.expected_ripeness_date, 'isoformat') else str(b.expected_ripeness_date)
            })

        # Index orders
        for o in orders:
            items_str = ", ".join(
                f"{oi.item.name} {oi.quantity_kg}kg"
                for oi in o.order_items if hasattr(oi, 'item') and oi.item
            )
            text = (
                f"Order {o.order_id}: Client {o.client_name} in {o.city}, "
                f"delivery on {o.delivery_date}, status: {o.status}, priority: {o.priority}. "
                f"Items: {items_str or 'no items'}"
            )
            docs.append(text)
            ids.append(f"order_{o.order_id}")
            metadatas.append({
                "type": "order", "order_id": o.order_id,
                "client": o.client_name, "city": o.city, "status": o.status,
                "delivery_date": o.delivery_date.isoformat()
                if hasattr(o.delivery_date, 'isoformat') else str(o.delivery_date)
            })

        # Index perishable catalog
        for item in items:
            text = (
                f"Product {item.name} (SKU: {item.sku}): category {item.category}, "
                f"stored in {item.zone} zone at {item.storage_temp_min_c}-{item.storage_temp_max_c}°C, "
                f"shelf life {item.shelf_life_days} days, peak ripeness at day {item.ripeness_peak_day}, "
                f"reorder point {item.reorder_point_kg}kg, lead time {item.lead_days} days."
            )
            docs.append(text)
            ids.append(f"item_{item.sku}")
            metadatas.append({"type": "item", "sku": item.sku, "name": item.name})

        if docs:
            embeddings = _embed(docs)
            # Upsert in batches of 100
            for i in range(0, len(docs), 100):
                collection.upsert(
                    documents=docs[i:i+100],
                    embeddings=embeddings[i:i+100],
                    ids=ids[i:i+100],
                    metadatas=metadatas[i:i+100]
                )
        return len(docs)
    except Exception as e:
        print(f"RAG indexing error: {e}")
        return 0


def query_rag(question: str, top_k: int = 8) -> Dict[str, Any]:
    """
    RAG pipeline: embed question → retrieve context → Gemini LLM response.
    Falls back to rules-based response if Gemini unavailable.
    """
    try:
        collection = _get_chroma()
        q_embedding = _embed([question])[0]
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        context_docs = results["documents"][0] if results["documents"] else []
        context = "\n".join([f"- {doc}" for doc in context_docs])

        today = date.today().isoformat()
        system_prompt = f"""You are SISM AI — an intelligent assistant for a perishable goods inventory and storage management system.
Today's date: {today}

You have access to the following live inventory data:
{context}

Answer the user's question accurately and concisely using the data above.
- Be specific: use batch IDs, quantities (kg), and dates when relevant.
- If a question asks about what's ripe today, check ripeness dates carefully.
- Flag any risks clearly (e.g., expiry, LIFO conflicts, stock gaps).
- If data is insufficient, say so honestly and suggest what action to take.
- Format your response in a clear, readable way."""

        model = _get_gemini()
        if model:
            response = model.generate_content(system_prompt + f"\n\nUser Question: {question}")
            answer = response.text
            source = "gemini"
        else:
            answer = _fallback_response(question, context_docs)
            source = "rules_engine"

        return {
            "answer": answer,
            "source": source,
            "context_chunks": len(context_docs),
            "question": question
        }

    except Exception as e:
        return {
            "answer": f"I encountered an error processing your query: {str(e)}. Please try rephrasing your question.",
            "source": "error",
            "context_chunks": 0,
            "question": question
        }


def generate_agentic_insights(db_summary: Dict[str, Any]) -> str:
    """Use Gemini to generate proactive insights from a DB summary snapshot."""
    try:
        model = _get_gemini()
        if not model:
            return _fallback_insights(db_summary)

        prompt = f"""You are an agentic AI for a perishable goods logistics company.
Analyze this inventory snapshot and generate 3-5 actionable, urgent insights.

Inventory Snapshot:
- Total active batches: {db_summary.get('total_batches', 0)}
- Items expiring in 24h: {db_summary.get('expiring_24h', 0)} batches ({db_summary.get('expiring_24h_kg', 0)}kg)
- Items below reorder point: {db_summary.get('below_reorder', [])}
- Storage utilization: {db_summary.get('storage_util_pct', 0):.1f}%
- Pending orders next 7 days: {db_summary.get('pending_orders_7d', 0)} orders worth {db_summary.get('pending_demand_kg', 0)}kg
- LIFO conflicts detected: {db_summary.get('conflicts', 0)}
- Overripe batches: {db_summary.get('overripe', 0)}

Generate exactly 3-5 short, specific, actionable insights. Each insight should:
1. Start with a severity emoji: 🔴 (critical), 🟡 (warning), 🟢 (info)
2. Name the specific item/batch/container
3. State the risk
4. Recommend the exact action

Format each as a single paragraph."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return _fallback_insights(db_summary)


def _fallback_response(question: str, context: List[str]) -> str:
    """Rules-based fallback when Gemini API unavailable."""
    q = question.lower()
    if "ripe" in q or "ripeness" in q:
        return (
            "Based on current inventory data:\n" +
            "\n".join(f"• {c}" for c in context[:5] if "ripe" in c.lower() or "batch" in c.lower())
            or "No batches matching ripeness query found."
        )
    elif "order" in q or "stock" in q:
        return "Current order and stock data:\n" + "\n".join(f"• {c}" for c in context[:5])
    else:
        return "Here's relevant inventory information:\n" + "\n".join(f"• {c}" for c in context[:5])


def _fallback_insights(summary: Dict) -> str:
    insights = []
    if summary.get("expiring_24h", 0) > 0:
        insights.append(f"🔴 {summary['expiring_24h']} batches ({summary.get('expiring_24h_kg', 0):.0f}kg) expire within 24 hours. Prioritize for immediate delivery or markdown.")
    if summary.get("conflicts", 0) > 0:
        insights.append(f"🟡 {summary['conflicts']} LIFO conflicts detected. Run storage optimizer to correct placement order.")
    if summary.get("below_reorder"):
        items_str = ", ".join(summary["below_reorder"][:3])
        insights.append(f"🟡 Low stock alert: {items_str} are below reorder points. Place purchase orders today.")
    if not insights:
        insights.append("🟢 Inventory levels are normal. No critical issues detected.")
    return "\n\n".join(insights)
