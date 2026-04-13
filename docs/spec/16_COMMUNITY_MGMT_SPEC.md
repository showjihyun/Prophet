# 16 — Community Management SPEC
Version: 0.2.0 | Status: CURRENT | Date: 2026-04-08

---

## 1. Overview

Functionality for dynamically managing communities during simulation execution.
Beyond the initial configuration at campaign setup, community editing/adding/deleting/agent reassignment is possible **when in paused/configured/created state**.

A fully implemented **Community Templates** CRUD feature exists independently of simulations.
Templates are persisted as JSON in `data/community_templates.json`.

**Core Principles:**
- Changes allowed when simulation is in `paused`, `configured`, or `created` state
- Read-only in `running` or `completed` state (returns 409)
- All changes are immediately reflected in in-memory state, asynchronously persisted to DB

**Implementation Status (2026-04-08):**
- Community CRUD (update/add/delete/reassign): ✅ Fully implemented
- Community Templates CRUD (list/create/update/delete): ✅ Fully implemented
- Frontend CommunitiesDetailPage (with CRUD buttons): ✅ Fully implemented
- Frontend CommunityManagePage (template management): ✅ Fully implemented
- Community Threads (list/detail): ✅ Fully implemented (synthetic generation)

---

## 2. API Endpoints

All community management endpoints are implemented in `backend/app/api/communities.py`.
Community Templates endpoints are separately implemented in `backend/app/api/community_templates.py`.

### 2.1 Community Edit (Update)

```
PATCH /api/v1/simulations/{simulation_id}/communities/{community_id}
```

**Request:**
```json
{
  "name": "Early Adopters (Revised)",
  "personality_profile": {
    "openness": 0.9,
    "skepticism": 0.2,
    "trend_following": 0.8,
    "brand_loyalty": 0.3,
    "social_influence": 0.7
  }
}
```

**Response 200:**
```json
{
  "community_id": "uuid",
  "name": "Early Adopters (Revised)",
  "size": 100,
  "agents_updated": 100
}
```

> **Note:** The `personality_profile` field is not included in the response. The actual response returns only 4 fields: `community_id`, `name`, `size`, `agents_updated`.

**Error:**
- 409: Simulation is in `running` or `completed` state
- 404: community_id does not exist (when there are no agents in that community)

**Behavior:**
- When `personality_profile` is changed, the personality values of **all agents** in that community
  are updated with ±10% random deviation from the new profile
- `name` change is display-only (no effect on agents)

### 2.2 Community Add (Create)

```
POST /api/v1/simulations/{simulation_id}/communities
```

**Request:**
```json
{
  "name": "New Segment",
  "agent_type": "consumer",
  "size": 50,
  "personality_profile": {
    "openness": 0.5,
    "skepticism": 0.5,
    "trend_following": 0.5,
    "brand_loyalty": 0.5,
    "social_influence": 0.4
  }
}
```

**Response 201:**
```json
{
  "community_id": "uuid",
  "name": "New Segment",
  "size": 50,
  "agents_created": 50,
  "edges_created": 120
}
```

**Behavior:**
- Creates `size` new agents (personality = profile ±10% deviation)
- Adds cross-community edges to the existing network with `cross_community_prob` probability
- Intra-community edges are generated using the Watts-Strogatz method

### 2.3 Community Delete (Delete)

```
DELETE /api/v1/simulations/{simulation_id}/communities/{community_id}
```

**Response 200:**
```json
{
  "community_id": "uuid",
  "agents_removed": 100,
  "edges_removed": 350
}
```

**Constraint:** A minimum of 1 community must be maintained (returns 400 when attempting to delete the last community)

**Behavior:**
- Removes all agents in that community from the `agents` list
- Removes all edges connected to the removed agents from the network
- No effect on step_history (past data is preserved)

### 2.4 Agent Reassign (Reassign)

```
POST /api/v1/simulations/{simulation_id}/communities/{community_id}/reassign
```

**Request:**
```json
{
  "agent_ids": ["uuid1", "uuid2"],
  "target_community_id": "uuid-target"
}
```

**Response 200:**
```json
{
  "reassigned_count": 2,
  "source_community_id": "uuid-source",
  "target_community_id": "uuid-target"
}
```

**Behavior:**
- Changes the agent's `community_id` to the target
- Existing cross-community edges are preserved (no new edges added — differs from SPEC)
- The `community_id` attribute of the network node is also updated

> **Implementation Difference:** The SPEC specifies adding new edges with `cross_community_prob` to agents in the new community, but the actual implementation preserves existing edges and does not add new edges. Can be improved in a future update.

### 2.5 Community List (List)

```
GET /api/v1/simulations/{simulation_id}/communities/
```

