"""BizIQ — Multi-Agent System Runner & Launcher.

Runs the integrated multi-agent gateway on http://127.0.0.1:8000
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("🧠 Starting BizIQ — Agentic AI Business Intelligence Assistant")
    print("=" * 70)
    print("  • Integrated Gateway & Frontend: http://127.0.0.1:8000")
    print("  • Interactive API Documentation: http://127.0.0.1:8000/docs")
    print("  • All 4 Specialized Agents Integrated:")
    print("      1. 🗣️ NLP Query Agent (Member 1)")
    print("      2. 🔎 Data Retrieval / IR Agent (Member 2)")
    print("      3. 🧠 LLM Insight Agent (Member 3)")
    print("      4. 🔐 Security & Compliance Agent (Member 4)")
    print("=" * 70)
    uvicorn.run("app_gateway:app", host="0.0.0.0", port=8000, reload=True)
