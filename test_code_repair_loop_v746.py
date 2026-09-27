from aurora.agent import Agent

def test_code_repair_is_exposed_to_brain(tmp_path):
    a = Agent(str(tmp_path))
    tools = a.available_tools()
    assert "code_repair" in tools
    assert "regression_engineering" in tools
    prompt = a.brain.build_prompt("corrigir um erro", research=False)
    assert "code_repair" in prompt

def test_regression_engineering_tool_dispatch(tmp_path):
    a = Agent(str(tmp_path))
    result = a._call("regression_engineering", {"action": "status"})
    assert result["ok"]
