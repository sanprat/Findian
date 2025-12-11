#!/usr/bin/env python3
"""
Agent Memory Auto-Initializer
Automatically integrates memory system with any agent working on this project
"""

import os
import sys
import json
import datetime
from pathlib import Path
from agent_memory import AgentMemory


class ProjectMemoryIntegrator:
    """Integrates memory system with project and automates memory operations for agents"""

    def __init__(self, project_dir: str = None):
        self.project_dir = project_dir or os.getcwd()
        self.memory_dir = os.path.join(self.project_dir, ".agent_memory")
        self.memory = None
        self.agent_name = None

    def initialize_for_agent(self, agent_name: str = "claude"):
        """Initialize memory system for an agent"""
        self.agent_name = agent_name

        # Initialize memory
        self.memory = AgentMemory(
            memory_dir=self.memory_dir,
            agent_name=agent_name
        )

        # Store agent start context
        self.memory.store_context(
            "agent_session",
            f"Agent {agent_name} started session",
            "high"
        )

        # Capture project state
        self._capture_project_state()

        # Store project context
        self._store_project_context()

        print(f"✓ Memory system initialized for agent: {agent_name}")
        return self.memory

    def before_task(self, task_description: str):
        """Called before agent starts a task"""
        if not self.memory:
            self.initialize_for_agent()

        # Create checkpoint
        checkpoint_id = self.memory.create_checkpoint(f"Before task: {task_description}")

        # Store task start
        self.memory.store_context(
            "task_start",
            f"Starting task: {task_description}",
            "high"
        )

        # Query relevant memories
        relevant_context = self._query_relevant_context(task_description)
        if relevant_context:
            print("\n📚 Relevant memories from previous sessions:")
            for ctx in relevant_context:
                print(f"  • {ctx}")

        # Get pattern recommendations
        recommendations = self._get_task_patterns(task_description)
        if recommendations:
            print("\n🎯 Recommended patterns:")
            for rec in recommendations:
                print(f"  • {rec}")

        return checkpoint_id

    def after_task(self, task_description: str, success: bool = True,
                   files_modified: list = None, errors: list = None):
        """Called after agent completes a task"""
        if not self.memory:
            return

        # Store task completion
        status = "completed successfully" if success else "failed"
        self.memory.store_context(
            "task_complete",
            f"Task {task_description} {status}",
            "high" if success else "critical"
        )

        # Store files modified
        if files_modified:
            for file_path in files_modified:
                self.memory.store_codebase_knowledge(
                    file_path,
                    f"Modified during task: {task_description}",
                    "update",
                    "medium"
                )

        # Store errors if any
        if errors:
            for error in errors:
                self.memory.store_error(
                    error.get("type", "UnknownError"),
                    error.get("solution", "Solution not documented"),
                    error.get("code", ""),
                    error.get("stack", ""),
                    error.get("prevention", "")
                )

        # Update session stats
        self._update_session_stats(success)

        print(f"✓ Task completion stored in memory: {task_description}")

    def _capture_project_state(self):
        """Capture current project state"""
        # Project structure
        py_files = list(Path(self.project_dir).rglob("*.py"))
        js_files = list(Path(self.project_dir).rglob("*.js"))
        other_files = list(Path(self.project_dir).rglob("*.*"))

        self.memory.store_context(
            "project_structure",
            f"Python files: {len(py_files)}, JavaScript files: {len(js_files)}, Total files: {len(other_files)}",
            "normal"
        )

        # Git status if available
        if os.path.exists(os.path.join(self.project_dir, ".git")):
            import subprocess
            try:
                git_status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                ).stdout
                if git_status:
                    self.memory.store_context(
                        "git_status",
                        f"Uncommitted changes: {len(git_status.splitlines())}",
                        "normal"
                    )
            except:
                pass

        # Dependencies
        if os.path.exists(os.path.join(self.project_dir, "requirements.txt")):
            with open(os.path.join(self.project_dir, "requirements.txt")) as f:
                deps = len([l for l in f if l.strip() and not l.startswith("#")])
                self.memory.store_context(
                    "dependencies",
                    f"Python dependencies: {deps}",
                    "normal"
                )

    def _store_project_context(self):
        """Store project-specific context"""
        # Look for README or project description
        for readme in ["README.md", "README.txt", "README"]:
            readme_path = os.path.join(self.project_dir, readme)
            if os.path.exists(readme_path):
                with open(readme_path) as f:
                    first_line = f.readline().strip()
                    self.memory.store_context(
                        "project_description",
                        first_line,
                        "high"
                    )
                break

        # Store project name
        project_name = os.path.basename(self.project_dir)
        self.memory.store_context(
            "project_name",
            project_name,
            "high"
        )

    def _query_relevant_context(self, task_description: str) -> list:
        """Query context relevant to the task"""
        relevant = []

        # Extract keywords from task description
        keywords = task_description.lower().split()

        # Query different context types
        for context_type in ["decisions", "errors", "architecture", "patterns"]:
            # This would need to be implemented in the memory system
            # For now, return empty
            pass

        return relevant

    def _get_task_patterns(self, task_description: str) -> list:
        """Get pattern recommendations for the task"""
        # Simple keyword-based recommendations
        recommendations = []

        task_lower = task_description.lower()

        if any(word in task_lower for word in ["test", "testing"]):
            recommendations.append("Test-driven development patterns")
        if any(word in task_lower for word in ["api", "endpoint"]):
            recommendations.append("REST API design patterns")
        if any(word in task_lower for word in ["database", "db"]):
            recommendations.append("Database access patterns")
        if any(word in task_lower for word in ["error", "exception"]):
            recommendations.append("Error handling patterns")

        return recommendations

    def _update_session_stats(self, success: bool):
        """Update session statistics"""
        session_file = os.path.join(self.memory_dir, "sessions", "current.json")
        if os.path.exists(session_file):
            with open(session_file, 'r+') as f:
                session = json.load(f)
                if "tasks_completed" not in session:
                    session["tasks_completed"] = 0
                session["tasks_completed"] += 1

                if success:
                    if "successful_tasks" not in session:
                        session["successful_tasks"] = 0
                    session["successful_tasks"] += 1

                f.seek(0)
                json.dump(session, f, indent=2)
                f.truncate()


