from unittest.mock import patch
from ai_assistant.tools import compare_time_of_day, get_risk_level_breakdown

SAMPLE_EVENTS = [
    {"created_at": "2026-09-04T09:15:12Z", "risk_level": "HIGH"},
    {"created_at": "2026-09-04T14:41:03Z", "risk_level": "CRITICAL"},
    {"created_at": "2026-09-05T10:02:47Z", "risk_level": "MEDIUM"},
]


@patch("ai_assistant.tools._get", return_value=SAMPLE_EVENTS)
def test_compare_time_of_day_buckets_correctly(mock_get):
    result = compare_time_of_day()
    assert result["morning_count"] == 2
    assert result["afternoon_count"] == 1


@patch("ai_assistant.tools._get", return_value=SAMPLE_EVENTS)
def test_compare_time_of_day_filters_by_date(mock_get):
    result = compare_time_of_day(date="2026-09-04")
    assert result["morning_count"] == 1
    assert result["afternoon_count"] == 1


@patch("ai_assistant.tools._get", return_value=SAMPLE_EVENTS)
def test_risk_level_breakdown_counts_each_level(mock_get):
    result = get_risk_level_breakdown()
    assert result["total"] == 3
    assert result["breakdown"] == {"HIGH": 1, "CRITICAL": 1, "MEDIUM": 1}