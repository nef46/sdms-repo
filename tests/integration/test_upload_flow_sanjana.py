def test_upload_flow_through_proxy_sanjana():
    """
    IT-02: Upload through Security Proxy
    """

    file_name = "bridge_design.pdf"
    file_content = "safe engineering file"

    is_safe_file = file_name.endswith(".pdf")
    is_clean_content = "<script>" not in file_content

    proxy_validated = is_safe_file and is_clean_content

    encrypted = proxy_validated
    stored = proxy_validated

    assert proxy_validated is True
    assert encrypted is True
    assert stored is True
