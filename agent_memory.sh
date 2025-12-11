#!/bin/bash

# Agentic Coding Agent Memory System v2.0
# Enhanced memory management system for AI coding agents

# Environment Configuration
MEMORY_DIR="${AGENT_MEMORY_DIR:-$PWD/.agent_memory}"
SESSION_ID="${AGENT_SESSION_ID:-$(date +%s)}"
PROJECT_NAME="$(basename "$PWD")"
AGENT_NAME="${AGENT_NAME:-claude}"

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize memory structure with enhanced organization
init_memory() {
    local session_info="$MEMORY_DIR/sessions/current.json"

    mkdir -p "$MEMORY_DIR"/context
    mkdir -p "$MEMORY_DIR"/decisions
    mkdir -p "$MEMORY_DIR"/codebase
    mkdir -p "$MEMORY_DIR"/errors
    mkdir -p "$MEMORY_DIR"/patterns
    mkdir -p "$MEMORY_DIR"/sessions
    mkdir -p "$MEMORY_DIR"/knowledge
    mkdir -p "$MEMORY_DIR"/analytics
    mkdir -p "$MEMORY_DIR"/checkpoints

    # Enhanced session tracking
    echo "{\n  \"session_id\": \"$SESSION_ID\"," > "$session_info"
    echo "  \"agent_name\": \"$AGENT_NAME\"," >> "$session_info"
    echo "  \"project_name\": \"$PROJECT_NAME\"," >> "$session_info"
    echo "  \"started_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$session_info"
    echo "  \"project_dir\": \"$(pwd)\"," >> "$session_info"

    # Git info
    local git_branch="none"
    local git_commit="unknown"
    if command -v git >/dev/null 2>&1; then
        git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "none")
        git_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    fi
    echo "  \"git_branch\": \"$git_branch\"," >> "$session_info"
    echo "  \"git_commit\": \"$git_commit\"," >> "$session_info"

    # Environment info
    echo "  \"environment\": {" >> "$session_info"
    echo "    \"python_version\": \"$(python3 --version 2>/dev/null || echo 'N/A')\"," >> "$session_info"
    echo "    \"node_version\": \"$(node --version 2>/dev/null || echo 'N/A')\"," >> "$session_info"
    echo "    \"os\": \"$(uname -s)\"," >> "$session_info"
    echo "    \"shell\": \"$SHELL\"" >> "$session_info"
    echo "  }," >> "$session_info"
    echo "  \"events\": []," >> "$session_info"
    echo "  \"tasks_completed\": 0," >> "$session_info"
    echo "  \"files_modified\": []," >> "$session_info"
    echo "  \"errors_encountered\": 0," >> "$session_info"
    echo "  \"patterns_learned\": 0" >> "$session_info"
    echo "}" >> "$session_info"

    # Create analytics structure
    local analytics_file="$MEMORY_DIR/analytics/stats.json"
    echo "{\n  \"total_sessions\": 1," > "$analytics_file"
    echo "  \"total_decisions\": 0," >> "$analytics_file"
    echo "  \"total_errors\": 0," >> "$analytics_file"
    echo "  \"total_patterns\": 0," >> "$analytics_file"
    echo "  \"files_analyzed\": 0," >> "$analytics_file"
    echo "  \"most_common_errors\": {}," >> "$analytics_file"
    echo "  \"project_progress\": {" >> "$analytics_file"
    echo "    \"phase\": \"initialization\"," >> "$analytics_file"
    echo "    \"completion_percentage\": 0" >> "$analytics_file"
    echo "  }" >> "$analytics_file"
    echo "}" >> "$analytics_file"

    echo -e "${GREEN}✓${NC} Memory initialized: $MEMORY_DIR"
    echo -e "${BLUE}Session ID:${NC} $SESSION_ID"
}

