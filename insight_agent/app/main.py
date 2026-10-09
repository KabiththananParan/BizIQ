import json
from fastapi import Depends, FastAPI, HTTPException
from . import db, analytics, forecast as fc, llm, privacy, verify
from .auth import User, can_access, get_current_user, require_role
from .schemas import Feedback, InsightRequest, ReportCreate, ReportUpdate

app = FastAPI(title="BizIQ - LLM Insight Agent")
db.init_db()
WRITE_ROLES = {"admin", "manager", "analyst"}
DISCLAIMER = "AI-generated insight. Verify important decisions with the source data."


@app.get("/health")
def health():
    return {"status": "ok", "agent": "llm-insight"}


# ---------------------------------------------------------------- INSIGHTS
@app.post("/insights/generate")
def generate_insight(req: InsightRequest, user: User = Depends(get_current_user)):
    require_role(user, WRITE_ROLES)
    sq = req.structured_query
    base = {"question": req.question, "ai_generated": True, "disclaimer": DISCLAIMER}

    # 1. Validate: no data -> do NOT let the LLM guess
    if not any(s.rows or s.text for s in req.retrieved_data):
        out = {**base, "answer": "I don't have enough data to answer this question.",
               "key_findings": [], "reasoning_steps": ["Retrieval returned no records"],
               "assumptions": [], "confidence": "low", "limitations": "No data retrieved.",
               "evidence": [], "stats": {}, "chart_spec": None, "forecast": None,
               "grounded": True, "ungrounded_numbers": [], "security_flags": []}
        out["id"] = db.save_insight(user.id, req.question, out, "none")
        return out

    # 2. Security + privacy: detect injection, redact PII before the external LLM sees anything
    flags = privacy.find_injection([s.model_dump() for s in req.retrieved_data])
    safe_sources = [s.model_copy(update={"rows": privacy.redact(s.rows),
                                         "text": privacy.redact(s.text) if s.text else None})
                    for s in req.retrieved_data]

    # 3. Compute numbers in code
    df = analytics.build_dataframe(safe_sources)
    metric = sq.metric
    if not metric and not df.empty:
        nums = df.select_dtypes("number").columns
        metric = nums[0] if len(nums) else None
    try:
        stats = analytics.compute_stats(df, metric or "", sq.group_by, sq.date_column)
    except ValueError as e:
        raise HTTPException(422, str(e))

    forecast = None
    if sq.intent == "forecast" and "monthly" in stats:
        forecast = fc.forecast_monthly(stats["monthly"])

    # 4. LLM explains the computed numbers (structured JSON)
    evidence_csv = df.head(20).to_csv(index=False)
    texts = [s.text for s in safe_sources if s.text]
    if texts:
        evidence_csv += "\n" + "\n".join(texts)[:2000]
    result, model_used = llm.generate(req.question, stats, forecast, evidence_csv)

    # 5. Verify numbers
    text_blob = " ".join([result.get("answer", "")] + [str(x) for x in result.get("key_findings", [])])
    allowed = analytics.flatten_numbers(stats) + analytics.flatten_numbers(forecast)
    bad = verify.ungrounded_numbers(text_blob, allowed)
    confidence = result.get("confidence", "low")
    limitations = result.get("limitations", "")
    if bad:
        confidence = "low"
        limitations += f" WARNING: numbers not found in computed stats: {bad}."
    if flags:
        limitations += " Retrieved data contained suspicious instructions that were ignored."

    out = {**base, "answer": result.get("answer", ""), "key_findings": result.get("key_findings", []),
           "reasoning_steps": result.get("reasoning_steps", []),
           "assumptions": result.get("assumptions", []), "confidence": confidence,
           "limitations": limitations.strip(),
           "evidence": [{"source": s.source, "rows_used": len(s.rows)} for s in req.retrieved_data],
           "stats": stats, "chart_spec": analytics.build_chart(stats, forecast), "forecast": forecast,
           "grounded": not bad, "ungrounded_numbers": bad, "security_flags": flags,
           "model_used": model_used}
    out["id"] = db.save_insight(user.id, req.question, out, model_used)
    return out


