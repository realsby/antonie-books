from app.books import make_filter, now


def test_no_filter():
    assert make_filter(None, None, None) == {}
    assert make_filter("", "", "") == {}


def test_author_and_title():
    query = make_filter("Mark", "Learning", None)
    assert query["author"].pattern == "Mark"
    assert query["title"].pattern == "Learning"


def test_filter_ignores_case():
    query = make_filter("mark", None, None)
    assert query["author"].search("Mark Lutz")


def test_filter_escapes_regex():
    # A user can not send a regex. ".*" means the text ".*".
    query = make_filter(None, ".*", None)
    assert not query["title"].search("Learning Python")
    assert query["title"].search("a .* b")


def test_tags():
    query = make_filter(None, None, "Python, learning")
    patterns = query["tags"]["$all"]
    assert len(patterns) == 2
    assert patterns[0].match("python")
    assert patterns[1].match("Learning")
    # A tag must match the whole word.
    assert not patterns[0].match("Python3")


def test_empty_tags():
    assert make_filter(None, None, " , ") == {}


def test_now_has_milliseconds_only():
    assert now().microsecond % 1000 == 0
    assert now().tzinfo is not None
