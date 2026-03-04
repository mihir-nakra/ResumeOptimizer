"""
Base classes and types for LangGraph agents.
"""
from typing import TypedDict
from langgraph.graph import StateGraph


class AgentState(TypedDict):
    """Base state for all agents."""
    request_id: str
    status: str
    error: str | None


class BaseAgent:
    """Base class for all LangGraph agents."""

    def __init__(self, name: str):
        self.name = name
        self.graph = StateGraph(AgentState)

    def build_graph(self) -> StateGraph:
        """Build and return the agent's graph."""
        raise NotImplementedError("Subclasses must implement build_graph")

    async def run(self, input_state: dict) -> dict:
        """Execute the agent with the given input state."""
        compiled_graph = self.build_graph().compile()
        result = await compiled_graph.ainvoke(input_state)
        return result
