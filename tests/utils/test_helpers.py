import transcription_bot.utils.helpers


def test_format_time():
    assert transcription_bot.utils.helpers.format_time(None) == "???"
    assert transcription_bot.utils.helpers.format_time(0.1) == "00:00"
    assert transcription_bot.utils.helpers.format_time(61.0) == "01:01"
    assert transcription_bot.utils.helpers.format_time(3661.0) == "1:01:01"
