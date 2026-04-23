"""Shared pytest fixtures. Stubs FastMCP so server modules import without the SDK."""
import sys
import types


def _install_fastmcp_stub() -> None:
    """Install a no-op FastMCP stub so server modules can be imported in-process."""
    if "fastmcp" in sys.modules:
        return

    class _Stub:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def run(self, *args, **kwargs):
            pass

    module = types.ModuleType("fastmcp")
    module.FastMCP = _Stub
    sys.modules["fastmcp"] = module


_install_fastmcp_stub()

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
