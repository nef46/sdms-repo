"""Service layer: interfaces and stateless helpers."""
from .document_service import DocumentService, RealDocumentService
from .otp_service import OTPService

__all__ = ["DocumentService", "RealDocumentService", "OTPService"]
