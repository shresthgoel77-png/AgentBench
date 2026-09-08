from solution import count_words


def test_single_spaces():
    assert count_words("the quick brown fox") == 4


def test_repeated_spaces():
    assert count_words("a  b") == 2


def test_leading_trailing_spaces():
    assert count_words("  hi   there  ") == 2