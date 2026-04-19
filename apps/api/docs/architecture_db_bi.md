# Architecture: Real Database/BI Integration for Jarvis PM Data Analysis

> **Version:** 1.0  
> **Status:** Design Document  
> **Scope:** Next.js 14 Frontend + FastAPI Python Backend  
> **Author:** Architect (Claude)  

---

## 1. Executive Summary

The Jarvis PM data analysis tool currently operates on synthetic data. This architecture enables secure, read-only integration with real business databases and BI tools, allowing AI to query live data and generate trustworthy insights. The design prioritizes **security, auditability, and incremental rollout**.

---

## 2. Security-First Principles

### 2.1 Read-Only Connections Only
- All data source connections MUST be configured with read-only credentials.
- The system validates this by running a lightweight `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` (or dialect equivalent) on connection open.
- Any detected write operation (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `EXECUTE` on stored procedures that mutate) is blocked at the application layer before reaching the database.

### 2.2 Credential Encryption at Rest
- Passwords and secrets are encrypted using **AES-256-GCM** before persistence.
- Encryption key is stored in an environment variable (`JARVIS_DB_ENCRYPTION_KEY`) and never committed to source control.
- Alternative: use a secret manager (e.g., AWS Secrets Manager, Azure Key Vault) and store only the reference ARN in the database.

```python
# cryptography-based encryption helper
from cryptography.fernet import Fernet
import os

key = os.environ["JARVIS_DB_ENCRYPTION_KEY"]
cipher = Fernet(key)

def encrypt_secret(plain: str) -> str:
    return cipher.encrypt(plain.encode()).decode()

def decrypt_secret(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()
```

### 2.3 Query Sandboxing
| Control | Value | Implementation |
|---------|-------|----------------|
| Query Timeout | 30 seconds | `statement_timeout` (PostgreSQL), `SET MAX_EXECUTION_TIME` (MySQL), or driver-level timeout |
| Row Limit | 10,000 max | Append `LIMIT 10000` or use `cursor.fetchmany(10000)` |
| Forbidden Commands | DDL + DML | Regex + AST-based denylist |
| Max Query Length | 10,000 characters | Reject oversized inputs |

**Forbidden keyword denylist (case-insensitive):**
```python
FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "grant", "revoke", "merge", "replace",
    "call", "execute", "exec", "sp_executesql",
    "into outfile", "into dumpfile", "load_file",
    "copy", "upsert"
}
```

### 2.4 Network Isolation
- **Preferred:** VPN, VPC peering, or dedicated line (专线) for on-premise hospital databases.
- **Public internet:** Allowed only with IP allowlisting, SSL/TLS enforced, and mutual TLS (mTLS) where supported.
- Connection metadata stores `ssl_mode` (`require`, `verify-ca`, `verify-full`, `disable`).

---

## 3. Supported Data Sources

### 3.1 Relational Databases
| Engine | Driver | Async Support |
|--------|--------|---------------|
| PostgreSQL | `psycopg2` / `asyncpg` | Yes (`asyncpg`) |
| MySQL | `pymysql` / `aiomysql` | Yes (`aiomysql`) |
| SQL Server | `pyodbc` / `aioodbc` | Yes (`aioodbc`) |
| Oracle | `oracledb` / `cx_Oracle` | Yes (`oracledb` thin mode) |

### 3.2 OLAP Engines
| Engine | Driver | Notes |
|--------|--------|-------|
| ClickHouse | `clickhouse-connect` | Fast analytical queries |
| Apache Doris | `pymysql` compatible | MySQL protocol |
| StarRocks | `pymysql` compatible | MySQL protocol |

### 3.3 BI APIs
| BI Tool | Integration Mode | API Endpoint Pattern |
|---------|------------------|----------------------|
| Metabase | REST API | `POST /api/card/:id/query` |
| Apache Superset | REST API | `POST /api/v1/chart/data` |
| FineBI | Simulated SQL or Embedded API | Vendor-specific SDK or JDBC bridge |

---

## 4. Connection Management

### 4.1 Database Schema

```sql
CREATE TABLE data_source_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type            VARCHAR(50) NOT NULL, -- postgresql, mysql, sqlserver, oracle, clickhouse, doris, starrocks, metabase, superset, finebi
    host            VARCHAR(500) NOT NULL,
    port            INTEGER NOT NULL,
    database_name   VARCHAR(255) NOT NULL,
    username        VARCHAR(255) NOT NULL,
    encrypted_password TEXT NOT NULL,
    ssl_mode        VARCHAR(50) DEFAULT 'require',
    extra_params    JSONB DEFAULT '{}', -- dialect-specific options
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dsc_project_id ON data_source_connections(project_id);
```

