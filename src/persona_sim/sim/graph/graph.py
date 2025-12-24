"""Simulation LangGraph assembly."""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, StateGraph

from persona_sim.sim.graph.nodes import (
    GraphDependencies,
    evaluator_node,
    init_run_node,
    persist_node,
    persona_response_node,
    update_state_node,
)
from persona_sim.sim.graph.state import GraphState, RunMode


def _route_after_update(state: GraphState) -> str:
    turn_count = len(state.config.turns) or 1
    max_turns = 1 if state.config.mode == RunMode.SINGLE_TURN else turn_count
    return "continue" if state.current_turn < max_turns else "evaluate"


def build_simulation_graph(deps: GraphDependencies) -> StateGraph:
    """Construct the simulation graph with deterministic routing."""

    graph = StateGraph(GraphState)
    graph.add_node("init_run", partial(init_run_node, deps=deps))
    graph.add_node("persona_response", partial(persona_response_node, deps=deps))
    graph.add_node("update_state", update_state_node)
    graph.add_node("evaluator", partial(evaluator_node, deps=deps))
    graph.add_node("persist", partial(persist_node, deps=deps))

    graph.set_entry_point("init_run")
    graph.add_edge("init_run", "persona_response")
    graph.add_edge("persona_response", "update_state")
    graph.add_conditional_edges(
        "update_state",
        _route_after_update,
        {"continue": "persona_response", "evaluate": "evaluator"},
    )
    graph.add_edge("evaluator", "persist")
    graph.add_edge("persist", END)

    return graph
