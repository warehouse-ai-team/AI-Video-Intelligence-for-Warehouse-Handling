from unittest.mock import patch, MagicMock
from ai_assistant.assistant import WarehouseAssistant


def _mock_text_response(text: str):
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp.content = [block]
    return resp


def _mock_tool_use_response(tool_name: str, tool_input: dict, tool_use_id="tu_1"):
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    resp.content = [block]
    return resp


@patch("ai_assistant.assistant.Anthropic")
def test_ask_returns_direct_answer_without_tools(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response("Hello, supervisor.")
    mock_anthropic_cls.return_value = mock_client

    assistant = WarehouseAssistant(api_key="fake-key")
    result = assistant.ask("hi")

    assert result["answer"] == "Hello, supervisor."
    assert result["tools_used"] == []


@patch("ai_assistant.assistant.TOOL_EXECUTORS", {"get_busiest_bay": lambda: {"bay": "Bay 3", "incident_count": 5}})
@patch("ai_assistant.assistant.Anthropic")
def test_ask_calls_tool_then_returns_grounded_answer(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_tool_use_response("get_busiest_bay", {}),
        _mock_text_response("Bay 3 has the most incidents (5)."),
    ]
    mock_anthropic_cls.return_value = mock_client

    assistant = WarehouseAssistant(api_key="fake-key")
    result = assistant.ask("Which bay has the most incidents?")

    assert result["tools_used"] == ["get_busiest_bay"]
    assert "Bay 3" in result["answer"]


@patch("ai_assistant.assistant.Anthropic")
def test_ask_stops_after_max_rounds(mock_anthropic_cls):
    mock_client = MagicMock()
    # Always returns tool_use, forcing the loop to hit MAX_TOOL_ROUNDS.
    mock_client.messages.create.return_value = _mock_tool_use_response("get_events", {})
    mock_anthropic_cls.return_value = mock_client

    assistant = WarehouseAssistant(api_key="fake-key")
    result = assistant.ask("anything")

    assert "wasn't able to finish" in result["answer"]