**Response 200:** `CommunitiesListResponse` — see `06_API_SPEC.md#5-community-endpoints`.

### 2.6 Community Thread List (List Threads)

```
GET /api/v1/simulations/{simulation_id}/communities/{community_id}/threads
```

**Response 200:** `ThreadsListResponse` — returns 3 synthetic threads per community.
Threads are deterministically generated reflecting the actual simulation state's `mean_belief`, `adoption_rate`, and `dominant_action`.

### 2.7 Community Thread Detail (Thread Detail)

```
GET /api/v1/simulations/{simulation_id}/communities/{community_id}/threads/{thread_id}
```

**Response 200:** `ThreadDetailResponse` — includes list of thread messages.
**Error:** 404 — thread_id does not exist.

---

## 2B. Community Templates API

Community templates are a global resource independent of simulations.
Implemented in `backend/app/api/community_templates.py`. Router prefix: `/api/v1/communities/templates`.
Persisted as JSON in `data/community_templates.json`. 5 default templates are built-in.

### Default Built-in Templates

| template_id | name | agent_type | default_size |
|-------------|------|------------|-------------|
| `early_adopters` | Early Adopters | early_adopter | 100 |
| `general_consumers` | General Consumers | consumer | 500 |
| `skeptics` | Skeptics | skeptic | 200 |
| `experts` | Industry Experts | expert | 30 |
| `influencers` | Influencers | influencer | 170 |

### GET `/api/v1/communities/templates/`

Returns all templates.

**Response 200:**
```json
{
  "templates": [
    {
      "template_id": "early_adopters",
      "name": "Early Adopters",
      "agent_type": "early_adopter",
      "default_size": 100,
      "description": "Tech-savvy, high openness",
      "personality_profile": { "openness": 0.8, "skepticism": 0.3, ... }
    }
  ]
}
```

### POST `/api/v1/communities/templates/`

Create a new template (UUID auto-assign).

**Request:** `CommunityTemplateInput`
```json
{
  "name": "string",
  "agent_type": "string",
  "default_size": 100,
  "description": "optional",
  "personality_profile": { "openness": 0.5, ... }
}
```

**Response 200:** Returns all fields of the created template.

### PUT `/api/v1/communities/templates/{template_id}`

Full replacement of an existing template (full replace).

**Response 200:** All fields of the updated template.
**Error:** 404 — template_id does not exist.

### DELETE `/api/v1/communities/templates/{template_id}`

Delete a template.

**Response:** 204 No Content.
**Error:** 404 — template_id does not exist.

---

## 3. Frontend UI

### 3.1 Communities Overview Page (`/communities`) — ✅ Implemented

`frontend/src/pages/CommunitiesDetailPage.tsx`

**Displayed content:**
- Summary Stats (Total Communities, Total Agents, Active Interactions, Avg Sentiment)
- Community card grid (sentiment bar, emotion distribution, activity status, key influencers)
- Community Connections matrix (cross-community edge strength visualization)

**Actions (canEdit condition: simulationId present and status is `paused`/`configured`/`created`):**
- [+ Add Community] button — enters name/size via `window.prompt()` → POST API
- [Edit] icon button on each card — enters name via `window.prompt()` → PATCH API
- [Delete] icon button on each card — `window.confirm()` then DELETE API
- [Manage Templates] button → navigates to `/communities/manage`

**Data source:** TanStack Query (`useCommunities`, `useCreateCommunity`, `useUpdateCommunity`, `useDeleteCommunity`)
**Toast:** Calls Zustand `addToast()` on success/failure

> **Implementation Difference:** The SPEC planned an edit modal (with sliders), but the actual implementation only accepts name input via `window.prompt()`. Personality profile slider editing is not implemented.

### 3.2 Community Manage Page (`/communities/manage`) — ✅ Implemented

`frontend/src/pages/CommunityManagePage.tsx`

**Features:**
- Community Templates CRUD (list, create, update/edit, delete)
- Inline form (Add/Edit): name, agent_type (dropdown), default_size, description, personality sliders (5 sliders)
- Template card grid: personality bars visualization, [Edit]/[Delete] buttons
- TanStack Query based (`useCommunityTemplates`, `useCreateCommunityTemplate`, `useUpdateCommunityTemplate`, `useDeleteCommunityTemplate`)
- Error banner, loading state, disabled while saving

**Supported Agent Types:** consumer, early_adopter, skeptic, expert, influencer, bridge

### 3.3 Community Opinion Page (`/communities/:communityId`) — ✅ Implemented

`frontend/src/pages/CommunityOpinionPage.tsx`

Displays conversation thread list and detail per community.
`GET .../communities/{community_id}/threads` → `GET .../threads/{thread_id}` chained.

---

## 4. Orchestrator Integration

