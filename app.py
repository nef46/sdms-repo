"""SDMS Demo Web Application.

Flask backend that wraps the existing SDMS modules to provide a visual
interface for the Phase 3 demonstration video.

Run:  python3 app.py
Open: http://localhost:5000
"""

from __future__ import annotations

import os
import sys
import base64
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory

# Make the sdms package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sdms.models.document import Document
from sdms.models.session import Session
from sdms.models.report import Report
from sdms.patterns.audit_logger import AuditLogger
from sdms.patterns.encryption_strategy import AES256Strategy, NoOpStrategy
from sdms.patterns.observer import NotificationService
from sdms.patterns.security_proxy import SecurityProxy
from sdms.patterns.user_factory import UserFactory
from sdms.services.document_service import RealDocumentService
from sdms.services.otp_service import OTPService

# Application bootstrap

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

AuditLogger._reset()

# Encryption key (demo only)
AES_KEY = os.urandom(32)

# Core services
real_service = RealDocumentService(encryption=AES256Strategy(AES_KEY))
notifier = NotificationService()
real_service.attach(notifier)

proxy = SecurityProxy(real_service=real_service)
otp_service = OTPService()

# Demo credentials (password hash would be used in production)
DEMO_CREDENTIALS = {
    "nefeli":       {"password": "admin2026",  "user_id": 1},
    "konstantinos": {"password": "editor2026", "user_id": 2},
    "sanjana":      {"password": "viewer2026", "user_id": 3},
}

# Pre-register demo users via Factory
demo_users = {
    1: UserFactory.create_user(1, "Nefeli", "nefeli@sdms.ac.uk", "admin"),
    2: UserFactory.create_user(2, "Konstantinos", "kon@sdms.ac.uk", "editor"),
    3: UserFactory.create_user(3, "Sanjana", "sanjana@sdms.ac.uk", "viewer"),
}
for u in demo_users.values():
    proxy.register_user(u)

# State
active_sessions: dict[int, Session] = {}
pending_2fa: dict[int, bool] = {}       # user_id waiting for OTP
next_doc_id = 1


# Helpers

def _user_dict(u):
    return {
        "user_id": u.user_id, "name": u.name, "email": u.email,
        "role": u.role, "status": u.status, "permissions": u.permissions(),
    }

def _doc_dict(d):
    return {
        "doc_id": d.doc_id, "name": d.name, "owner_id": d.owner_id,
        "version": d.version, "locked_by": d.locked_by,
        "size": len(d.content), "created_at": d.created_at.isoformat(),
    }

def _log_dict(entry):
    return {
        "audit_id": entry.audit_id, "user_id": entry.user_id,
        "action_type": entry.action_type, "document_id": entry.document_id,
        "details": entry.details, "timestamp": entry.timestamp.isoformat(),
    }

def _event_dict(ev):
    return {
        "event_type": ev.event_type, "document_id": ev.document_id,
        "actor_user_id": ev.actor_user_id, "details": ev.details,
    }


# Static

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# AUTH Step 1: password, Step 2: OTP (two-factor)

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Step 1 validate username + password, then issue OTP."""
    data = request.json
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    cred = DEMO_CREDENTIALS.get(username)
    if not cred or cred["password"] != password:
        AuditLogger().log_action(user_id=0, action_type="LOGIN_FAILED",
                                 details=f"username={username}")
        return jsonify({"error": "Invalid username or password"}), 401

    uid = cred["user_id"]
    user = demo_users[uid]

    # Generate OTP for second factor
    code = otp_service.generate_otp(uid)
    pending_2fa[uid] = True

    AuditLogger().log_action(user_id=uid, action_type="PASSWORD_OK",
                             details="OTP sent to email")

    return jsonify({
        "step": "otp_required",
        "user_id": uid,
        "name": user.name,
        "email": user.email,
        "otp_hint": code,
        "message": f"Password accepted. A 6-digit code has been sent to {user.email}.",
    })


@app.route("/api/auth/verify-otp", methods=["POST"])
def auth_verify_otp():
    """Step 2 validate OTP and complete login."""
    data = request.json
    uid = int(data["user_id"])
    code = data.get("code", "")

    if uid not in pending_2fa:
        return jsonify({"error": "No pending login for this user"}), 400

    valid = otp_service.validate_otp(uid, code)
    if not valid:
        AuditLogger().log_action(user_id=uid, action_type="OTP_FAILED",
                                 details="invalid or expired code")
        return jsonify({"error": "Invalid or expired OTP code"}), 401

    # OTP passed complete login
    del pending_2fa[uid]
    user = demo_users[uid]
    user.login()

    session = Session.create_session(
        user_id=uid,
        session_id=f"sess-{uid}-{datetime.utcnow().timestamp():.0f}",
        ip_address=request.remote_addr or "127.0.0.1",
    )
    active_sessions[uid] = session

    AuditLogger().log_action(user_id=uid, action_type="LOGIN_COMPLETE",
                             details=f"2FA passed, ip={session.ip_address}")

    return jsonify({
        "message": f"{user.name} logged in successfully",
        "user": _user_dict(user),
        "session_id": session.session_id,
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    data = request.json
    uid = int(data["user_id"])
    user = demo_users.get(uid)
    if not user:
        return jsonify({"error": "Unknown user"}), 404

    sess = active_sessions.pop(uid, None)
    if sess:
        sess.close()
    user.logout()

    AuditLogger().log_action(user_id=uid, action_type="LOGOUT",
                             details="session closed")
    return jsonify({"message": f"{user.name} logged out"})


# DOCUMENTS real file upload via multipart form

@app.route("/api/documents", methods=["GET"])
def list_documents():
    docs = list(real_service._repo.values())
    return jsonify([{
        **_doc_dict(d),
        "encrypted": not isinstance(real_service._cipher, NoOpStrategy),
    } for d in docs])


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Accept real files via multipart/form-data."""
    global next_doc_id
    uid = int(request.form.get("user_id", 0))

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "No file selected"}), 400

    file_bytes = uploaded.read()
    filename = uploaded.filename

    doc = Document(
        doc_id=next_doc_id,
        name=filename,
        owner_id=uid,
        content=file_bytes,
    )
    next_doc_id += 1
    original_size = len(file_bytes)

    try:
        result = proxy.upload_file(doc, uid)
        return jsonify({
            "success": result,
            "document": _doc_dict(doc),
            "encrypted": True,
            "original_size": original_size,
            "encrypted_size": len(doc.content),
        })
    except (PermissionError, ValueError) as e:
        next_doc_id -= 1
        return jsonify({"error": str(e)}), 403


