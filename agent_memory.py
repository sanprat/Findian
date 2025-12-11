#!/usr/bin/env python3
"""
Agent Memory System Python Wrapper
Provides Python API for the Agent Memory System
"""

import json
import os
import subprocess
import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path


class AgentMemory:
    """Python interface for the Agent Memory System"""

    def __init__(self, memory_dir: Optional[str] = None, session_id: Optional[str] = None, agent_name: str = "claude"):
        """
        Initialize the Agent Memory interface

        Args:
            memory_dir: Directory to store memories (default: ./.agent_memory)
            session_id: Unique session identifier (default: timestamp)
            agent_name: Name of the agent (default: claude)
        """
        self.memory_dir = memory_dir or os.path.join(os.getcwd(), ".agent_memory")
        self.session_id = session_id or str(int(datetime.datetime.now().timestamp()))
        self.agent_name = agent_name
        self.memory_script = os.path.join(os.path.dirname(__file__), "agent_memory.sh")

        # Set environment variables
        os.environ["AGENT_MEMORY_DIR"] = self.memory_dir
        os.environ["AGENT_SESSION_ID"] = self.session_id
        os.environ["AGENT_NAME"] = self.agent_name

        # Initialize if not exists
        if not os.path.exists(self.memory_dir):
            self.init()

    def _run_command(self, command: List[str]) -> str:
        """Run a memory system command"""
        try:
            result = subprocess.run(
                [self.memory_script] + command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Memory command failed: {e.stderr}")

    def init(self) -> None:
        """Initialize the memory system"""
        self._run_command(["init"])

    def store_context(self, context_type: str, content: str, priority: str = "normal") -> None:
        """
        Store context information

        Args:
            context_type: Type of context (e.g., architecture, design)
            content: Context content
            priority: low, normal, high, critical
        """
        self._run_command(["store-context", context_type, content, priority])

    def store_decision(self, decision: str, reasoning: str, files_affected: str,
                      impact: str = "medium", alternatives: str = "") -> None:
        """
        Store a coding decision

        Args:
            decision: What was decided
            reasoning: Why this decision was made
            files_affected: Comma-separated list of affected files
            impact: low, medium, high, critical
            alternatives: Alternative approaches considered
        """
        cmd = ["store-decision", decision, reasoning, files_affected, impact]
        if alternatives:
            cmd.append(alternatives)
        self._run_command(cmd)

    def store_codebase_knowledge(self, file_path: str, knowledge: str,
                               knowledge_type: str = "general", confidence: str = "medium") -> None:
        """
        Store knowledge about a codebase file

        Args:
            file_path: Path to the file
            knowledge: What was learned
            knowledge_type: general, pattern, anti-pattern, optimization
            confidence: low, medium, high
        """
        self._run_command(["store-codebase", file_path, knowledge, knowledge_type, confidence])

    def store_error(self, error_type: str, solution: str, error_code: str = "",
                   stack_trace: str = "", prevention: str = "") -> None:
        """
        Store an error pattern

        Args:
            error_type: Type of error
            solution: How to fix it
            error_code: Error code if available
            stack_trace: Stack trace
            prevention: How to prevent in future
        """
        cmd = ["store-error", error_type, solution, error_code, stack_trace, prevention]
        # Remove empty strings
        cmd = [arg for arg in cmd if arg]
        self._run_command(cmd)

    def store_pattern(self, pattern_name: str, pattern_code: str, use_case: str,
                     pattern_type: str = "design", tags: str = "") -> None:
        """
        Store a reusable pattern

        Args:
            pattern_name: Name of the pattern
            pattern_code: Code template
            use_case: When to use this pattern
            pattern_type: design, algorithm, optimization, security
            tags: Comma-separated tags
        """
        cmd = ["store-pattern", pattern_name, pattern_code, use_case, pattern_type, tags]
        # Remove empty strings
        cmd = [arg for arg in cmd if arg]
        self._run_command(cmd)

    def create_checkpoint(self, description: str) -> str:
        """
        Create a checkpoint

        Args:
            description: Description of the checkpoint

        Returns:
            Checkpoint ID
        """
        result = self._run_command(["checkpoint", description])
        # Extract checkpoint ID from output
        return result.split()[-1]

    def query_context(self, context_type: str, search_term: str = "", priority: str = "") -> List[str]:
        """
        Query stored context

        Args:
            context_type: Type of context to query
            search_term: Optional search term
            priority: Optional priority filter

        Returns:
            List of matching context entries
        """
        cmd = ["query-context", context_type]
        if search_term:
            cmd.append(search_term)
        if priority:
            cmd.append(priority)

        result = self._run_command(cmd)
        return result.split('\n') if result else []

    def recommend_patterns(self, context: str, task_type: str) -> List[Dict[str, str]]:
        """
        Get pattern recommendations

        Args:
            context: Current context
            task_type: Type of task being performed

        Returns:
            List of recommended patterns with metadata
        """
        result = self._run_command(["recommend", context, task_type])
        # Parse recommendations (basic implementation)
        recommendations = []
        for line in result.split('\n'):
            if line.strip():
                recommendations.append({"pattern": line.strip()})
        return recommendations

    def health_check(self) -> Dict[str, Any]:
        """
        Perform project health check

        Returns:
            Health check results
        """
        result = self._run_command(["health"])
        return {"output": result}

    def generate_report(self, report_type: str = "summary", output_file: Optional[str] = None) -> str:
        """
        Generate a memory report

        Args:
            report_type: summary, detailed, analytics
            output_file: Optional file to save report

        Returns:
            Report content
        """
        cmd = ["report", report_type]
        if output_file:
            cmd.append(output_file)

        result = self._run_command(cmd)
        return result

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        session_file = os.path.join(self.memory_dir, "sessions", "current.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}

    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data"""
        analytics_file = os.path.join(self.memory_dir, "analytics", "stats.json")
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                return json.load(f)
        return {}


class MemoryContext:
    """Context manager for automatic memory operations"""

    def __init__(self, memory: AgentMemory, operation: str, description: str):
        self.memory = memory
        self.operation = operation
        self.description = description
        self.checkpoint_id = None
        self.errors = []

    def __enter__(self):
        # Create checkpoint before operation
        self.checkpoint_id = self.memory.create_checkpoint(f"Before: {self.description}")
        self.memory.store_context("operation_start", f"Starting: {self.description}", "normal")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Store error if exception occurred
            error_msg = f"{exc_type.__name__}: {exc_val}"
            self.memory.store_error(error_msg, "Exception occurred during operation", str(exc_type))
            self.errors.append(error_msg)
        else:
            # Store successful completion
            self.memory.store_context("operation_complete", f"Completed: {self.description}", "normal")

        return False  # Don't suppress exceptions


# Convenience decorator for automatic memory tracking
def track_memory(memory: AgentMemory, operation_type: str = "function"):
    """Decorator to automatically track function execution in memory"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = f"{operation_type}:{func.__name__}"

            with MemoryContext(memory, func_name, f"Executing {func_name}"):
                try:
                    result = func(*args, **kwargs)
                    memory.store_context("function_success", f"{func_name} completed successfully", "normal")
                    return result
                except Exception as e:
                    memory.store_error(f"Error in {func_name}", str(e), type(e).__name__)
                    raise

        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Initialize memory
    memory = AgentMemory(agent_name="python-agent")

    # Store some initial context
    memory.store_context("project", "Python project with agent memory system", "high")

    # Store a decision
    memory.store_decision(
        "Use Python wrapper",
        "Easier integration with Python code",
        "agent_memory.py",
        "medium",
        "Direct bash calls, Subprocess wrapper"
    )

    # Store a pattern
    memory.store_pattern(
        "context_manager",
        """
class MemoryContext:
    def __enter__(self):
        # Setup
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup
        pass
        """,
        "Automatic resource management",
        "design",
        "python,resource,management"
    )

    # Generate a report
    report = memory.generate_report("detailed")
    print("Memory System Report:")
    print(report)

    # Health check
    health = memory.health_check()
    print("\nHealth Check:")
    print(health["output"])