# Enhanced context storage with categorization
store_context() {
    local context_type="$1"
    local content="$2"
    local priority="${3:-normal}"  # low, normal, high, critical

    local ctx_file="$MEMORY_DIR/context/${context_type}.txt"
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Add priority indicator
    local priority_icon=""
    case "$priority" in
        "critical") priority_icon="🔴 " ;;
        "high") priority_icon="🟡 " ;;
        "normal") priority_icon="🟢 " ;;
        "low") priority_icon="⚪ " ;;
    esac

    echo "[$timestamp] [$priority] $priority_icon$content" >> "$ctx_file"

    # Keep entries based on priority
    local max_entries=50
    case "$priority" in
        "critical"|"high") max_entries=100 ;;
        "normal") max_entries=50 ;;
        "low") max_entries=20 ;;
    esac

    tail -n "$max_entries" "$ctx_file" > "$ctx_file.tmp" && mv "$ctx_file.tmp" "$ctx_file"

    # Update analytics
    echo "$(date +%s):$context_type" >> "$MEMORY_DIR/analytics/context_usage.log"
}

# Enhanced decision storage with impact tracking
store_decision() {
    local decision="$1"
    local reasoning="$2"
    local files_affected="$3"
    local impact="${4:-medium}"  # low, medium, high, critical
    local alternatives="${5:-}"  # Alternative approaches considered

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local decision_id=$(echo "$decision$timestamp" | sha256sum | cut -c1-8)

    echo "{" >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"id\": \"$decision_id\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"timestamp\": \"$timestamp\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"decision\": \"$decision\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"reasoning\": \"$reasoning\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"files_affected\": \"$files_affected\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"impact\": \"$impact\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"alternatives\": \"$alternatives\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"session\": \"$SESSION_ID\"," >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "  \"outcome\": \"pending\"" >> "$MEMORY_DIR/decisions/decisions.jsonl"
    echo "}" >> "$MEMORY_DIR/decisions/decisions.jsonl"

    # Update analytics
    echo "$(date +%s):$impact" >> "$MEMORY_DIR/analytics/decision_impacts.log"
}

# Enhanced codebase knowledge with semantic understanding
store_codebase_knowledge() {
    local file_path="$1"
    local knowledge="$2"
    local knowledge_type="${3:-general}"  # general, pattern, anti-pattern, optimization
    local confidence="${4:-medium}"  # low, medium, high

    local safe_path=$(echo "$file_path" | sed 's/[^a-zA-Z0-9._-]/_/g')
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    echo "[$timestamp] [$knowledge_type] [$confidence]" >> "$MEMORY_DIR/codebase/${safe_path}.txt"
    echo "$knowledge" >> "$MEMORY_DIR/codebase/${safe_path}.txt"
    echo "" >> "$MEMORY_DIR/codebase/${safe_path}.txt"
    echo "---" >> "$MEMORY_DIR/codebase/${safe_path}.txt"

    # Store in knowledge graph
    local knowledge_entry="$MEMORY_DIR/knowledge/$(date +%Y-%m-%d).jsonl"
    echo "{" >> "$knowledge_entry"
    echo "  \"timestamp\": \"$timestamp\"," >> "$knowledge_entry"
    echo "  \"file_path\": \"$file_path\"," >> "$knowledge_entry"
    echo "  \"knowledge\": \"$knowledge\"," >> "$knowledge_entry"
    echo "  \"type\": \"$knowledge_type\"," >> "$knowledge_entry"
    echo "  \"confidence\": \"$confidence\"," >> "$knowledge_entry"
    echo "  \"session\": \"$SESSION_ID\"" >> "$knowledge_entry"
    echo "}" >> "$knowledge_entry"

    # Update files analyzed count
    local stats_file="$MEMORY_DIR/analytics/stats.json"
    if [ -f "$stats_file" ]; then
        # Simple increment without jq
        echo "Files analyzed: $(ls "$MEMORY_DIR/codebase"/*.txt 2>/dev/null | wc -l)" > "$MEMORY_DIR/analytics/files_count.txt"
    fi
}