### 4.2 Connection Pooling
- Use **SQLAlchemy** with `AsyncEngine` for relational sources.
- OLAP sources use lightweight per-request connections due to their connectionless HTTP-like protocols.
- Pool settings:
  - `pool_size=5`
  - `max_overflow=10`
  - `pool_timeout=30`
  - `pool_recycle=1800`

```python
from sqlalchemy.ext.asyncio import create_async_engine

async def get_engine(conn: DataSourceConnection):
    driver = DRIVER_MAP[conn.type]  # e.g., "postgresql+asyncpg"
    password = decrypt_secret(conn.encrypted_password)
    url = f"{driver}://{conn.username}:{password}@{conn.host}:{conn.port}/{conn.database_name}"
    return create_async_engine(url, pool_size=5, max_overflow=10, pool_timeout=30)
```

### 4.3 Health Check Endpoint
```python
@router.get("/data-sources/{ds_id}/health")
async def health_check(ds_id: UUID, db: AsyncSession = Depends(get_db)):
    conn = await get_connection(db, ds_id)
    engine = await get_engine(conn)
    try:
        async with engine.connect() as c:
            result = await c.execute(text("SELECT 1"))
            await result.scalar()
        return {"status": "healthy", "latency_ms": ...}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    finally:
        await engine.dispose()
```

---

## 5. Query Generation Strategy

### 5.1 Option A: AI Generates SQL from Natural Language
- User inputs a question in Chinese or English.
- LLM receives schema context + business annotations + user question.
- LLM returns SQL.
- Human reviews SQL in a preview pane before execution.

### 5.2 Option B: Predefined Metric Templates
- Product manager defines reusable metric templates (e.g., "月度挂号量").
- Template stores parameterized SQL with Jinja2 placeholders.
- AI only fills date ranges, department filters, etc.

```sql
-- Template: monthly_registration_volume
SELECT
  DATE_TRUNC('month', registration_time) AS month,
  COUNT(*) AS total_registrations
FROM registrations
WHERE department_id = {{ department_id }}
  AND registration_time BETWEEN '{{ start_date }}' AND '{{ end_date }}'
GROUP BY 1
ORDER BY 1;
```

### 5.3 Option C: Text-to-SQL with Schema Context
- Automatic schema discovery builds a compact context string.
- Context includes table names, column names, data types, primary keys, foreign keys, and user annotations.
- Sent to LLM with a system prompt that restricts output to read-only `SELECT` statements.

### 5.4 Recommended Hybrid Approach
1. **Phase 1:** Option B (templates) for high-trust, repeatable metrics.
2. **Phase 2:** Option C for ad-hoc exploration by power users.
3. **Guardrails:** All AI-generated SQL passes through the sandbox validator (Section 2.3) before execution.

---

## 6. Schema Discovery & Context Building

### 6.1 Auto-Discovery
```python
async def discover_schema(engine, ds_type: str) -> SchemaCatalog:
    if ds_type in ("postgresql", "mysql", "sqlserver"):
        tables = await fetch_tables_sqlalchemy(engine)
    elif ds_type == "clickhouse":
        tables = await fetch_tables_clickhouse(engine)
    return SchemaCatalog(tables=[
        TableSchema(
            name=t.name,
            columns=[ColumnSchema(name=c.name, dtype=c.type, nullable=c.nullable) for c in t.columns]
        ) for t in tables
    ])
```

### 6.2 User Annotations
```sql
CREATE TABLE data_source_annotations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id     UUID NOT NULL REFERENCES data_source_connections(id) ON DELETE CASCADE,
    table_name        VARCHAR(255) NOT NULL,
    column_name       VARCHAR(255),
    business_meaning  TEXT NOT NULL,
    created_by        UUID NOT NULL REFERENCES users(id),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.3 LLM Prompt Context Format
```markdown
## Database Schema Context

### Table: registrations
- registration_id (UUID, PK) — 挂号记录唯一标识
- patient_id (UUID, FK) — 患者ID
- department_id (UUID, FK) — 科室ID
- registration_time (TIMESTAMP) — 挂号时间
- fee (DECIMAL) — 挂号费金额
- status (VARCHAR) — 挂号状态: pending, completed, cancelled

### Table: departments
- department_id (UUID, PK)
- name (VARCHAR) — 科室名称
- hospital_id (UUID, FK) — 所属医院

## User Question
"上个月各科室的挂号量排名"

## Instructions
- Generate a read-only PostgreSQL SELECT query.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE.
- Limit results to 10,000 rows.
- Use table aliases for readability.
```

---

## 7. Execution & Caching

### 7.1 Async Execution
- All queries run in async tasks to avoid blocking the FastAPI event loop.
- Long-running queries (>10s) return a `job_id` and stream progress via Server-Sent Events (SSE) or WebSocket.

```python
@router.post("/data-sources/{ds_id}/queries")
async def execute_query(ds_id: UUID, payload: QueryPayload):
    validated_sql = sandbox_validate(payload.sql)
    task = asyncio.create_task(run_query_task(ds_id, validated_sql))
    return {"job_id": task.get_name(), "status": "queued"}
