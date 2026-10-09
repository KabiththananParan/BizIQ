"""Sample business datasets and seeding utilities for BizIQ."""

import csv
import io
from pathlib import Path

SAMPLE_DATASOURCES = [
    {
        "name": "Regional Sales & Performance 2025-2026",
        "description": "Comprehensive regional sales dataset covering Colombo, Kandy, Galle, Jaffna, North, South, East, and West branches with revenue, product sales, and quarterly performance notes.",
        "source_type": "csv",
        "content": """date,region,product,revenue,units_sold,customer_channel,notes
2025-01-15,Colombo,Product A,5890,210,Retail,Strong holiday demand in Western Province
2025-01-15,Kandy,Product A,4100,165,Retail,Stable demand in Central Province
2025-01-15,Galle,Product B,3640,140,Wholesale,Tourism sector orders expanding
2025-02-15,Colombo,Product B,6200,230,Retail,Promotional discount drove sales volume
2025-02-15,Kandy,Product B,4350,170,Retail,Consistent monthly sales
2025-02-15,Jaffna,Product A,3100,115,Wholesale,New distribution branch opening
2025-03-15,Colombo,Product A,6450,245,Retail,End of Q1 volume targets achieved
2025-03-15,Kandy,Product A,4600,180,Retail,Consistent performance
2025-03-15,Galle,Product A,3800,150,Wholesale,Steady orders
2025-04-15,Colombo,Product B,5900,220,Retail,Seasonal festival shopping demand
2025-04-15,Kandy,Product B,4400,175,Retail,Festival promotions successful
2025-04-15,West,Product A,3902,155,Distributor,Distributor contract renewed
2025-05-15,Colombo,Product A,6800,260,Retail,Top performing branch across all metrics
2025-05-15,Kandy,Product A,4700,185,Retail,Steady sales
2025-05-15,South,Product A,4666,190,Retail,Southern expansion underway
2025-06-15,Colombo,Product B,7100,275,Retail,Mid-year revenue peak
2025-06-15,North,Product A,3574,140,Wholesale,Northern logistics improving
2025-06-15,East,Product A,4766,180,Retail,Eastern region sales solid
2025-07-15,Colombo,Product A,6950,265,Retail,Sustained high volume
2025-07-15,West,Product A,3212,130,Distributor,West region distributor warning of retail contract termination
2025-07-15,South,Product B,4838,195,Retail,Strong retail demand
2025-08-15,Colombo,Product B,7300,285,Retail,New product bundle launch
2025-08-15,West,Product A,2945,115,Distributor,Distributor disputes ongoing
2025-08-15,Kandy,Product B,4871,190,Retail,Steady customer acquisition
2025-09-15,Colombo,Product A,7550,295,Retail,Colombo achieved highest Q3 revenue
2025-09-15,West,Product B,2859,105,Distributor,West region sales decreased by 18% in Q3 mainly due to key distributor losing their major retail contract
2025-09-15,East,Product B,5010,200,Retail,Eastern branch growth
2025-10-15,Colombo,Product B,7800,305,Retail,Q4 enterprise accounts onboarded
2025-10-15,West,Product B,2608,98,Distributor,Transitioning to direct retail channel
2025-10-15,South,Product B,5067,205,Retail,Expanding shelf space
2025-11-15,Colombo,Product A,8100,320,Retail,Pre-holiday surge
2025-11-15,Kandy,Product A,5357,215,Retail,Central region record month
2025-11-15,East,Product B,4834,195,Wholesale,Wholesale fulfillment
2025-12-15,Colombo,Product A,8650,345,Retail,Colombo achieved peak annual sales revenue of 8650 in December
2025-12-15,South,Product A,5373,220,Retail,Southern region second highest sales
2025-12-15,Kandy,Product B,5400,225,Retail,Strong year-end close""",
    },
    {
        "name": "Product Line Margins & Category Revenue",
        "description": "Product catalog performance metrics including units sold, unit revenue, gross profit margin, return rate, and customer satisfaction rating across categories.",
        "source_type": "csv",
        "content": """product_id,product_name,category,unit_price,cost_per_unit,units_sold,total_revenue,gross_margin_pct,return_rate_pct,satisfaction_score
PRD-001,Product A,Electronics,45.00,22.50,14500,652500,50.0,1.2,4.8
PRD-002,Product B,Hardware,35.00,18.00,12800,448000,48.6,0.8,4.6
PRD-003,Product C,Accessories,15.00,5.50,24000,360000,63.3,2.1,4.4
PRD-004,Product D,Enterprise Services,250.00,75.00,1200,300000,70.0,0.2,4.9
PRD-005,Product E,Maintenance Packs,95.00,38.00,2800,266000,60.0,0.5,4.7""",
    },
    {
        "name": "Quarterly Financial KPIs & Branch Operations",
        "description": "Executive summary of quarterly revenue, operating expenses, net profit, delayed order counts, and branch efficiency benchmarks.",
        "source_type": "text",
        "content": """BIZIQ EXECUTIVE SUMMARY — FINANCIAL & OPERATIONAL REPORT 2025:

Quarterly Financial Breakdown:
- Q1 2025: Revenue was $412,000, Operating Expenses were $288,000, Net Profit was $124,000 (30.1% Net Margin).
- Q2 2025: Revenue was $478,000, Operating Expenses were $315,000, Net Profit was $163,000 (34.1% Net Margin).
- Q3 2025: Revenue was $521,000, Operating Expenses were $342,000, Net Profit was $179,000 (34.3% Net Margin). West region underperformed due to contract termination.
- Q4 2025: Revenue was $615,000, Operating Expenses were $380,000, Net Profit was $235,000 (38.2% Net Margin). Driven by Colombo and Southern branch records.
- Total Annual Revenue reached $2,026,000 with Total Net Profit of $701,000.

Branch Logistics & Operational Delivery Analysis:
- Colombo branch maintained a 98.4% on-time delivery rate with only 12 delayed orders in Q3 and 9 in Q4.
- Kandy branch achieved 96.1% on-time delivery rate with 22 delayed orders across the second half of the year.
- West distribution hub recorded 64 delayed orders in Q3 due to carrier logistics bottlenecks and warehouse reorganization.
- Galle branch maintained 97.2% fulfillment speed with average order processing turnaround of 1.4 days.""",
    },
    {
        "name": "Customer Segments & Channel Retention",
        "description": "Customer retention rates, average order values, and revenue contribution by customer segment.",
        "source_type": "text",
        "content": """CUSTOMER SEGMENTATION & CHANNEL RETENTION ANALYSIS:

1. Enterprise SME Clients:
- Total active clients: 142 businesses.
- Revenue contribution: 48% of total revenue.
- Annual retention rate: 94.2%.
- Average annual contract value: $14,200.

2. Retail Direct Consumers:
- Total active customers: 8,450 accounts.
- Revenue contribution: 36% of total revenue.
- Repeat purchase rate: 68.5%.
- Average order value: $148.50.

3. Wholesale & Regional Distributors:
- Total distributor partners: 28 partners across 5 provinces.
- Revenue contribution: 16% of total revenue.
- West region distributor contract dropped volume by 18% in Q3 before direct channel substitution was deployed in Q4.""",
    },
]


def parse_csv_rows(content: str) -> list[dict]:
    """Parse CSV text content into a list of row dicts."""
    try:
        reader = csv.DictReader(io.StringIO(content.strip()))
        return [dict(row) for row in reader]
    except Exception:
        return []
