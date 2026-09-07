from unittest.mock import patch, MagicMock
from ai_assistant.assistant import WarehouseAssistant


def _mock_text_response(text: str):
    part = MagicMock()
    part.function_call = None
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = text
    return resp


def _mock_function_call_response(name: str, args: dict):
    call = MagicMock()
    call.name = name
    call.args = args
    part = MagicMock()
    part.function_call = call
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    resp = MagicMock()
    resp.candidates = [candidate]
    return resp


@patch("ai_assistant.assistant.genai.Client")
def test_ask_returns_direct_answer_without_tools(mock_client_cls):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_text_response("Hello, supervisor.")
    mock_client_cls.return_value = mock_client

    assistant = WarehouseAssistant(api_key="fake-key")
    result = assistant.ask("hi")

    assert result["answer"] == "Hello, supervisor."
    assert result["tools_used"] == []


@patch(
    "ai_assistant.assistant.TOOL_EXECUTORS",
    {"get_summary": lambda: {"most_common_behaviour": "dropping", "busiest_risky_video": "V001"}},
)
@patch("ai_assistant.assistant.genai.Client")
def test_ask_calls_tool_then_returns_grounded_answer(mock_client_cls):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        _mock_function_call_response("get_summary", {}),
        _mock_text_response("Dropping is the most common behaviour, mostly on V001."),
    ]
    mock_client_cls.return_value = mock_client

    assistant = WarehouseAssistant(api_key="fake-key")
    result = assistant.ask("What's the most common behaviour?")

    assert result["tools_used"] == ["get_summary"]
    assert "Dropping" in result["answer"]


@patch("ai_assistant.assistant.genai.Client")
def test_ask_stops_after_max_rounds(mock_client_cls):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_function_call_response("get_events", {})
    mock_client_cls.return_value = mock_client

    assistant = WarehouseAssistant(api_key="fake-key")
    result = assistant.ask("anything")

    assert "wasn't able to finish" in result["answer"]