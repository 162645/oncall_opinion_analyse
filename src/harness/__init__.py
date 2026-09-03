"""Evidence-driven Agent Harness for network measurement analysis.

The graph implementation is loaded lazily so catalog/contract tooling can be
used without importing the optional LangGraph runtime.
"""


def get_harness():
    from .graph import get_harness as factory
    return factory()


__all__ = ["get_harness"]
