"""Safe, mockable Groq structured-output integration."""
import json
from app.core.config import settings
from app.schemas.security import SecurityAIResult
SYSTEM_PROMPT="""You are the Security & Compliance analysis component of BizIQ. Reason only from supplied evidence, express uncertainty, do not invent facts or claim any user is malicious or compromised."""
SCHEMA={"type":"object","additionalProperties":False,"required":["risk_level","suspicious","confidence","findings","evidence","recommendation"],"properties":{"risk_level":{"type":"string","enum":["LOW","MEDIUM","HIGH","UNKNOWN"]},"suspicious":{"type":"boolean"},"confidence":{"type":"number","minimum":0,"maximum":1},"findings":{"type":"array","items":{"type":"object","additionalProperties":False,"required":["signal","description"],"properties":{"signal":{"type":"string"},"description":{"type":"string"}}}},"evidence":{"type":"array","items":{"type":"string"}},"recommendation":{"type":"string"}}}
def fallback_result() -> SecurityAIResult: return SecurityAIResult(risk_level="UNKNOWN",suspicious=False,confidence=0.0,findings=[{"signal":"AI_ANALYSIS_UNAVAILABLE","description":"AI security analysis could not be completed."}],evidence=[],recommendation="Review the deterministic security signals manually.")
def safe_evidence(context) -> dict:
    data=context.model_dump(mode="json")
    forbidden=("password","secret","token","credential","api_key")
    def clean(value):
        if isinstance(value,dict): return {k:clean(v) for k,v in value.items() if not any(x in k.lower() for x in forbidden)}
        if isinstance(value,list): return [clean(v) for v in value]
        return value
    return clean(data)
def analyze_security_evidence(context, client=None) -> SecurityAIResult:
    if not settings.groq_api_key: return fallback_result()
    try:
        if client is None:
            from groq import Groq
            client=Groq(api_key=settings.groq_api_key)
        response=client.chat.completions.create(model=settings.groq_model,messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps(safe_evidence(context))}],response_format={"type":"json_schema","json_schema":{"name":"security_analysis","strict":True,"schema":SCHEMA}})
        return SecurityAIResult.model_validate_json(response.choices[0].message.content)
    except Exception: return fallback_result()
