# Agent Memory System v2.0

An advanced memory management system for AI coding agents that provides persistent, queryable memory across sessions with intelligent pattern recognition and project health monitoring.

## Features

### 🧠 Memory Types
- **Context**: Project events, architectural decisions, and environmental information
- **Decisions**: Coding decisions with reasoning, impact assessment, and alternatives
- **Codebase Knowledge**: File-specific insights, patterns, and anti-patterns
- **Errors**: Error patterns with solutions and prevention strategies
- **Patterns**: Reusable code patterns with templates and use cases

### 📊 Analytics & Monitoring
- Session tracking with detailed metadata
- Decision impact analysis
- Error pattern frequency tracking
- Pattern recommendation engine
- Project health checks
- Comprehensive reporting

### 🔄 Advanced Features
- Checkpoint/rollback system for safe experimentation
- Priority-based context storage
- Semantic pattern search
- Cross-session knowledge persistence
- AI-ready export formats

## Quick Start

1. **Initialize the memory system**:
```bash
./agent_memory.sh init
```

2. **Store your first decision**:
```bash
./agent_memory.sh store-decision "Use FastAPI" "Better async support and automatic docs" "main.py api.py" "high"
```

3. **Store an error pattern**:
```bash
./agent_memory.sh store-error "ImportError" "Missing dependency" "MODULE_NOT_FOUND" "" "Always check requirements.txt"
```

4. **Check project health**:
```bash
./agent_memory.sh health
```

## Command Reference

### Initialization
```bash
./agent_memory.sh init
```
Creates the memory structure in `.agent_memory/` directory with organized subdirectories for different memory types.

### Storing Memories

#### Context
```bash
./agent_memory.sh store-context <type> <content> [priority]
```
- `type`: Category (e.g., architecture, design, performance)
- `content`: The context information
- `priority`: low, normal, high, critical (default: normal)

Example:
```bash
./agent_memory.sh store-context "architecture" "Decided on microservices approach" "high"
```

#### Decisions
```bash
./agent_memory.sh store-decision <decision> <reasoning> <files> [impact] [alternatives]
```
- `decision`: What was decided
- `reasoning`: Why this decision was made
- `files`: Files affected by this decision
- `impact`: low, medium, high, critical (default: medium)
- `alternatives`: Other approaches considered

Example:
```bash
./agent_memory.sh store-decision "Use PostgreSQL" "ACID compliance needed for transactions" "models.py database.py" "high" "MongoDB, SQLite"
```

#### Codebase Knowledge
```bash
./agent_memory.sh store-codebase <file> <knowledge> [type] [confidence]
```
- `file`: Path to the file
- `knowledge`: What was learned about this file
- `type`: general, pattern, anti-pattern, optimization (default: general)
- `confidence`: low, medium, high (default: medium)

Example:
```bash
./agent_memory.sh store-codebase "auth.py" "Contains JWT token validation logic" "pattern" "high"
```

#### Errors
```bash
./agent_memory.sh store-error <error_type> <solution> [code] [stack] [prevention]
```
- `error_type`: Type of error
- `solution`: How to fix it
- `code`: Error code (optional)
- `stack`: Stack trace (optional)
- `prevention`: How to prevent in future (optional)

Example:
```bash
./agent_memory.sh store-error "TypeError" "Convert string to int using int()" "INVALID_TYPE" "line 42" "Validate input types"
```

#### Patterns
```bash
./agent_memory.sh store-pattern <name> <code> <use_case> [type] [tags]
```
- `name`: Pattern name
- `code`: Code template
- `use_case`: When to use this pattern
- `type`: design, algorithm, optimization, security (default: design)
- `tags`: Comma-separated tags for searchability

Example:
```bash
./agent_memory.sh store-pattern "singleton" "class Singleton:..." "Global state management" "design" "oop,state"
```

### Checkpoints
```bash
./agent_memory.sh checkpoint <description>
```
Creates a snapshot of the current project state for rollback.

Example:
```bash
./agent_memory.sh checkpoint "Before major refactor"
```

### Querying

#### Context
```bash
./agent_memory.sh query-context <type> [search_term] [priority]
```
Retrieve stored context with optional search and priority filtering.

