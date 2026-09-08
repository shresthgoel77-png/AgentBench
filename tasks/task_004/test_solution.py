from solution import to_hex


def test_positive():
    assert to_hex(255) == "ff"


def test_zero():
    assert to_hex(0) == "0"


def test_negative():
    assert to_hex(-255) == "-ff"