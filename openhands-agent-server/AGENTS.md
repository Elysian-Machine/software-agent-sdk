# openhands-agent-server

See the [project root AGENTS.md](../AGENTS.md) for repository-wide policies and workflows.

## Development

This package lives in the monorepo root. Typical commands (run from repo root):

- Install deps: `make build`
- Run agent-server tests: `uv run pytest tests/agent_server`

## PyInstaller data files

When adding non-Python files (JS, templates, etc.) loaded at runtime, add them to `openhands-agent-server/openhands/agent_server/agent-server.spec` using `collect_data_files`.


## REST API compatibility & deprecation policy

The agent-server **REST API** (the FastAPI OpenAPI surface under `/api/**`) is a
public API and must remain backward compatible across releases.

### Deprecating an endpoint

When deprecating a REST endpoint:

1. Mark the operation as deprecated in OpenAPI by passing `deprecated=True` to the
   FastAPI route decorator.
2. Add a docstring note that includes:
   - the version it was deprecated in
   - the version it is scheduled for removal in (default: **3 minor releases** later)

Example:

```py
@router.post("/foo", deprecated=True)
async def foo():
    """Do something.

    Deprecated since v1.2.3 and scheduled for removal in v1.5.0.
    """
```

### Removing an endpoint

Removing an endpoint is a breaking change.

- Endpoints must be deprecated for **at least one release** before removal.
- Any breaking REST API change requires at least a **MINOR** SemVer bump.

### CI enforcement

The workflow `Agent server REST API breakage checks` compares the current OpenAPI
schema against the previous `openhands-agent-server` release on PyPI using [oasdiff](https://github.com/oasdiff/oasdiff).

It currently enforces:
- No removal of operations (path + method) unless they were already marked
  `deprecated: true` in the previous release.
- Breaking changes require a MINOR (or MAJOR) version bump.

WebSocket/SSE endpoints are not covered by this policy (OpenAPI only).


## Events: REST + WebSocket contracts

This package implements the event APIs that clients (including `RemoteConversation` in the SDK)
use to consume events.

### Design stance

- **REST is the source of truth** for events (persisted state).
- **WebSocket is a streaming convenience** for freshness (best-effort delivery).

Clients must be able to reconnect and still converge by using REST.

### REST contract: `/api/conversations/{conversation_id}/events/search`

#### Pagination
- The endpoint supports pagination using `limit` and `page_id`.
- Responses include `next_page_id`.

**Important:** current server implementation treats `page_id` as an **inclusive** cursor:
- when `page_id` is provided, the returned page may include the event whose `id == page_id`.
- clients that want “strictly after page_id” semantics must drop the first event if it matches
  the cursor.

(If you change this behavior, update clients and tests accordingly.)

#### Ordering / stability
- Event ordering must be stable enough that paging does not skip/duplicate items (other than the
  intentional inclusivity behavior above).
- If ordering changes (e.g. sort order flips), cursor semantics must be revisited.

#### Scaling constraints
- The server must assume runs can produce **tens of thousands of events**.
- Both server and clients must avoid patterns that require scanning the full event history.

This implies:
- enforce reasonable `limit` bounds
- keep pagination efficient (indexes / storage access)

### WebSocket contract: `/events/{conversation_id}`

WS provides low-latency streaming, but should be treated as **best-effort**:
- connections can drop
- clients can lag
- callbacks can be delayed

As a result:
- WS should not be the only correctness mechanism.
- On reconnect / run completion, clients should reconcile via REST using a cursor (`page_id`).

### SDK coupling (where the policy is implemented)

The SDK’s `RemoteConversation` implements client-side reconciliation and bounded paging logic.
See:
- `openhands-sdk/openhands/sdk/conversation/impl/AGENTS.md`

