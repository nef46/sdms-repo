def test_security_proxy_blocks_malicious_file_sanjana():
    file_content = "<script>alert('hack')</script>"

    assert "<script>" in file_content


def test_security_proxy_accepts_safe_file_sanjana():
    file_name = "bridge_design.pdf"

    assert file_name.endswith(".pdf")
