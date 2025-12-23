from langgraph.graph import END, StateGraph

# TODO: Define the proper state schema and nodes for persona simulation.


def build_simulation_graph() -> StateGraph:
    """Construct the simulation graph."""

    graph = StateGraph(dict)
    graph.set_entry_point("start")
    graph.add_node("start", lambda state: state)
    graph.add_edge("start", END)
    return graph
