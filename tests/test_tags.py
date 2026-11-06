from tags import parse_tags


def test_parse_tags_drops_whitespace_only():
    assert parse_tags("red, ,blue") == ["red", "blue"]
    assert parse_tags("a, , ,b") == ["a", "b"]
