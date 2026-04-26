from src.otp_service import OTPService

def test_valid_otp_sanjana():
    service = OTPService()
    result = service.validate("123456", "123456")
    assert result is True

def test_invalid_otp_sanjana():
    service = OTPService()
    result = service.validate("123456", "000000")
    assert result is False

def test_empty_otp_sanjana():
    service = OTPService()
    result = service.validate("123456", "")
    assert result is False
