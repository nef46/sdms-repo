from src.security_proxy import SecurityProxy

def test_security_proxy_blocks_malicious_file_sanjana():
    proxy = SecurityProxy()
    result = proxy.validate("attack.docm", "<script>alert('hack')</script>")
    assert result is False

def test_security_proxy_accepts_safe_file_sanjana():
    proxy = SecurityProxy()
    result = proxy.validate("bridge_design.pdf", "safe engineering file")
    assert result is True
