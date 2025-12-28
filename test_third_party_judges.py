from third_party_judges import judge_tool_necessity

def test_judge_tool_necessity_false() -> None:
    """
    Test that the judge tool for context retrieval necessity gives a result of False
    for trivial queries and questions that can be answered from existing context.
    """
    query1 = "How are you"
    assert not judge_tool_necessity(query1)[0]
    
    query2 = "give me the 3 big picture context titles?"
    assert not judge_tool_necessity(query2)[0]


def test_judge_tool_necessity_true() -> None:
    """
    Test that the judge tool for context retrieval necessity gives a result of True
    for queries more specific to the organizaiton.
    """
    query1 = "next steps for data processing team?"
    assert judge_tool_necessity(query1)[0]

    query2 = "did we have a optics team meeting last week?"
    assert judge_tool_necessity(query1)[0]