@app.route("/api/upload-text", methods=["POST"])
def upload_text():
    """Fallback: upload with typed filename + content (for security demos)."""
    global next_doc_id
    data = request.json
    uid = int(data["user_id"])
    filename = data["filename"]
    content = data.get("content", "").encode()

    doc = Document(doc_id=next_doc_id, name=filename, owner_id=uid, content=content)
    next_doc_id += 1

    try:
        result = proxy.upload_file(doc, uid)
        return jsonify({
            "success": result, "document": _doc_dict(doc),
            "encrypted": True, "original_size": len(content),
            "encrypted_size": len(doc.content),
        })
    except (PermissionError, ValueError) as e:
        next_doc_id -= 1
        return jsonify({"error": str(e)}), 403


@app.route("/api/download", methods=["POST"])
def download_file():
    data = request.json
    uid = int(data["user_id"])
    doc_id = int(data["doc_id"])
    try:
        doc = proxy.download_file(doc_id, uid)
        try:
            text = doc.content.decode("utf-8")
            return jsonify({"document": _doc_dict(doc), "content": text,
                            "binary": False, "decrypted": True})
        except UnicodeDecodeError:
            return jsonify({"document": _doc_dict(doc),
                            "content": base64.b64encode(doc.content).decode(),
                            "binary": True, "decrypted": True})
    except (PermissionError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/reserve", methods=["POST"])
def reserve_doc():
    data = request.json
    uid = int(data["user_id"])
    doc_id = int(data["doc_id"])
    try:
        result = proxy.reserve(doc_id, uid)
        return jsonify({"success": result, "doc_id": doc_id,
                        "locked_by": uid if result else None})
    except (PermissionError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/release", methods=["POST"])
def release_doc():
    data = request.json
    uid = int(data["user_id"])
    doc_id = int(data["doc_id"])
    try:
        result = proxy.release(doc_id, uid)
        return jsonify({"success": result, "doc_id": doc_id})
    except (PermissionError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/search", methods=["POST"])
def search_docs():
    data = request.json
    query = data["query"]
    try:
        results = proxy.search(query)
        return jsonify({"query": query, "results": [_doc_dict(d) for d in results],
                        "count": len(results)})
    except ValueError as e:
        return jsonify({"error": str(e), "blocked": True}), 400


# Audit / Notifications / Report

@app.route("/api/audit", methods=["GET"])
def get_audit_log():
    return jsonify([_log_dict(e) for e in AuditLogger().get_logs()])


@app.route("/api/audit/report", methods=["POST"])
def generate_report():
    data = request.json
    uid = int(data.get("user_id", 1))
    logs = AuditLogger().get_logs()
    report = Report(report_id=1, generated_by=uid)
    body = report.generate([str(l) for l in logs])
    return jsonify({"body": body, "size": len(report.download())})


@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    return jsonify([_event_dict(e) for e in notifier.sent])


# Design patterns metadata

@app.route("/api/patterns", methods=["GET"])
def get_patterns():
    return jsonify([
        {"name": "Proxy Pattern", "class": "SecurityProxy",
         "description": "Wraps RealDocumentService with permission checks, rate limiting, input validation, and audit logging. Transparent to callers via the DocumentService interface.",
         "file": "patterns/security_proxy.py"},
        {"name": "Singleton Pattern", "class": "AuditLogger",
         "description": "Thread-safe singleton holding the in-memory audit trail. All modules share one instance, ensuring a consistent, tamper-resistant log.",
         "file": "patterns/audit_logger.py"},
        {"name": "Factory Method Pattern", "class": "UserFactory",
         "description": "Creates Admin, Editor, or Viewer instances by role string. Extensible via register_role() without modifying the factory itself.",
         "file": "patterns/user_factory.py"},
        {"name": "Strategy Pattern", "class": "AES256Strategy / EncryptionStrategy",
         "description": "Defines interchangeable encryption algorithms. RealDocumentService delegates to the injected strategy, satisfying NFR-01 (AES-256 at rest) without coupling to a specific cipher.",
         "file": "patterns/encryption_strategy.py"},
        {"name": "Observer Pattern", "class": "Subject / NotificationService",
         "description": "RealDocumentService (Subject) notifies attached Observers on every state change. NotificationService captures events for email alerts (FR-05).",
         "file": "patterns/observer.py"},
    ])


# Run

if __name__ == "__main__":
    print("\n  SDMS Demo running at http://localhost:5000")
    print("  Demo credentials:")
    print("    nefeli       / admin2026   (Admin)")
    print("    konstantinos / editor2026  (Editor)")
    print("    sanjana      / viewer2026  (Viewer)\n")
    app.run(debug=False, port=5000)