# Global instance for project
_project_integrator = None


def get_project_integrator():
    """Get or create project integrator instance"""
    global _project_integrator
    if _project_integrator is None:
        _project_integrator = ProjectMemoryIntegrator()
    return _project_integrator


def initialize_agent(agent_name: str = "claude"):
    """Initialize memory system for current agent"""
    integrator = get_project_integrator()
    return integrator.initialize_for_agent(agent_name)


def start_task(task_description: str):
    """Call before starting a task"""
    integrator = get_project_integrator()
    return integrator.before_task(task_description)


def complete_task(task_description: str, success: bool = True,
                 files_modified: list = None, errors: list = None):
    """Call after completing a task"""
    integrator = get_project_integrator()
    integrator.after_task(task_description, success, files_modified, errors)


# Auto-initialization script for agents
def create_agent_hooks():
    """Create hook scripts for automatic memory integration"""
    hooks_dir = os.path.join(os.getcwd(), ".agent_hooks")
    os.makedirs(hooks_dir, exist_ok=True)

    # Create pre-task hook
    pre_task_hook = f"""#!/usr/bin/env python3
import sys
sys.path.insert(0, '{os.getcwd()}')
from init_agent_memory import start_task

task_description = sys.argv[1] if len(sys.argv) > 1 else "Unnamed task"
start_task(task_description)
"""

    with open(os.path.join(hooks_dir, "pre_task.py"), 'w') as f:
        f.write(pre_task_hook)

    # Create post-task hook
    post_task_hook = f"""#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, '{os.getcwd()}')
from init_agent_memory import complete_task

task_description = sys.argv[1] if len(sys.argv) > 1 else "Unnamed task"
success = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True

# Parse optional JSON for files and errors
files_modified = []
errors = []
if len(sys.argv) > 3:
    try:
        data = json.loads(sys.argv[3])
        files_modified = data.get('files', [])
        errors = data.get('errors', [])
    except:
        pass

complete_task(task_description, success, files_modified, errors)
"""

    with open(os.path.join(hooks_dir, "post_task.py"), 'w') as f:
        f.write(post_task_hook)

    # Make hooks executable
    os.chmod(os.path.join(hooks_dir, "pre_task.py"), 0o755)
    os.chmod(os.path.join(hooks_dir, "post_task.py"), 0o755)

    print(f"✓ Agent hooks created in {hooks_dir}")
    print("\nUsage:")
    print(f"  python .agent_hooks/pre_task.py 'Your task description'")
    print(f"  python .agent_hooks/post_task.py 'Your task description' true '{{\"files\": [\"file1.py\"], \"errors\": []}}'")


if __name__ == "__main__":
    # Check if running as hook
    if len(sys.argv) > 1 and sys.argv[1] == "--create-hooks":
        create_agent_hooks()
    else:
        # Initialize for direct usage
        agent = initialize_agent()
        print(f"\nMemory system ready for agent!")
        print(f"Memory directory: {agent.memory_dir}")
        print(f"Session ID: {agent.session_id}")

        # Show recent context
        print("\nRecent project context:")
        context = agent.query_context("project")
        for ctx in context[-3:]:
            print(f"  • {ctx}")