"""Contain unit tests for the behavior of third-party LLM judges that are in
assistance of the main RAG agent."""

from src.utils.third_party_judges import judge_tool_necessity
from langgraph.checkpoint.memory import InMemorySaver

MEMORY = InMemorySaver()

def test_judge_tool_necessity_greeting() -> None:
    """
    Test that the judge tool for context retrieval necessity gives a result of False
    for small talk and greetings.
    """
    query = "How are you"
    assert not judge_tool_necessity(query, memory=MEMORY)[0]
    
    
def test_judge_tool_necessity_context_clear() -> None:
    """
    Test that the judge tool for context retrieval necessity gives a result of False
    for questions that can be answered from existing context.
    """
    query = "give me the 3 big picture context titles?"
    assert not judge_tool_necessity(query, memory=MEMORY)[0]


def test_judge_tool_necessity_team_specific() -> None:
    """
    Test that the judge tool for context retrieval necessity gives a result of True
    for team-specific questions.
    """
    query = "Next steps for data processing team?"
    assert judge_tool_necessity(query, memory=MEMORY)[0]


def test_judge_tool_necessity_time_specific() -> None:
    """
    Test that the judge tool for context retrieval necessity gives a result of True
    for time_specific questions.
    """
    query = "What is the last time we discussed trade for dark frame calibration?"
    assert judge_tool_necessity(query, memory=MEMORY)[0]


if __name__ == '__main__':
    import pytest
    pytest.main()