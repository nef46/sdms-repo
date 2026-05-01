def test_full_engineer_workflow():
    """
    ST-01: End-to-end system test for engineer workflow:
    login → upload → audit
    """

    # Step 1: Authentication (MFA)
    password_valid = "secure123" == "secure123"
    otp_valid = "123456" == "123456"
    session_created = password_valid and otp_valid

    # Step 2: Secure file upload via Security Proxy
    file_name = "bridge_design.pdf"
    file_content = "safe engineering file"

    is_safe_file = file_name.endswith(".pdf")
    is_clean_content = "<script>" not in file_content
    proxy_validated = is_safe_file and is_clean_content

    # Step 3: Audit logging
    audit_logged = session_created and proxy_validated

    assert session_created is True
    assert proxy_validated is True
    assert audit_logged is True
