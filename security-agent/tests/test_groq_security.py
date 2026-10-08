"""Groq boundary tests that never call the provider."""
import unittest
from datetime import datetime, timezone
from app.core.config import settings
from app.schemas.security import SecurityAnalysisResponse, SecuritySummary
from app.services.groq_security_service import analyze_security_evidence, safe_evidence
class GroqSecurityTest(unittest.TestCase):
 def test_missing_key_uses_safe_fallback_and_sanitizes(self):
  context=SecurityAnalysisResponse(user_id=1,window_start=datetime.now(timezone.utc),window_end=datetime.now(timezone.utc),summary=SecuritySummary(total_login_attempts=0,successful_logins=0,failed_logins=0,successful_login_rate=0,failed_login_rate=0,unique_ip_addresses=0,access_denied_events=0,invalid_token_events=0,expired_token_events=0,security_related_audit_events=0),signals=[],evidence=[])
  original=settings.groq_api_key; settings.groq_api_key=None
  try: self.assertEqual(analyze_security_evidence(context).risk_level,"UNKNOWN")
  finally: settings.groq_api_key=original
  self.assertNotIn("password",str(safe_evidence(context)).lower())
if __name__=='__main__': unittest.main()
