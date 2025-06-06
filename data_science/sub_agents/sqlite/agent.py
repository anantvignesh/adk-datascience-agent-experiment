import os

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from . import tools
from .prompts import return_instructions_sqlite


def setup_before_agent_call(callback_context: CallbackContext) -> None:
    """Setup the SQLite agent."""
    if "database_settings" not in callback_context.state:
        callback_context.state["database_settings"] = tools.get_database_settings()


database_agent = Agent(
    model=os.getenv("SQLITE_AGENT_MODEL"),
    name="database_agent",
    instruction=return_instructions_sqlite(),
    tools=[tools.initial_sqlite_nl2sql, tools.run_sqlite_validation],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)
