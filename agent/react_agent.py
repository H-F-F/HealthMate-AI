from langchain.agents import create_agent

from agent.prompts import SYSTEM_PROMPT
from agent.tools.agent_tools import HEALTH_TOOLS
from model.factory import get_chat_model


def create_health_agent():
    llm = get_chat_model()
    agent = create_agent(
        model=llm,
        tools=HEALTH_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        debug=False,
        name="healthmate_agent",
    )
    return agent
