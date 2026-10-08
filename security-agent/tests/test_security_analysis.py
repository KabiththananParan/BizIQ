"""Deterministic security-analysis tests using an isolated SQLite database."""
import tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.database import Base
from app.database.models import LoginAttempt, AuditLog
from app.services.security_analyzer import analyze_security_events
from app.services.security_event_service import get_security_events
class SecurityAnalysisTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.engine=create_engine(f"sqlite:///{Path(self.tmp.name)/'test.db'}"); Base.metadata.create_all(self.engine); self.db=Session(self.engine); self.now=datetime.now(timezone.utc)
 def tearDown(self): self.db.close(); self.engine.dispose(); self.tmp.cleanup()
 def test_empty_and_observable_signals(self):
  result=analyze_security_events(1,self.now-timedelta(hours=1),self.now,[],[]); self.assertEqual(result.summary.total_login_attempts,0)
  attempts=[LoginAttempt(email='x@example.com',success=False,ip_address='1.1.1.1',timestamp=self.now) for _ in range(5)]+[LoginAttempt(email='x@example.com',success=False,ip_address='2.2.2.2',timestamp=self.now)]
  audits=[AuditLog(action='ACCESS_DENIED',status='FAILED',created_at=self.now) for _ in range(3)]+[AuditLog(action='INVALID_TOKEN',status='FAILED',created_at=self.now)]
  result=analyze_security_events(1,self.now-timedelta(hours=1),self.now,attempts,audits)
  self.assertEqual(result.summary.failed_login_rate,1); self.assertEqual(result.summary.unique_ip_addresses,2); self.assertIn('REPEATED_FAILED_LOGINS',[s.type for s in result.signals]); self.assertIn('INVALID_TOKEN_ACTIVITY',[s.type for s in result.signals])
if __name__=='__main__': unittest.main()
