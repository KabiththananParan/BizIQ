"""BizIQ — Multi-Agent System Runner & Launcher.

Runs the integrated multi-agent gateway on http://127.0.0.1:8000
"""

import sys
import uvicorn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    print("=" * 70)
    print("BizIQ - Unified Multi-Agent Business Intelligence Assistant")
    print("=" * 70)
    print("  * Web App & Frontend:    http://127.0.0.1:8000")
    print("  * Interactive Swagger:   http://127.0.0.1:8000/docs")
    print("  * Integrated Agents:")
    print("      [1] NLP Query Agent (Member 1)")
    print("      [2] Data Retrieval / IR Agent (Member 2)")
    print("      [3] LLM Insight Agent (Member 3)")
    print("      [4] Security & Compliance Agent (Member 4)")
    print("=" * 70)
    uvicorn.run("app_gateway:app", host="127.0.0.1", port=8000, reload=True)

