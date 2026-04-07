# Secure Document Management System (SDMS)

Reference implementation for the 5CM505 Software Engineering coursework, Phase 3.
Implements the class model defined in the SDS and three of the five design
patterns: Proxy, Singleton, and Factory Method.

## Repository layout

```
sdms-repo/
├── src/sdms/
│   ├── models/        # Domain classes (User, Session, Document, AuditLog, Report)
│   ├── patterns/      # SecurityProxy, AuditLogger singleton, UserFactory
│   └── services/      # DocumentService interface, OTPService
├── tests/             # pytest unit tests
├── docs/              # Coding conventions and design notes
└── README.md
```

## Running

```bash
python -m pip install -r requirements.txt
python -m pytest tests/
```

## Authors

Group coursework, 5CM505 Software Engineering, 2025-26.
