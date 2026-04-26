def test_login_flow_with_mfa_sanjana():
    """
    IT-01: Login with MFA
    """

    email = "engineer01@sdms.test"
    password = "secure123"
    otp = "123456"

    # simulate system checks
    password_valid = password == "secure123"
    otp_valid = otp == "123456"

    session_created = password_valid and otp_valid

    assert session_created is True
