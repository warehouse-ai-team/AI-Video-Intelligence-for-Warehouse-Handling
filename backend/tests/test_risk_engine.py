from backend.app.risk_engine import assess
from backend.app.schemas import EventCreate


def test_dropping_event_has_critical_risk():
    event = EventCreate(
        event_id="EVT_V001_001", video_id="V001", start_time=1.0, end_time=1.4,
        behaviour="dropping", confidence=0.8, reason="Sudden downward motion followed by a stop",
    )
    result = assess(event, repeat_frequency=0)
    assert result.level == "CRITICAL"
    assert result.score == 83
    assert "potential handling risk" in result.explanation


def test_outside_area_is_medium_without_amplifiers():
    event = EventCreate(
        event_id="EVT_V001_002", video_id="V001", start_time=1.0, end_time=1.2,
        behaviour="outside_designated_area", confidence=0.5, reason="Object outside handling zone",
    )
    result = assess(event, repeat_frequency=0)
    assert result.level == "MEDIUM"
    assert result.score == 40


def test_pipeline_level_is_preserved_for_shared_contract():
    event = EventCreate(
        event_id="EVT_V001_003", video_id="V001", start_time=1.0, end_time=8.0,
        behaviour="throwing", risk="HIGH", confidence=0.9, reason="High-speed product motion",
    )
    result = assess(event, repeat_frequency=5)
    assert result.level == "HIGH"
    assert 60 <= result.score <= 79


def test_member_two_raw_event_shape_is_accepted():
    event = EventCreate.model_validate({
        "behaviour": "stepping_on_carton", "start_frame": 366, "end_frame": 410,
        "start_time": 12.2, "end_time": 13.67, "confidence": 0.6,
        "reason": "Foot keypoint overlapped a carton", "risk": "HIGH",
    })
    assert event.event_id.startswith("EVT_")
    assert event.video_id == "UNKNOWN"
    assert event.reported_risk == "HIGH"