`backend/app/engine/simulation/orchestrator.py` — implemented in the `SimulationOrchestrator` class.

### SimulationOrchestrator Methods (implementation finalized)

```python
async def update_community(
    self,
    simulation_id: UUID,
    community_id: str,
    name: str | None = None,
    personality_profile: dict[str, float] | None = None,
) -> dict:
    """Update community properties. Requires PAUSED/CONFIGURED/CREATED state.
    Returns: {community_id, name, size, agents_updated}
    """

async def add_community(
    self,
    simulation_id: UUID,
    name: str,
    agent_type: str,
    size: int,
    personality_profile: dict[str, float],
) -> dict:
    """Add a new community with agents and intra/cross-community edges.
    Returns: {community_id, name, size, agents_created, edges_created}
    """

async def remove_community(
    self,
    simulation_id: UUID,
    community_id: str,
) -> dict:
    """Remove community and its agents/edges. Raises ValueError if last community.
    Returns: {community_id, agents_removed, edges_removed}
    """

async def reassign_agents(
    self,
    simulation_id: UUID,
    community_id: str,          # source community (NOT in SPEC signature — added in impl)
    agent_ids: list[UUID],
    target_community_id: str,
) -> dict:
    """Move agents to a different community. Updates network node community_id attr.
    Returns: {reassigned_count, source_community_id, target_community_id}
    """
```

> **Implementation Difference:** The actual signature of `reassign_agents` has an additional `community_id` (source) parameter compared to the SPEC. The API layer passes the path param `{community_id}` as this parameter.

### _require_mutable State Constraints

Based on `_require_mutable()` internal implementation:

| Current State | Allowed | Not Allowed |
|----------|------|--------|
| `configured` | All community management | — |
| `paused` | All community management | — |
| `created` | All community management | — |
| `running` | Read-only | Edit/Add/Delete/Reassign → 409 |
| `completed` | Read-only | Edit/Add/Delete/Reassign → 409 |

> **SPEC Change:** The original SPEC did not include `created` state in the mutable list, but the actual implementation also allows `"created"` state. The frontend's `canEdit` condition is also implemented to include `SIM_STATUS.CREATED`.

---

## 5. Error Specification

### Community CRUD Errors

| Condition | HTTP | Detail |
|-----------|------|--------|
| Simulation running/completed | 409 | "Community changes only allowed when paused or configured" |
| community_id not found (update) | 404 | "Community {id!r} not found" — when there are no members |
| community_id not found (delete) | 400 | "Community {id!r} not found" — ValueError mapped to 400 |
| Attempt to delete last community | 400 | "Cannot delete last community" |
| size < 1 or size > 10000 | 422 | Pydantic validation error (Field(ge=1, le=10000)) |
| target_community_id not found (reassign) | 400 | "Target community {id!r} not found" — ValueError mapped to 400 |
| agent_id not in source community | — | Returns reassigned_count = 0 without error (silent skip) |

> **Implementation Difference:** The SPEC defined community_id not found as 404, but in delete/reassign, ValueError is mapped to 400. Also, when agent_id is not in the source community, it silently skips (reassigned_count=0) instead of returning 400.

### Community Templates Errors

| Condition | HTTP | Detail |
|-----------|------|--------|
| template_id not found (PUT/DELETE) | 404 | "Template '{id}' not found" |


---

## 6. Acceptance Criteria

### Community CRUD

- **CM-01:** ✅ PATCH community → updates personality of all agents in that community (±10% deviation applied)
- **CM-02:** ✅ POST community → creates new agents + network edges (Watts-Strogatz internal + cross-community)
- **CM-03:** ✅ DELETE community → removes agents + edges, maintains minimum of 1
- **CM-04:** ✅ POST reassign → changes agent community_id + updates network node attribute
- **CM-05:** ✅ Attempt to change in running/completed state → 409
- **CM-06:** ✅ Edit/Add/Delete buttons in UI are active only when paused/configured/created

### Community Templates

- **CT-01:** ✅ GET templates → returns full template list (5 defaults + user-created)
- **CT-02:** ✅ POST template → creates new template + JSON persistence
- **CT-03:** ✅ PUT template → full replacement of existing template + JSON persistence
- **CT-04:** ✅ DELETE template → removes template + JSON persistence
- **CT-05:** ✅ CommunityManagePage provides full CRUD functionality

### Not Implemented / Future Improvements

- **OPEN-01:** CommunitiesDetailPage editing only allows name changes (personality sliders not implemented)
- **OPEN-02:** New cross-community edge creation with new community on reassign is not implemented
- **OPEN-03:** Community detail page (`/communities/:communityId`) — detailed view such as agent list, emotion charts, etc. not implemented (currently only list page)
