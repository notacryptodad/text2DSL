# Text2DSL User Scenarios & Workflows

## Overview

This document outlines the key user scenarios and workflows for the Text2DSL system, covering administration, schema management, query generation, and quality control.

---

## Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **Super Admin** | Platform administrator | Create workspaces, manage workspace admins |
| **Workspace Admin** | Workspace owner/manager | Configure providers, connections, schema refresh |
| **Expert** | Schema/Query specialist | Review queue, schema annotation, approve/reject examples |
| **User** | End user | Submit queries, select provider/connection, provide feedback |

---

## Scenario 1: Workspace & Admin Setup

### 1.1 Super Admin Creates Workspace Admin

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Super Admin   │         │     System      │         │ Workspace Admin │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. Create Workspace      │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  2. Assign Workspace Admin│                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │                           │  3. Send Invitation       │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  4. Admin Accepts         │
         │                           │◄──────────────────────────│
         │                           │                           │
```

**API Endpoints:**
- `POST /api/v1/admin/workspaces` - Create workspace
- `POST /api/v1/admin/workspaces/{id}/admins` - Assign workspace admin
- `GET /api/v1/admin/workspaces` - List all workspaces (super admin only)

**Data Model:**
```python
class WorkspaceAdmin:
    workspace_id: UUID
    user_id: str
    role: AdminRole  # owner, admin, member
    invited_by: str
    invited_at: datetime
    accepted_at: Optional[datetime]
```

### 1.2 Workspace Admin Configures Provider/Connection

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Workspace Admin │         │     System      │         │   Target DB     │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. Create Provider       │                           │
         │  (type: postgresql)       │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  2. Add Connection        │                           │
         │  (host, port, creds)      │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  3. Test Connection       │                           │
         │──────────────────────────►│  4. Connect & Verify      │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  5. Connection OK         │
         │                           │◄──────────────────────────│
         │                           │                           │
         │  6. Trigger Schema Refresh│                           │
         │──────────────────────────►│  7. Introspect Schema     │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  8. Schema Metadata       │
         │                           │◄──────────────────────────│
         │                           │                           │
         │  9. Schema Cached (Redis) │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
```

**API Endpoints:**
- `POST /api/v1/workspaces/{ws_id}/providers` - Create provider
- `POST /api/v1/workspaces/{ws_id}/providers/{prov_id}/connections` - Add connection
- `POST /api/v1/workspaces/{ws_id}/providers/{prov_id}/connections/{conn_id}/test` - Test connection
- `POST /api/v1/workspaces/{ws_id}/providers/{prov_id}/connections/{conn_id}/schema/refresh` - Refresh schema

---

## Scenario 2: Expert Schema Review & Auto-Annotation

### 2.1 Expert Reviews Schema with LLM Assistance

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│     Expert      │         │  Annotation     │         │      LLM        │
│                 │         │    Agent        │         │   (Claude)      │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. View Schema Tables    │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  2. "Auto-annotate the    │                           │
         │   orders table"           │                           │
         │──────────────────────────►│                           │
         │                           │  3. Analyze schema +      │
         │                           │     generate annotations  │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  4. Suggested annotations │
         │                           │◄──────────────────────────│
         │                           │                           │
         │  5. Show suggestions      │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
         │  6. "What does the        │                           │
         │   status column mean?"    │                           │
         │──────────────────────────►│  7. Query with context    │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  8. Use tool: sample_data │
         │                           │◄──────────────────────────│
         │                           │                           │
         │                           │  9. Execute tool          │
         │                           │──────────────────────────►│
         │                           │                           │
         │  10. "status has values:  │                           │
         │   pending, shipped..."    │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
         │  11. Approve & Save       │                           │
         │──────────────────────────►│                           │
         │                           │                           │
