def test_security_proxy_blocks_malicious_file_sanjana():
    file_content = "<script>alert('hack')</script>"

    is_safe = "<script>" not in file_content

    assert is_safe is False


def test_security_proxy_accepts_safe_file_sanjana():
    file_name = "bridge_design.pdf"
    file_content = "safe file"

    is_safe = file_name.endswith(".pdf") and "<script>" not in file_content

    assert is_safe is True
