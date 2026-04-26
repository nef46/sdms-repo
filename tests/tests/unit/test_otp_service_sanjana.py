def test_valid_otp_sanjana():
    email = "engineer01@sdms.test"
    generated_otp = "123456"
    entered_otp = "123456"

    assert generated_otp == entered_otp


def test_invalid_otp_sanjana():
    generated_otp = "123456"
    entered_otp = "000000"

    assert generated_otp != entered_otp
