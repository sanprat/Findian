# Agent Memory System Integration Guide

This guide explains how the Agent Memory System is integrated into your project to automatically track all agent activities.

## Overview

The Agent Memory System provides persistent memory across agent sessions, enabling:
- Learning from past decisions and errors
- Reusing patterns and solutions
- Maintaining project context
- Automatic health monitoring

## Automatic Integration

### 1. Project-Level Auto-Initialization

When any agent works on this project, the memory system automatically initializes via:
- `__init__.py` - Auto-loads when project is imported
- `.claude_project_init.py` - Specifically for Claude agents

### 2. Task Lifecycle Tracking

The system automatically tracks:

#### Before Starting a Task
```python
from init_agent_memory import start_task
start_task("Your task description")
```

This:
- Creates a checkpoint
- Stores task context
- Shows relevant memories
- Recommends patterns

#### After Completing a Task
```python
from init_agent_memory import complete_task
complete_task(
    "Your task description",
    success=True,
    files_modified=["file1.py", "file2.py"],
    errors=[]
)
```

This:
- Stores completion status
- Records files modified
- Stores any errors encountered
- Updates session statistics

## Using the Memory System

### Direct Python API

```python
from agent_memory import AgentMemory

# Initialize
memory = AgentMemory()

# Store context
memory.store_context("architecture", "Using microservices pattern", "high")

# Store decisions
memory.store_decision(
    "Use PostgreSQL",
    "ACID compliance needed",
    "database.py",
    "high",
    "MongoDB, SQLite"
)

# Store patterns
memory.store_pattern(
    "singleton",
    "class Singleton:...",
    "Global state management",
    "design",
    "oop,state"
)

# Query context
context = memory.query_context("architecture", "microservices")

# Get recommendations
patterns = memory.recommend_patterns("authentication", "user login")
```

### Command Line Interface

```bash
# Initialize
./agent_memory.sh init

# Store data
./agent_memory.sh store-context "architecture" "Using microservices" "high"
./agent_memory.sh store-decision "Use PostgreSQL" "ACID needed" "db.py" "high"
./agent_memory.sh store-error "TypeError" "Convert using int()" "TYPE_ERROR"

# Query data
./agent_memory.sh query-context "architecture"
./agent_memory.sh recommend "authentication" "login"

# Health check
./agent_memory.sh health

# Generate reports
./agent_memory.sh summary report.md
```

## Agent Hooks

The project includes automatic hooks in `.agent_hooks/`:

### Pre-Task Hook
```bash
python .agent_hooks/pre_task.py "Task description"
```

### Post-Task Hook
```bash
python .agent_hooks/post_task.py "Task description" true '{"files": [], "errors": []}'
```

## Memory Storage Structure

```
.agent_memory/
├── analytics/          # Usage statistics
├── checkpoints/        # Project state snapshots
├── codebase/          # File-specific knowledge
├── context/           # General context
├── decisions/         # Decision logs
├── errors/           # Error patterns
├── knowledge/        # Daily knowledge dumps
├── patterns/         # Reusable patterns
└── sessions/         # Session tracking
```

## Best Practices for Agents

### 1. Before Starting Work
Always check existing memory:
```python
# Export memory context
memory.export_for_ai()

# Check recent decisions
decisions = memory.query_context("decisions")

# Look for error patterns
errors = memory.query_context("errors", "similar to your task")
```

### 2. During Development
- Store important decisions as they're made
- Document error solutions
- Save reusable patterns
- Create checkpoints before major changes

### 3. After Completing Work
- Store completion status
- Document any issues found
- Update knowledge about modified files

## Example Workflow

```python
# Agent starts work
memory = initialize_agent("agent-name")

# Check existing context
print("Recent project decisions:")
print(memory.query_context("decisions"))

# Start new task
start_task("Implement user authentication")

# During work - store decisions
memory.store_decision(
    "Use JWT for auth",
    "Stateless, good for APIs",
    "auth.py, middleware.py",
    "high"
)

# Store a pattern learned
memory.store_pattern(
    "middleware_auth",
    """
@app.middleware
async def auth_middleware(request):
    token = request.headers.get('Authorization')
    if not verify_token(token):
        raise HTTPException(401)
    """,
    "JWT authentication",
    "security",
    "auth,jwt,api"
)

# Complete task
complete_task(
    "Implement user authentication",
    success=True,
    files_modified=["auth.py", "middleware.py"],
    errors=[{
        "type": "ImportError",
        "solution": "Added jose package to requirements",
        "prevention": "Check imports before implementation"
    }]
)
```

## Health Monitoring

Regular health checks help maintain project quality:
```bash
./agent_memory.sh health
```

Checks for:
- Uncommitted changes
- High error frequency
- Stale code patterns
- Missing documentation

## Integration with IDEs

### VS Code
Add to `.vscode/tasks.json`:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Task with Memory",
            "type": "shell",
            "command": "python",
            "args": [".agent_hooks/pre_task.py", "${input:taskDescription}"]
        },
        {
            "label": "Complete Task with Memory",
            "type": "shell",
            "command": "python",
            "args": [".agent_hooks/post_task.py", "${input:taskDescription}", "true"]
        }
    ]
}
```

## Troubleshooting

### Memory Not Initializing
- Check directory permissions
- Ensure Python 3.7+ is available
- Verify bash is accessible

### Queries Not Working
- Initialize memory first: `./agent_memory.sh init`
- Check file permissions in `.agent_memory/`

### Large Memory Size
- Clean old sessions: `./agent_memory.sh cleanup 30`
- Exclude from git: add `.agent_memory/` to `.gitignore`

## Extending the System

To add new memory types:
1. Create storage function in `agent_memory.sh`
2. Add query function
3. Update Python wrapper in `agent_memory.py`
4. Update documentation

## Privacy Considerations

- Memory stored locally by default
- No data sent to external services
- Can be encrypted if needed
- Checkpoint files may contain sensitive code

Add `.agent_memory/` to `.gitignore` to keep memory local.