# Enhanced error storage with resolution tracking
store_error() {
    local error_type="$1"
    local solution="$2"
    local error_code="${3:-}"
    local stack_trace="${4:-}"
    local prevention="${5:-}"  # How to prevent in future

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local error_id=$(echo "$error_type$timestamp" | sha256sum | cut -c1-8)

    echo "{" >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"id\": \"$error_id\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"timestamp\": \"$timestamp\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"error_type\": \"$error_type\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"error_code\": \"$error_code\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"solution\": \"$solution\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"stack_trace\": \"$stack_trace\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"prevention\": \"$prevention\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"session\": \"$SESSION_ID\"," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"resolved\": true," >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "  \"occurrence_count\": 1" >> "$MEMORY_DIR/errors/errors.jsonl"
    echo "}" >> "$MEMORY_DIR/errors/errors.jsonl"

    # Update error frequency
    echo "$(date +%s):$error_type" >> "$MEMORY_DIR/analytics/error_frequency.log"
}

# Enhanced pattern storage with template support
store_pattern() {
    local pattern_name="$1"
    local pattern_code="$2"
    local use_case="$3"
    local pattern_type="${4:-design}"  # design, algorithm, optimization, security
    local tags="${5:-}"  # Comma-separated tags

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    echo "# $pattern_name" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "**Type:** $pattern_type" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "**Use Case:** $use_case" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "**Tags:** $tags" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "**Added:** $timestamp" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo '```' >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "$pattern_code" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo '```' >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "## Usage Notes" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "<!-- Add usage notes here -->" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "## Variations" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "<!-- Document variations here -->" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "" >> "$MEMORY_DIR/patterns/${pattern_name}.md"
    echo "---" >> "$MEMORY_DIR/patterns/${pattern_name}.md"

    # Create pattern index
    local index_file="$MEMORY_DIR/patterns/index.json"
    if [ -f "$index_file" ]; then
        echo ",\"$pattern_name\": {\"type\": \"$pattern_type\", \"tags\": \"$tags\", \"added\": \"$timestamp\"}" >> "$index_file.tmp"
        sed '$s/^//' "$index_file" >> "$index_file.tmp"
        sed '$s/,$//' "$index_file.tmp" > "$index_file" && rm "$index_file.tmp"
    else
        echo "{\"$pattern_name\": {\"type\": \"$pattern_type\", \"tags\": \"$tags\", \"added\": \"$timestamp\"}}" > "$index_file"
    fi
}

# Create checkpoint for rollback
create_checkpoint() {
    local description="$1"
    local checkpoint_id=$(date +%s)
    local checkpoint_dir="$MEMORY_DIR/checkpoints/$checkpoint_id"

    mkdir -p "$checkpoint_dir"

    # Save current state
    {
        echo "description: $description"
        echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "session_id: $SESSION_ID"
        echo "git_commit: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
        echo "git_status: $(git status --porcelain 2>/dev/null || echo 'not a git repo')"
    } > "$checkpoint_dir/meta.json"

    # Store file snapshots
    if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
        git ls-files > "$checkpoint_dir/files.txt"
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                mkdir -p "$checkpoint_dir/$(dirname "$file")"
                cp "$file" "$checkpoint_dir/$file" 2>/dev/null
            fi
        done < "$checkpoint_dir/files.txt"
    fi

    echo -e "${GREEN}✓${NC} Checkpoint created: $checkpoint_id"
    echo "$checkpoint_id"
}

# Enhanced querying with semantic search
query_context() {
    local context_type="$1"
    local search_term="${2:-}"
    local priority_filter="${3:-}"

    local ctx_file="$MEMORY_DIR/context/${context_type}.txt"

    if [ -f "$ctx_file" ]; then
        if [ -n "$search_term" ]; then
            if [ -n "$priority_filter" ]; then
                grep -i "\[$priority_filter\]" "$ctx_file" | grep -i "$search_term" | tail -n 10
            else
                grep -i "$search_term" "$ctx_file" | tail -n 10
            fi
        else
            if [ -n "$priority_filter" ]; then
                grep -i "\[$priority_filter\]" "$ctx_file" | tail -n 10
            else
                tail -n 10 "$ctx_file"
            fi
        fi
    fi
}