```

**Multi-Turn Conversation Support:**
- Maintain conversation context for schema discussion
- Expert can ask follow-up questions
- LLM can request clarification

**Tool Use for Annotation Agent:**
```python
ANNOTATION_TOOLS = [
    {
        "name": "sample_data",
        "description": "Get sample values from a column",
        "parameters": {
            "table": str,
            "column": str,
            "limit": int
        }
    },
    {
        "name": "column_stats",
        "description": "Get statistics for a column (min, max, distinct count)",
        "parameters": {
            "table": str,
            "column": str
        }
    },
    {
        "name": "find_relationships",
        "description": "Find foreign key relationships for a table",
        "parameters": {
            "table": str
        }
    },
    {
        "name": "search_similar_tables",
        "description": "Find tables with similar column names",
        "parameters": {
            "column_pattern": str
        }
    },
    {
        "name": "save_annotation",
        "description": "Save an annotation for a table or column",
        "parameters": {
            "target_type": str,  # "table" or "column"
            "target_name": str,
            "description": str,
            "business_terms": list[str],
            "enum_values": list[str]  # optional
        }
    }
]
```

**API Endpoints:**
- `GET /api/v1/workspaces/{ws_id}/connections/{conn_id}/schema` - Get schema
- `POST /api/v1/workspaces/{ws_id}/connections/{conn_id}/schema/auto-annotate` - Trigger auto-annotation
- `POST /api/v1/workspaces/{ws_id}/annotations/chat` - Multi-turn annotation chat
- `GET /api/v1/workspaces/{ws_id}/annotations` - List annotations
- `PUT /api/v1/workspaces/{ws_id}/annotations/{id}` - Update annotation

---

## Scenario 3: User Query Generation (Agentic Loop)

### 3.1 User Submits Query → Agentic DSL Generation

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│      User       │         │   Orchestrator  │         │     Agents      │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. Select Provider &     │                           │
         │     Connection            │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  2. "Show me top 10       │                           │
         │   customers by revenue"   │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │                           │  3. Dispatch to agents    │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │     ┌──────────────────┐  │
         │                           │     │ Schema Agent     │  │
         │                           │     │ - Get schema     │  │
         │                           │     │ - Get annotations│  │
         │                           │     └──────────────────┘  │
         │                           │            ↓              │
         │                           │     ┌──────────────────┐  │
         │                           │     │ RAG Agent        │  │
         │                           │     │ - Find examples  │  │
         │                           │     └──────────────────┘  │
         │                           │            ↓              │
         │                           │     ┌──────────────────┐  │
         │                           │     │ Query Builder    │  │
         │                           │     │ - Generate DSL   │  │
         │                           │     │ - Confidence: 0.9│  │
         │                           │     └──────────────────┘  │
         │                           │            ↓              │
         │                           │     ┌──────────────────┐  │
         │                           │     │ Validator Agent  │  │
         │                           │     │ - Syntax check   │  │
         │                           │     │ - Execute test   │  │
         │                           │     └──────────────────┘  │
         │                           │                           │
         │  4. Generated Query:      │                           │
         │  SELECT c.name, SUM(...)  │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
```

### 3.2 Handling Vague Queries (Clarification Flow)

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│      User       │         │   Orchestrator  │         │  Query Builder  │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. "Show me the data"    │                           │
         │──────────────────────────►│                           │
         │                           │  2. Generate query        │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  3. Low confidence (0.4)  │
         │                           │     Ambiguous query       │
         │                           │◄──────────────────────────│
         │                           │                           │
         │  4. Clarification needed: │                           │
         │  "Which table? orders,    │                           │
         │   customers, or products?"│                           │
         │◄──────────────────────────│                           │
         │                           │                           │
         │  5. "customers table"     │                           │
         │──────────────────────────►│                           │
         │                           │  6. Retry with context    │
         │                           │──────────────────────────►│
         │                           │                           │
         │                           │  7. High confidence (0.95)│
         │                           │◄──────────────────────────│
         │                           │                           │
         │  8. SELECT * FROM         │                           │
         │     customers LIMIT 100   │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
```

**Agentic Loop Termination Criteria:**
```python
def should_terminate(result: QueryResult) -> bool:
    return (
        # Success: high confidence + validation passed
        (result.confidence_score >= 0.85 and result.validation_passed)
        # Or: max iterations reached
        or result.iteration_count >= MAX_ITERATIONS
        # Or: user provided clarification and new attempt succeeded
        or (result.clarification_resolved and result.validation_passed)
    )

def should_ask_clarification(result: QueryResult) -> bool:
    return (
        result.confidence_score < 0.6
        and result.iteration_count < MAX_ITERATIONS
        and not result.validation_passed
    )
```

**API Endpoints:**
- `POST /api/v1/query` - Submit query (main endpoint)
- `POST /api/v1/conversations/{conv_id}/turns` - Continue conversation
- `GET /api/v1/conversations/{conv_id}` - Get conversation history

---

## Scenario 4: Expert Review Queue

### 4.1 Expert Reviews Good/Bad Cases

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│     Expert      │         │  Review System  │         │   RAG Store     │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. Get Review Queue      │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  2. Queue Items:          │                           │
         │  - Low confidence queries │                           │
         │  - Validation failures    │                           │
         │  - Negative feedback      │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
         │  3. Review Item #1        │                           │
         │  NL: "monthly revenue"    │                           │
         │  SQL: SELECT SUM(...)     │                           │
         │──────────────────────────►│                           │
         │                           │                           │
         │  4a. APPROVE              │                           │
         │  (mark as good example)   │                           │
         │──────────────────────────►│  5a. Index in RAG         │
         │                           │──────────────────────────►│
         │                           │                           │
         │  4b. REJECT               │                           │
         │  (mark as bad example)    │                           │
         │──────────────────────────►│  5b. Index as negative    │
         │                           │──────────────────────────►│
         │                           │                           │
         │  4c. CORRECT & APPROVE    │                           │
         │  (fix query, then approve)│                           │
         │──────────────────────────►│  5c. Index corrected      │
         │                           │──────────────────────────►│
         │                           │                           │
```

**Review Queue Triggers:**
1. **Low Confidence** - Queries with confidence < 0.7
2. **Validation Failure** - Queries that failed execution
3. **User Thumbs Down** - Negative user feedback
4. **Clarification Required** - Queries needing multiple clarifications