```

### 7.2 Caching Strategy
| Cache Target | TTL | Use Case |
|--------------|-----|----------|
| Dashboard queries | 5 minutes | Real-time-ish metrics |
| Report queries | 1 hour | Scheduled reports |
| Schema metadata | 24 hours | Schema browser |

```python
import redis.asyncio as redis

cache_key = f"query:{hash(sql)}:{hash(json.dumps(params))}"
cached = await redis_client.get(cache_key)
if cached:
    return json.loads(cached)

result = await run_query(ds_id, sql)
await redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
return result
```

---

## 8. Error Handling & Auditing

### 8.1 Query Execution Logs
```sql
CREATE TABLE query_audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id   UUID NOT NULL REFERENCES data_source_connections(id),
    executed_by     UUID NOT NULL REFERENCES users(id),
    sql_text        TEXT NOT NULL,
    row_count       INTEGER,
    execution_time_ms INTEGER,
    status          VARCHAR(50) NOT NULL, -- success, timeout, error, blocked
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_qal_connection_id ON query_audit_logs(connection_id);
CREATE INDEX idx_qal_created_at ON query_audit_logs(created_at);
```

### 8.2 Graceful Degradation
- If the data source is unreachable, the UI falls back to **framework-only analysis** using cached historical aggregates or synthetic explanations.
- User sees a clear banner: "实时数据连接不可用，当前展示基于历史缓存数据的分析结果。"

---

## 9. Frontend UI

### 9.1 Pages & Components
| Page | Route | Purpose |
|------|-------|---------|
| Data Sources | `/settings/data-sources` | CRUD for connections |
| Schema Browser | `/data-sources/:id/schema` | Explore tables/columns |
| Query Builder | `/data-sources/:id/query` | Natural language input + SQL preview |
| Results & Insights | `/data-sources/:id/results` | Result table + AI insights |

### 9.2 Key UI Components
- `<DataSourceForm />` — host, port, credentials, SSL toggle, test connection button
- `<SchemaBrowser />` — searchable tree of tables and columns with annotation inline-edit
- `<QueryInput />` — natural language textarea + SQL preview accordion
- `<ResultTable />` — paginated, sortable data grid
- `<InsightPanel />` — AI-generated markdown summary of results

---

## 10. Implementation Phases

### Phase 1: PostgreSQL Read-Only, Manual SQL
- [ ] Implement `data_source_connections` schema
- [ ] Build encryption helper and credential storage
- [ ] Add PostgreSQL connector with `asyncpg`
- [ ] Build sandbox validator (timeout, row limit, forbidden keywords)
- [ ] Frontend: connection form + schema browser + manual SQL input
- [ ] Query execution + result table
- [ ] Audit logging

### Phase 2: Natural Language to SQL
- [ ] Schema discovery service
- [ ] Annotation CRUD UI
- [ ] LLM prompt builder with schema context
- [ ] SQL preview + human approval step
- [ ] AI insight generation on query results

### Phase 3: Multi-Connector & BI Integration
- [ ] Add MySQL, SQL Server, Oracle connectors
- [ ] Add ClickHouse, Doris, StarRocks connectors
- [ ] Metabase/Superset/FineBI API adapters
- [ ] Predefined metric template system
- [ ] Automated dashboard scheduling
- [ ] Advanced caching and query optimization

---

## 11. Security Checklist

Before deploying each phase:

- [ ] Encryption key is stored in environment variables or a secret manager
- [ ] Database credentials are never logged in plaintext
- [ ] All queries pass the forbidden keyword validator
- [ ] Query timeouts and row limits are enforced at the driver level
- [ ] Read-only mode is verified on connection open
- [ ] SSL is required for all public internet connections
- [ ] Audit logs capture every query execution attempt
- [ ] Connection pooling does not leak credentials between tenants
- [ ] Redis cache keys are namespaced by `project_id`
- [ ] Fallback behavior is tested when connections fail

---

## 12. Code Interfaces (Summary)

```python
# Pydantic models
class DataSourceConnectionCreate(BaseModel):
    name: str
    project_id: UUID
    type: Literal["postgresql", "mysql", "sqlserver", "oracle", "clickhouse", "doris", "starrocks", "metabase", "superset", "finebi"]
    host: str
    port: int
    database_name: str
    username: str
    password: str
    ssl_mode: str = "require"
    extra_params: dict = {}

class QueryPayload(BaseModel):
    sql: str
    parameters: dict = {}

class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: int
    cached: bool = False
```

---

*End of Document*