# Smart pattern recommendation
recommend_patterns() {
    local context="$1"
    local task_type="$2"

    echo -e "${BLUE}Recommended patterns for: $task_type${NC}"
    echo

    # Search patterns by tags and use case
    for pattern_file in "$MEMORY_DIR/patterns"/*.md; do
        if [ -f "$pattern_file" ]; then
            local pattern_name=$(basename "$pattern_file" .md)
            if grep -q -i "$task_type\|$context" "$pattern_file"; then
                echo -e "${GREEN}→${NC} $pattern_name"
                grep -A 1 "Use Case:" "$pattern_file" | tail -n 1
                echo
            fi
        fi
    done
}

# Project health check
health_check() {
    echo -e "${BLUE}=== Project Health Check ===${NC}"
    echo

    # Check for common issues
    local issues=0

    # Check for uncommitted changes
    if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
        if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
            echo -e "${YELLOW}⚠${NC} Uncommitted changes detected"
            ((issues++))
        fi
    fi

    # Check for error patterns
    local error_count=$(wc -l < "$MEMORY_DIR/errors/errors.jsonl" 2>/dev/null || echo "0")
    if [ "$error_count" -gt 5 ]; then
        echo -e "${YELLOW}⚠${NC} High error count: $error_count"
        ((issues++))
    fi

    # Check for recent activity
    local last_activity=0
    for log in "$MEMORY_DIR/sessions/current.json" "$MEMORY_DIR/decisions/decisions.jsonl" "$MEMORY_DIR/errors/errors.jsonl"; do
        if [ -f "$log" ]; then
            local file_time=$(stat -f %m "$log" 2>/dev/null || stat -c %Y "$log" 2>/dev/null || echo "0")
            if [ "$file_time" -gt "$last_activity" ]; then
                last_activity="$file_time"
            fi
        fi
    done

    local time_diff=$(($(date +%s) - last_activity))
    if [ "$time_diff" -gt 3600 ]; then  # 1 hour
        echo -e "${YELLOW}⚠${NC} No recent activity (last: $((time_diff / 60)) minutes ago)"
        ((issues++))
    fi

    if [ "$issues" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Project is healthy"
    else
        echo -e "${RED}✗${NC} Found $issues potential issues"
    fi

    echo
}

# Generate comprehensive report
generate_summary_report() {
    local output_file="$1"
    local report_content="=== Agent Memory Summary Report ===
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Project: $PROJECT_NAME
Session: $SESSION_ID
Agent: $AGENT_NAME

## Quick Stats
- Total Sessions: 1
- Decisions Made: $(wc -l < "$MEMORY_DIR/decisions/decisions.jsonl" 2>/dev/null || echo "0")
- Errors Encountered: $(wc -l < "$MEMORY_DIR/errors/errors.jsonl" 2>/dev/null || echo "0")
- Patterns Learned: $(ls "$MEMORY_DIR/patterns/" 2>/dev/null | wc -l)
- Files Analyzed: $(ls "$MEMORY_DIR/codebase/" 2>/dev/null | wc -l)

## Recent Activity
$(tail -n 5 "$MEMORY_DIR/sessions/current.json" 2>/dev/null | grep -o '"description":"[^"]*"' | sed 's/"description":"/- /' | sed 's/"$//' || echo "No recent activity")

## Top Error Patterns
$(awk -F':' '{print $3}' "$MEMORY_DIR/analytics/error_frequency.log" 2>/dev/null | sort | uniq -c | sort -nr | head -3 | awk '{print "- " $2 " (" $1 " times)"}' || echo "No errors recorded")

## Recent Decisions
$(tail -n 3 "$MEMORY_DIR/decisions/decisions.jsonl" 2>/dev/null | grep '"decision":' | sed 's/.*"decision": *"//' | sed 's/".*//' | sed 's/^/- /' || echo "No decisions yet")
"

    if [ -n "$output_file" ]; then
        echo "$report_content" > "$output_file"
        echo -e "${GREEN}✓${NC} Report saved to: $output_file"
    else
        echo "$report_content"
    fi
}

