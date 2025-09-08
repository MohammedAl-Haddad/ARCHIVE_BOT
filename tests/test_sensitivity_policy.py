from bot.policies.sensitivity import SensitivityPolicy


def test_detect_sensitive_text():
    policy = SensitivityPolicy()
    assert policy.is_sensitive("patient with SSN 123-45-6789")
    assert not policy.is_sensitive("hello world")


def test_detect_sensitive_filename():
    policy = SensitivityPolicy()
    assert policy.is_sensitive("", filename="patient_record.png", section="clinical")
    assert not policy.is_sensitive("", filename="image.png")
