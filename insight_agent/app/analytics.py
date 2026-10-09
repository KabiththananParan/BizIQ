"""All arithmetic happens HERE (pandas), never inside the LLM."""
from typing import Any
import pandas as pd


def build_dataframe(sources) -> pd.DataFrame:
    rows = [r for s in sources for r in s.rows]
    return pd.DataFrame(rows)


def compute_stats(df: pd.DataFrame, metric: str, group_by: str | None, date_col: str | None) -> dict[str, Any]:
    if metric not in df.columns:
        raise ValueError(f"Metric column '{metric}' not found in retrieved data")
    df = df.copy()
    df[metric] = pd.to_numeric(df[metric], errors="coerce")
    df = df.dropna(subset=[metric])
    if df.empty:
        raise ValueError("No numeric values for the requested metric")

    stats: dict[str, Any] = {
        "metric": metric,
        "row_count": int(len(df)),
        "total": round(float(df[metric].sum()), 2),
        "average": round(float(df[metric].mean()), 2),
    }
    if group_by and group_by in df.columns:
        g = df.groupby(group_by)[metric].sum().sort_values(ascending=False)
        stats["group_by"] = group_by
        stats["by_group"] = {str(k): round(float(v), 2) for k, v in g.items()}
        stats["top_group"] = str(g.index[0])
        stats["bottom_group"] = str(g.index[-1])

    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        d = df.dropna(subset=[date_col])
        if not d.empty:
            monthly = d.set_index(date_col)[metric].resample("MS").sum()
            stats["monthly"] = {k.strftime("%Y-%m"): round(float(v), 2) for k, v in monthly.items()}
            if len(monthly) >= 2 and monthly.iloc[-2] != 0:
                stats["last_month_change_pct"] = round(
                    float((monthly.iloc[-1] - monthly.iloc[-2]) / monthly.iloc[-2] * 100), 1)
            if group_by and group_by in d.columns and len(monthly) >= 2:
                piv = d.groupby([pd.Grouper(key=date_col, freq="MS"), group_by])[metric].sum().unstack(group_by)
                prev, last = piv.iloc[-2], piv.iloc[-1]
                ch = ((last - prev) / prev.replace(0, float("nan")) * 100).dropna().round(1)
                stats["group_change_pct"] = {str(k): float(v) for k, v in ch.items()}
    return stats


def flatten_numbers(obj: Any) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out += flatten_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            out += flatten_numbers(v)
    return out


def build_chart(stats: dict[str, Any], forecast: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Chart.js-compatible spec built in code (not by the LLM)."""
    if "monthly" in stats:
        labels = list(stats["monthly"].keys())
        data = list(stats["monthly"].values())
        spec = {"type": "line", "data": {"labels": labels, "datasets": [
            {"label": stats["metric"], "data": data}]}}
        if forecast and forecast.get("available"):
            f = forecast["points"]
            spec["data"]["labels"] += [p["month"] for p in f]
            spec["data"]["datasets"][0]["data"] += [None] * len(f)
            spec["data"]["datasets"].append({"label": "forecast",
                "data": [None] * len(data) + [p["value"] for p in f], "borderDash": [5, 5]})
        return spec
    if "by_group" in stats:
        return {"type": "bar", "data": {"labels": list(stats["by_group"].keys()),
                "datasets": [{"label": stats["metric"], "data": list(stats["by_group"].values())}]}}
    return None
