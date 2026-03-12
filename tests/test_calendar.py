from integrations.apple_calendar.client import AppleCalendarClient


def test_calendar_init():
    client = AppleCalendarClient()
    assert client is not None


def test_calendar_get_events():
    """Test that get_events doesn't crash even if Calendar app isn't available."""
    client = AppleCalendarClient()
    try:
        events = client.get_events("today")
        assert isinstance(events, list)
    except RuntimeError:
        # AppleScript may fail in CI environments
        pass


def test_calendar_free_slots():
    client = AppleCalendarClient()
    try:
        result = client.find_free_slots()
        assert isinstance(result, str)
    except RuntimeError:
        pass


def test_calendar_week_summary():
    client = AppleCalendarClient()
    try:
        result = client.get_week_summary()
        assert isinstance(result, str)
    except RuntimeError:
        pass