def _load_insight(iid: str, user: User) -> dict:
    row = db.get_insight(iid)
    if not row:
        raise HTTPException(404, "Insight not found")
    if not can_access(user, row["user_id"]):
        raise HTTPException(403, "You cannot access this insight")
    return json.loads(row["payload"])


@app.get("/insights")
def list_insights(user: User = Depends(get_current_user), limit: int = 20, offset: int = 0):
    sql = "SELECT id,question,model_used,created_at FROM insights"
    args: list = []
    if user.role not in {"admin", "manager"}:
        sql += " WHERE user_id=?"
        args.append(user.id)
    with db.conn() as c:
        rows = c.execute(sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
    return [dict(r) for r in rows]


@app.get("/insights/{iid}")
def get_insight(iid: str, user: User = Depends(get_current_user)):
    return _load_insight(iid, user)


@app.post("/insights/{iid}/feedback")
def feedback(iid: str, fb: Feedback, user: User = Depends(get_current_user)):
    _load_insight(iid, user)
    with db.conn() as c:
        c.execute("UPDATE insights SET feedback=?, feedback_comment=? WHERE id=?",
                  (int(fb.helpful), fb.comment, iid))
    return {"saved": True}


# ---------------------------------------------------------------- REPORTS (CRUD)
def _report_row(rid: str, user: User):
    with db.conn() as c:
        row = c.execute("SELECT * FROM reports WHERE id=? AND deleted=0", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Report not found")
    if not can_access(user, row["user_id"]):
        raise HTTPException(403, "You cannot access this report")
    return row


@app.post("/reports", status_code=201)                      # CREATE
def create_report(body: ReportCreate, user: User = Depends(get_current_user)):
    require_role(user, WRITE_ROLES)
    _load_insight(body.insight_id, user)
    rid, ts = db.new_id(), db.now()
    with db.conn() as c:
        c.execute("INSERT INTO reports VALUES(?,?,?,?,?,0,0,?,?)",
                  (rid, user.id, body.insight_id, body.title, body.notes, ts, ts))
    return {"id": rid, "title": body.title}


@app.get("/reports")                                         # READ (list)
def list_reports(user: User = Depends(get_current_user), pinned: bool | None = None):
    q, args = "SELECT * FROM reports WHERE deleted=0", []
    if user.role not in {"admin", "manager"}:
        q += " AND user_id=?"
        args.append(user.id)
    if pinned is not None:
        q += " AND pinned=?"
        args.append(int(pinned))
    with db.conn() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY created_at DESC", args).fetchall()]


@app.get("/reports/{rid}")                                   # READ (one)
def get_report(rid: str, user: User = Depends(get_current_user)):
    row = _report_row(rid, user)
    return {**dict(row), "insight": _load_insight(row["insight_id"], user)}


@app.put("/reports/{rid}")                                   # UPDATE
def update_report(rid: str, body: ReportUpdate, user: User = Depends(get_current_user)):
    require_role(user, WRITE_ROLES)
    row = _report_row(rid, user)
    title = body.title if body.title is not None else row["title"]
    notes = body.notes if body.notes is not None else row["notes"]
    pinned = int(body.pinned) if body.pinned is not None else row["pinned"]
    with db.conn() as c:
        c.execute("UPDATE reports SET title=?,notes=?,pinned=?,updated_at=? WHERE id=?",
                  (title, notes, pinned, db.now(), rid))
    return {"id": rid, "title": title, "notes": notes, "pinned": bool(pinned)}


@app.delete("/reports/{rid}")                                # DELETE (soft)
def delete_report(rid: str, user: User = Depends(get_current_user)):
    require_role(user, WRITE_ROLES)
    _report_row(rid, user)
    with db.conn() as c:
        c.execute("UPDATE reports SET deleted=1, updated_at=? WHERE id=?", (db.now(), rid))
    return {"deleted": True}
