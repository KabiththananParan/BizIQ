"""Isolated tests for audit and login-attempt persistence."""
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.database.database import Base
from app.database.models import AuditLog, LoginAttempt, Role, User
from app.core.security import hash_password
from app.services.auth_service import InvalidCredentialsError, authenticate_user
from app.services.audit_service import get_events, record_event
from app.services.rbac_service import seed_access_control

class AuditTrackingTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.engine=create_engine(f"sqlite:///{Path(self.tmp.name) / 'audit.db'}"); Base.metadata.create_all(self.engine); self.db=Session(self.engine); seed_access_control(self.db)
        role=self.db.scalar(select(Role).where(Role.name=="USER")); self.user=User(username="audit-user",email="audit@example.com",password_hash=hash_password("StrongPassword123"),full_name="Audit User",role=role); self.db.add(self.user); self.db.commit()
    def tearDown(self): self.db.close(); self.engine.dispose(); self.tmp.cleanup()
    def test_login_success_and_failure_are_recorded_without_passwords(self):
        authenticate_user(self.db,"audit@example.com","StrongPassword123","127.0.0.1","test-agent")
        with self.assertRaises(InvalidCredentialsError): authenticate_user(self.db,"missing@example.com","WrongPassword123")
        self.assertEqual(self.db.query(LoginAttempt).count(),2)
        self.assertEqual({e.action for e in get_events(self.db)}, {"LOGIN_SUCCESS","LOGIN_FAILED"})
        self.assertNotIn("StrongPassword123", " ".join((e.details or "") for e in get_events(self.db)))
    def test_audit_filtering(self):
        record_event(self.db,"USER_CREATED","SUCCESS",self.user.id,"/api/v1/users/2")
        self.assertEqual(len(get_events(self.db,action="USER_CREATED")),1)
        self.assertEqual(len(get_events(self.db,user_id=self.user.id)),1)

if __name__ == "__main__": unittest.main()
