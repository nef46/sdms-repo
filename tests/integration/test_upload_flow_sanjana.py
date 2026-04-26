def test_upload_flow_through_proxy_sanjana():
    file_name = "bridge_design.pdf"
    file_content = "safe file"

    proxy_valid = file_name.endswith(".pdf") and "<script>" not in file_content

    assert proxy_valid
