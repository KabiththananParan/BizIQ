import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.query_service import process_question

examples = [
    "Compare sales between Colombo and Kandy in January.",
    "Which product had the highest sales last month?",
    "What is the total revenue this month?",
    "What will the sales be next month?",
    "Show the sales trend for the West region in Q3.",
]

for question in examples:
    print("\nQUESTION:", question)
    result = process_question(question)
    print("INTENT:", result["intent"])
    print("ENTITIES:", result["entities"])
    print("STRUCTURED:", result["structured_query"])