**API Endpoints:**
- `GET /api/v1/review/queue` - Get pending reviews
- `GET /api/v1/review/queue?status=pending&provider_id=xxx` - Filter queue
- `PUT /api/v1/review/queue/{id}` - Submit review decision
- `GET /api/v1/review/stats` - Review statistics

**Review Decision Model:**
```python
class ReviewDecision(str, Enum):
    APPROVE = "approve"           # Good example, add to RAG
    REJECT = "reject"             # Bad example, add as negative
    CORRECT = "correct"           # Fix and approve
    SKIP = "skip"                 # Skip for now
    ESCALATE = "escalate"         # Need more expert input

class ReviewSubmission(BaseModel):
    decision: ReviewDecision
    corrected_query: Optional[str]  # If decision is CORRECT
    notes: Optional[str]
    tags: Optional[List[str]]       # For categorization
```

---

## Scenario 5: User Feedback (Thumbs Up/Down)

### 5.1 User Provides Feedback on Generated DSL

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│      User       │         │     System      │         │  Review Queue   │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. Receive generated DSL │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
         │  2a. 👍 Thumbs Up         │                           │
         │──────────────────────────►│                           │
         │                           │  3a. Record positive      │
         │                           │      feedback             │
         │                           │      (potential RAG add)  │
         │                           │                           │
         │  2b. 👎 Thumbs Down       │                           │
         │──────────────────────────►│                           │
         │                           │  3b. Add to review queue  │
         │                           │──────────────────────────►│
         │                           │                           │
         │  4. Optional: "What was   │                           │
         │   wrong with this query?" │                           │
         │◄──────────────────────────│                           │
         │                           │                           │
         │  5. "Wrong table used"    │                           │
         │──────────────────────────►│  6. Attach feedback       │
         │                           │──────────────────────────►│
         │                           │                           │
```

**Feedback Flow:**
```python
class UserFeedback(BaseModel):
    turn_id: UUID
    rating: Literal["up", "down"]
    feedback_text: Optional[str]
    feedback_category: Optional[FeedbackCategory]

class FeedbackCategory(str, Enum):
    WRONG_TABLE = "wrong_table"
    WRONG_COLUMNS = "wrong_columns"
    WRONG_FILTER = "wrong_filter"
    WRONG_AGGREGATION = "wrong_aggregation"
    SYNTAX_ERROR = "syntax_error"
    INCOMPLETE = "incomplete"
    OTHER = "other"
```

**Auto-Actions Based on Feedback:**
| Feedback | Confidence | Action |
|----------|------------|--------|
| 👍 + High (≥0.9) | Auto-approve to RAG |
| 👍 + Medium (0.7-0.9) | Add to review queue (priority: low) |
| 👎 + Any | Add to review queue (priority: high) |
| 👎 + Feedback text | Add to queue with context |

**API Endpoints:**
- `POST /api/v1/conversations/{conv_id}/turns/{turn_id}/feedback` - Submit feedback
- `GET /api/v1/feedback/stats` - Feedback statistics
- `GET /api/v1/feedback/recent` - Recent feedback items

---

## Data Flow Summary

```
                                    ┌─────────────────────────────────────┐
                                    │           SUPER ADMIN               │
                                    │  • Create Workspaces                │
                                    │  • Assign Workspace Admins          │
                                    └──────────────┬──────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WORKSPACE                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ WORKSPACE ADMIN │    │     EXPERT      │    │      USER       │         │
│  │                 │    │                 │    │                 │         │
│  │ • Configure     │    │ • Review Queue  │    │ • Submit Query  │         │
│  │   Providers     │    │ • Annotate      │    │ • Select Conn   │         │
│  │ • Add Conns     │    │   Schema        │    │ • Get DSL       │         │
│  │ • Refresh       │    │ • Approve/      │    │ • 👍/👎         │         │
│  │   Schema        │    │   Reject        │    │   Feedback      │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SHARED RESOURCES                             │   │
│  │  • Providers & Connections (configured by admin)                     │   │
│  │  • Schema Cache (Redis)                                              │   │
│  │  • Schema Annotations (created by experts)                           │   │
│  │  • RAG Examples (approved by experts)                                │   │
│  │  • Conversation History                                              │   │
│  │  • Audit Logs                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Core Infrastructure ✅
- [x] Workspace/Provider/Connection models & repos
- [x] SchemaAnnotation model & repo
- [x] Conversation/Turn models & repos
- [x] RAGExample model & repo
- [x] AuditLog model & repo

### Phase 2: Admin & Setup
- [ ] Super Admin APIs
- [ ] Workspace Admin APIs
- [ ] Connection testing
- [ ] Schema introspection & caching

### Phase 3: Expert Tools
- [ ] Annotation Agent with tools
- [ ] Multi-turn annotation chat
- [ ] Review Queue UI & APIs
- [ ] Auto-annotation with LLM

### Phase 4: Query Generation
- [ ] Agentic orchestrator
- [ ] Schema Agent
- [ ] RAG Retrieval Agent
- [ ] Query Builder Agent
- [ ] Validator Agent
- [ ] Clarification flow

### Phase 5: Feedback Loop
- [ ] User feedback APIs
- [ ] Auto-queue based on feedback
- [ ] RAG index updates
- [ ] Metrics & dashboards