#### Pattern Recommendations
```bash
./agent_memory.sh recommend <context> <task_type>
```
Get AI-powered pattern recommendations based on context and task.

Example:
```bash
./agent_memory.sh recommend "authentication" "user login system"
```

### Health & Reports

#### Health Check
```bash
./agent_memory.sh health
```
Provides a comprehensive health check of your project including:
- Uncommitted changes
- Error frequency analysis
- Recent activity monitoring

#### Generate Reports
```bash
./agent_memory.sh report [type] [output_file]
```
- `type`: summary (default), detailed, analytics
- `output_file`: Save report to file (optional)

Example:
```bash
./agent_memory.sh report detailed project_report.md
```

## Directory Structure

```
.agent_memory/
├── analytics/          # Usage statistics and metrics
│   ├── stats.json     # Overall statistics
│   ├── context_usage.log
│   ├── decision_impacts.log
│   └── error_frequency.log
├── checkpoints/        # Project state snapshots
├── codebase/          # File-specific knowledge
├── context/           # General context information
├── decisions/         # Decision logs
├── errors/           # Error patterns and solutions
├── knowledge/        # Daily knowledge dumps
├── patterns/         # Reusable patterns
│   └── index.json   # Pattern search index
└── sessions/         # Session tracking
```

## Environment Variables

- `AGENT_MEMORY_DIR`: Memory storage location (default: `./.agent_memory`)
- `AGENT_SESSION_ID`: Session identifier (default: timestamp)
- `AGENT_NAME`: Agent name (default: `claude`)

## Best Practices

1. **Regular Checkpoints**: Create checkpoints before major changes
   ```bash
   ./agent_memory.sh checkpoint "Before implementing feature X"
   ```

2. **Detailed Decisions**: Always include reasoning and alternatives
   ```bash
   ./agent_memory.sh store-decision "Use React" "Component-based architecture" "frontend/" "high" "Vue, Angular"
   ```

3. **Error Prevention**: Document how to prevent errors
   ```bash
   ./agent_memory.sh store-error "NullPointer" "Always check for null" "NPE" "" "Use Optional types"
   ```

4. **Pattern Tags**: Use descriptive tags for better searchability
   ```bash
   ./agent_memory.sh store-pattern "observer" "class Observer:..." "Event handling" "behavioral,pubsub,events"
   ```

5. **Regular Health Checks**: Monitor project health
   ```bash
   ./agent_memory.sh health
   ```

## Integration with AI

The memory system exports data in AI-friendly formats:

```bash
# Export all memory for AI consumption
./agent_memory.sh export

# Generate context for current session
./agent_memory.sh export context
```

The export format includes:
- Recent decisions with reasoning
- Known error patterns
- Available patterns
- Project context
- Session metadata

## Advanced Usage

### Custom Analytics
The system logs usage patterns that can be analyzed:
```bash
# Most used context types
awk -F':' '{print $2}' .agent_memory/analytics/context_usage.log | sort | uniq -c

# Decision impact distribution
awk -F':' '{print $2}' .agent_memory/analytics/decision_impacts.log | sort | uniq -c
```

### Pattern Search
Use the pattern index for efficient searching:
```bash
# Find all design patterns
jq 'to_entries[] | select(.value.type == "design") | .key' .agent_memory/patterns/index.json
```

### Rollback from Checkpoint
To restore from a checkpoint:
```bash
# List checkpoints
ls .agent_memory/checkpoints/

# Restore files from checkpoint (manual process)
cp -r .agent_memory/checkpoints/TIMESTAMP/* ./
```

## Troubleshooting

### Memory Not Initializing
- Check directory permissions
- Ensure `AGENT_MEMORY_DIR` is writable
- Verify bash is available

### Queries Not Working
- Check if memory has been initialized
- Verify file permissions in `.agent_memory/`
- Check for valid JSON format in stored data

### Large Memory Size
- Run cleanup to remove old sessions:
  ```bash
  ./agent_memory.sh cleanup 30  # Remove sessions older than 30 days
  ```
- Consider splitting projects into separate memory directories

## Contributing

To extend the memory system:
1. Add new memory types in the `init_memory()` function
2. Create corresponding storage functions
3. Update the query system
4. Add analytics tracking
5. Update documentation

## License

This memory system is part of the AI coding agent toolkit and follows the same license terms.