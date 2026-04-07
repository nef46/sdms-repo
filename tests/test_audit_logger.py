"""Unit tests for the Singleton AuditLogger."""
from sdms.patterns.audit_logger import AuditLogger


def setup_function(_):
    AuditLogger._reset()


def test_singleton_returns_same_instance():
    a = AuditLogger()
    b = AuditLogger()
    assert a is b


def test_log_action_persists_across_references():
    AuditLogger().log_action(user_id=1, action_type="LOGIN")
    assert len(AuditLogger().get_logs()) == 1


def test_archive_clears_entries():
    logger = AuditLogger()
    logger.log_action(user_id=1, action_type="UPLOAD", document_id=10)
    archived = logger.archive_logs()
    assert len(archived) == 1
    assert logger.get_logs() == []


def test_get_logs_returns_copy():
    logger = AuditLogger()
    logger.log_action(user_id=1, action_type="LOGIN")
    snapshot = logger.get_logs()
    snapshot.clear()
    assert len(logger.get_logs()) == 1
