#!/usr/bin/env python3
"""
Claude Project Auto-Initializer
Automatically sets up memory system for Claude agents working on this project
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def initialize_claude_memory():
    """Initialize memory system for Claude"""
    try:
        from init_agent_memory import initialize_agent, start_task

        # Initialize memory for Claude
        memory = initialize_agent("claude")

        # Store Claude's arrival
        memory.store_context(
            "agent_session",
            "Claude agent initialized for project work",
            "high"
        )

        # Check for previous work
        analytics = memory.get_analytics()
        if analytics.get("total_sessions", 0) > 1:
            print(f"\n📚 Found previous work in this project:")
            print(f"   - {analytics.get('total_decisions', 0)} decisions made")
            print(f"   - {analytics.get('total_patterns', 0)} patterns learned")
            print(f"   - {analytics.get('files_analyzed', 0)} files analyzed")

        return memory

    except Exception as e:
        print(f"Warning: Could not initialize memory system: {e}")
        return None

def store_claude_context():
    """Store Claude-specific context"""
    try:
        from init_agent_memory import get_project_integrator

        integrator = get_project_integrator()

        # Store Claude's capabilities
        integrator.memory.store_context(
            "agent_capabilities",
            "Claude: Advanced coding, debugging, architecture design, pattern recognition",
            "high"
        )

        # Store working context
        integrator.memory.store_context(
            "working_directory",
            os.getcwd(),
            "normal"
        )

    except:
        pass

# Auto-run when imported
if __name__ != "__main__":
    # When imported by Claude, initialize automatically
    memory = initialize_claude_memory()
    store_claude_context()

    # Store in global scope for Claude to access
    import builtins
    builtins.project_memory = memory