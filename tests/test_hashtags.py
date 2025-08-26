from bot.parser.hashtags import parse_hashtags


def test_parse_hashtags_accepts_full_lecture_sequence():
    text = "\n".join(
        [
            "#lecture",
            "#المحاضرة_1: العنوان",
            "#1446",
            "#الدكتور_فلان",
        ]
    )
    info, error = parse_hashtags(text)
    assert error is None
    assert info.content_type == "lecture"
    assert info.lecture_no == 1
    assert info.title == "العنوان"
    assert info.year == 1446
    assert info.lecturer == "فلان"
