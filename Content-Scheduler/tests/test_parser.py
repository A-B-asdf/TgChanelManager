from content_scheduler.services.anekdot_parser import fetch_anekdot

def test_parser():
    result = fetch_anekdot()
    assert isinstance(result, str)