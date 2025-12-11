"""
PyStock - Python Stock Analysis Project
Auto-initializes Agent Memory System for any agent working on this project
"""

# Initialize memory system for agents
try:
    from .claude_project_init import initialize_claude_memory, store_claude_context
    from .init_agent_memory import get_project_integrator

    # Auto-initialize for any agent
    memory = initialize_claude_memory()
    store_claude_context()

    # Make available globally
    import sys
    sys.modules[__name__].memory = memory
    sys.modules[__name__].project_integrator = get_project_integrator()

    # Store initialization
    if memory:
        memory.store_context(
            "agent_session",
            f"Agent initialized module: PyStock",
            "normal"
        )

except ImportError:
    # Memory system not available
    pass
except Exception as e:
    # Silently fail to avoid breaking imports
    print(f"Note: Memory system initialization failed: {e}")

# Project metadata
__version__ = "1.0.0"
__author__ = "AI Agent"
__description__ = "Python Stock Analysis with Agent Memory System"