# Export memory for AI consumption
export_for_ai() {
    echo "# Agent Memory Export"
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Session: $SESSION_ID"
    echo ""

    echo "## Project Context"
    echo "Project: $PROJECT_NAME"
    echo "Agent: $AGENT_NAME"
    echo ""

    echo "## Recent Decisions (Last 5)"
    tail -n 5 "$MEMORY_DIR/decisions/decisions.jsonl" 2>/dev/null | grep '"decision":' | sed 's/.*"decision": *"//' | sed 's/".*//' | sed 's/^/- /' || echo "No decisions"
    echo ""

    echo "## Known Error Patterns (Last 5)"
    tail -n 5 "$MEMORY_DIR/errors/errors.jsonl" 2>/dev/null | grep '"error_type":' | sed 's/.*"error_type": *"//' | sed 's/".*//' | sed 's/^/- /' || echo "No errors"
    echo ""

    echo "## Available Patterns"
    ls "$MEMORY_DIR/patterns/" 2>/dev/null | sed 's/.md$//' | sed 's/^/- /' || echo "No patterns"
    echo ""

    echo "## Context Summary"
    echo "Files analyzed: $(ls "$MEMORY_DIR/codebase/" 2>/dev/null | wc -l)"
    echo "Decisions made: $(wc -l < "$MEMORY_DIR/decisions/decisions.jsonl" 2>/dev/null || echo "0")"
    echo "Errors recorded: $(wc -l < "$MEMORY_DIR/errors/errors.jsonl" 2>/dev/null || echo "0")"
}

# Main command dispatcher
case "${1:-}" in
    init)
        init_memory
        ;;
    store-context)
        store_context "$2" "$3" "$4"
        ;;
    store-decision)
        store_decision "$2" "$3" "$4" "$5" "$6"
        ;;
    store-codebase)
        store_codebase_knowledge "$2" "$3" "$4" "$5"
        ;;
    store-error)
        store_error "$2" "$3" "$4" "$5" "$6"
        ;;
    store-pattern)
        store_pattern "$2" "$3" "$4" "$5" "$6"
        ;;
    checkpoint)
        create_checkpoint "$2"
        ;;
    query-context)
        query_context "$2" "$3" "$4"
        ;;
    recommend)
        recommend_patterns "$2" "$3"
        ;;
    health)
        health_check
        ;;
    summary)
        generate_summary_report "$2"
        ;;
    export)
        export_for_ai
        ;;
    *)
        cat <<EOF
${BLUE}Agent Memory System v2.0${NC}

Usage:
  $0 init                                    Initialize memory system
  $0 store-context <type> <content> [priority]
  $0 store-decision <decision> <reasoning> <files> [impact] [alternatives]
  $0 store-codebase <file> <knowledge> [type] [confidence]
  $0 store-error <error> <solution> [code] [stack] [prevention]
  $0 store-pattern <name> <code> <use_case> [type] [tags]
  $0 checkpoint <description>                Create rollback checkpoint
  $0 query-context <type> [search] [priority]
  $0 recommend <context> <task_type>         Recommend patterns
  $0 health                                  Project health check
  $0 summary [output_file]                   Generate summary report
  $0 export                                  Export for AI consumption

Environment Variables:
  AGENT_MEMORY_DIR    Memory location (default: ./.agent_memory)
  AGENT_SESSION_ID    Session ID (default: timestamp)
  AGENT_NAME          Agent name (default: claude)
EOF
        ;;
esac