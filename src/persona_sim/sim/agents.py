from langchain_core.runnables import Runnable, RunnableLambda

# TODO: Flesh out persona agents using LangChain primitives.


def build_agent() -> Runnable:
    """Return a placeholder agent runnable."""

    return RunnableLambda(lambda state: state)
