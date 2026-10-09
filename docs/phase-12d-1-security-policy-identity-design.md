# BizIQ Phase 12D-1 — Security Policy and Identity Design

**Status: design proposal only.** No policy, code, environment, credential,
database, dependency, or runtime setting was changed for this document. No tests
were run. The current policy remains authoritative until the decisions at the
end are approved.

## 1. Current verified policy

In `security-agent/app/services/request_security_service.py`:

```python
OPERATION_PERMISSION = {
    "SECURITY_ANALYSIS": "RUN_SECURITY_ANALYSIS",
}

SERVICE_OPERATION_ALLOWLIST = {
    "security-agent": {"security-agent": {"SECURITY_ANALYSIS"}},
}
```

Consequences:

- The only currently mapped user operation is `SECURITY_ANALYSIS`, which
  requires the database permission `RUN_SECURITY_ANALYSIS`.
- The only currently allowed verified service/target/operation tuple is
  `security-agent → security-agent / SECURITY_ANALYSIS`.
- `QUERY_DATA`, `RETRIEVE_DATA`, and `GENERATE_INSIGHT` are accepted by the
  request schema as operation labels, but have no user permission mapping and
  no service allowlist grant. They are denied.
- Both checks are required: service authorization is checked separately from
  the authenticated user's role permissions.
- Service identity is derived from the configured service token and compared
  with `source_agent`; the body label alone is not trusted.
- Missing service-token configuration fails closed. Service tokens are read
  from `BIZIQ_SERVICE_TOKEN_NLP_AGENT`, `BIZIQ_SERVICE_TOKEN_IR_AGENT`,
  `BIZIQ_SERVICE_TOKEN_INSIGHT_AGENT`, and
  `BIZIQ_SERVICE_TOKEN_SECURITY_AGENT`.

`security-agent/app/services/rbac_service.py` currently seeds:

| Existing role | Existing business permissions |
|---|---|
| `ADMIN` | None. Its current grants are security, audit, user-management, and own-profile permissions. |
| `ANALYST` | None. It can view users/security analysis and its own profile. |
| `USER` | None. It can view its own profile. |

No current role has any of the three business permissions because those
permissions do not yet exist in the permission seed.

## 2. Orchestrator choice from current source

**Recommendation: make NLP the initial pipeline orchestrator.** This is the
smaller change against current behavior:

- NLP owns the user-question `/query` entry point, parses and saves the query,
  and already calls an IR client. `/forward-to-ir` also exists.
- Insight currently exposes `/insights/generate` for a caller-supplied question,
  structured query, and retrieved data. It does not call NLP or IR and has no
  downstream service client.
- Using Insight as orchestrator would add both NLP and IR clients and a new
  question-entry operation to Insight, while the existing NLP→IR path would
  need to be bypassed or reworked.

This recommendation retains the intended NLP → IR → Insight order. It does not
mean the current NLP-to-IR call works, nor that NLP is authorized to call any
downstream service today. It also does not solve Insight's incompatible auth or
the data-shape limitations described below.

## 3. Proposed minimum service policy

The table is a proposed exact allowlist for an NLP-orchestrated request. Each
tuple is narrow: one verified caller, one target, and one operation. No wildcard
or service-wide grant is proposed.

| Verified calling service | Target service | Operation | Purpose | Current status |
|---|---|---|---|---|
| `nlp-agent` | `nlp-agent` | `QUERY_DATA` | Authorize the incoming question parse/submit step | Denied today; proposed |
| `nlp-agent` | `ir-agent` | `RETRIEVE_DATA` | Retrieve evidence for this authorized question | Denied today; proposed |
| `nlp-agent` | `insight-agent` | `GENERATE_INSIGHT` | Generate the final answer from approved evidence | Denied today; proposed |

If later work changes orchestration so NLP itself calls IR, the tuple remains
`nlp-agent → ir-agent / RETRIEVE_DATA`. If Insight becomes the orchestrator,
the service identity/target tuples must be redesigned and explicitly approved;
do not add both designs speculatively.

The operation permission mapping must separately associate each operation
with a permission, for example:

| Operation | Proposed end-user permission |
|---|---|
| `QUERY_DATA` | `QUERY_DATA` |
| `RETRIEVE_DATA` | `RETRIEVE_DATA` |
| `GENERATE_INSIGHT` | `GENERATE_INSIGHT` |

The validator must allow a request only when both its exact service tuple and
the authenticated user's permission pass. A valid service token does not
provide user permission; a user permission does not authenticate a service.

## 4. Proposed end-user role mapping and data scope

Least-privilege proposal for the existing roles:

| Role | `QUERY_DATA` | `RETRIEVE_DATA` | `GENERATE_INSIGHT` | Rationale |
|---|---:|---:|---:|---|
| `USER` | No | No | No | Public registration currently creates this role; no business-data access is implied by registration. |
| `ANALYST` | Yes | Yes | Yes | These capabilities match the role's business-analysis purpose. Retrieval remains limited to data the user is entitled to access. |
| `ADMIN` | No by default | No by default | No by default | Current ADMIN is a Security/user-management role. Administrative status must not automatically grant access to business data. Grant each capability only if the product owner approves that responsibility. |

This table is a proposal, not a grant. The permission model can support
individually assigned permissions, but the current seed creates no business
permissions or grants. A role change and permission seed update would require
separate approval.

**Tenant and ownership requirements:**

- IR currently scopes every data source by an `owner` string derived from its
  bearer token. Its default development token maps to owner `demo`; configured
  `IR_API_TOKENS` map tokens to arbitrary owner strings.
- Security user IDs are integer database primary keys. Insight uses a string
  user ID from JWT `sub` or development headers. IR owner IDs are strings.
- There is no canonical tenant ID or tenant-aware data model in these APIs.
- Do not use one shared IR token mapped to one owner for all users; that would
  collapse user isolation. Do not trust a caller-provided owner or tenant ID.
- Before retrieval is enabled, define the authoritative tenant/data-owner
  mapping and ensure the authorization evidence limits the search to that
  scope. If one Security user may access multiple businesses, the authorization
  grant must include a selected tenant/business scope and IR must enforce it.

The current data model is per-owner, not explicitly multi-tenant. Whether to
represent a tenant as an IR owner or add tenant-aware ownership requires a
product/data-owner decision before implementation; this design does not change
the database schema.

## 5. Current identity issuance and incompatibilities

### Security Agent identity

- `POST /api/v1/auth/login` authenticates credentials against the Security
  Agent's user database and issues an HS256 JWT.
- The token claims are `sub`, `role`, and `exp`. `sub` is the numeric Security
  database user ID serialized as a string.
- `decode_access_token` verifies the signature and expiry using
  `JWT_SECRET_KEY` and `JWT_ALGORITHM` (restricted to HS256).
- The request validator reads `sub`, loads the active user record with
  `get_active_user_by_id`, compares that authenticated user's ID to the
  requested `user_id`, and checks permissions from the current database role.
  The JWT role claim is not the RBAC source of truth.

### Other agents

- **Insight:** `JWT_SECRET` is a separate setting. If configured, Insight
  decodes `sub` and `role` locally; it does not look up a Security user or
  validate current Security permissions. `DEV_AUTH` defaults to true and
  permits `X-User-Id`/`X-User-Role` identity headers. Those headers are not
  acceptable production identity evidence.
- **IR:** `IR_API_TOKENS` maps bearer tokens to owner strings and has a built-in
  development fallback. It does not validate Security JWTs or look up Security
  users. Its owner is used to scope data-source CRUD and search.
- **NLP:** the existing query routes have no authentication dependency. An
  authentication helper exists but is not applied to those routes. Its
  configured outbound IR token is not a Security-issued user token.
- **Shared contract:** `BusinessQuestionRequest.user_id` is a caller-provided
  string, while Security validation expects an integer ID. That field is
  identity context, not proof of identity.

Therefore an Insight request cannot currently establish an active Security
user merely by forwarding its own JWT or by supplying `user_id`. The current
Insight JWT secret, development headers, IR token-owner mapping, and Security
JWT/database identity are not a shared identity system.

### Proposed identity flow

1. The user authenticates with Security Agent and receives its existing
   end-user JWT. The client sends that JWT only to the NLP entry service and
   Security validation endpoint as user-authentication evidence; it is never
   used as a service credential.
2. NLP calls the Security validator with its own configured
   `X-BizIQ-Service-Token` and the user's Security JWT as a separate user
   credential. Security derives service identity from the header, validates
   the JWT, resolves the active user from its database, and checks the exact
   target/operation and user permission.
3. After authorization, Security issues a short-lived, audience-bound
   delegation assertion for the one approved downstream service and operation.
   Downstream agents validate that assertion and use its authenticated subject
   and tenant scope; they do not accept `user_id` headers as proof.
4. Each service-to-service hop uses the caller's service credential separately
   from the delegation assertion. Request ID, audience, operation, subject,
   tenant scope, expiry, and a unique token identifier are bound into the
   assertion. A downstream service must reject the wrong audience or scope.

**Signing design proposal:** use asymmetric signing for the delegation
assertion (Security retains the private key; consumers receive only the public
verification key). Do not distribute the current HS256 signing secret to all
agents. Key storage, rotation, issuer/audience values, and assertion lifetime
need approval. The assertion is not implemented by the current validation
endpoint, whose response only contains an allow/deny decision.

The initial user JWT may be sent to Security's validator as the user credential
because Security is the issuer and verifier. It must remain separate from the
service-token header, be excluded from audit records, and never be forwarded to
NLP/IR/Insight as their service authentication.

## 6. Proposed authorization request contract

Keep the current Security validator route, but separate credentials by channel.
Proposed request:

```http
POST /api/v1/security/validate-request
X-BizIQ-Service-Token: <credential for the calling service>
Authorization: Bearer <Security-issued end-user JWT>
Content-Type: application/json
```

```json
{
  "request_id": "<correlation-id>",
  "user_id": 42,
  "source_agent": "nlp-agent",
  "target_agent": "ir-agent",
  "operation": "RETRIEVE_DATA"
}
```

Contract rules:

- `request_id` is generated once at ingress, non-empty, bounded, and preserved
  across all calls and audit events.
- `source_agent` is a claim checked against the identity derived from the
  service credential. It never determines identity.
- `target_agent` and `operation` are enums with no arbitrary names or wildcard
  operation. Security checks their exact tuple against the service allowlist.
- `user_id` is a claim checked for exact equality with the active user ID
  obtained from the verified JWT. Prefer deriving this field from the JWT in a
  future request version to remove duplicate identity claims.
- The Security-issued JWT is user-authentication evidence only. The service
  token authenticates only the caller service.
- Do not accept raw credentials in `metadata`; omit arbitrary metadata from
  this authorization request unless a future schema defines safe, bounded
  fields.
- On allow, the proposed response must include a signed, short-lived delegation
  assertion scoped to the requested target/operation, plus the request ID. On
  denial, return a safe category and request ID, without either credential.
- Audit verified service identity, authenticated user ID, target, operation,
  request ID, outcome, and safe denial category. Never log either token.

This differs from the current API: the current user JWT is in the JSON field
`authorization_token`; it has no delegation assertion in its response. Those
contract changes require approval before implementation.

## 7. NLP/IR and IR/Insight data boundaries

### `/retrieve` versus `/search`

The current NLP client posts to `IR_AGENT_URL + "/retrieve"` with `query`,
`intent`, `entities`, `top_k`, `include_structured`, and `request_id`. Current
IR exposes `POST /search`, whose body accepts only `query` (up to 500 chars) and
`top_k` (1–20). There is no `/retrieve` route. IR returns `{query, results}`;
each result has `datasource_id`, `name`, `snippet`, `score`, and
`matched_terms`. It returns `results: []` successfully when no documents match.

Required later adapter: map NLP's normalized `structured_query.query` to IR's
`query`, pass `top_k`, send IR authentication in the service/user-authorization
mechanism approved above, then validate the actual `{query, results}` response.
Do not send NLP's extra fields to current `/search` and assume they were used.

### IR snippets versus Insight analytics input

Insight's `POST /insights/generate` requires `question`, `structured_query`,
and `retrieved_data[]`. Each retrieved source can contain `rows[]` and/or
`text`. IR provides text snippets and relevance metadata, not business rows.
Insight's no-data branch only handles sources where both rows and text are
empty. A non-empty snippet passes that branch, but the analytics code builds a
DataFrame from `rows` and may return 422 because the requested metric column is
missing. Sending snippets as fabricated rows would be incorrect.

The existing Insight contract can accept text as text, but its current
statistics path requires actual structured rows with the requested metric and
optional grouping/date columns. A structured business-data retrieval adapter
or a separately approved text-only answer path is required. Preserve the IR
`datasource_id`, `score`, and matched terms in a defined evidence metadata
contract; current Insight `RetrievedSource` has no fields for them.

## 8. Test plan after approval

Use isolated Security database fixtures and mock all service HTTP calls and LLM
providers.

| Test group | Allowed cases | Denied/failure cases |
|---|---|---|
| Service identity | Exact configured service credential matches its source claim | Missing/invalid credential; duplicate credential; source mismatch; unconfigured identity |
| Target/operation | Each individually approved tuple only | Unsupported target, operation, or tuple; no wildcard matching |
| User JWT | Valid Security-issued JWT resolves active DB user | Missing, invalid, expired JWT; inactive/nonexistent user; user-ID mismatch |
| User RBAC | Each permission granted to approved role and scoped tenant | Each missing permission; USER/ADMIN do not gain access by assumption |
| Combined authorization | Both service tuple and user permission pass | Either gate fails; service credential cannot substitute for user permission |
| Delegation assertion | Valid issuer, audience, subject, tenant, operation, request ID, expiry | Wrong audience/scope, expired/replayed assertion, tampered signature, mismatched subject |
| Tenant/ownership | User accesses only approved tenant/owner data | Cross-user or cross-tenant retrieval denied even with a valid service token |
| Audit | Correlation and verified identities recorded | Tokens, passwords, arbitrary metadata absent; audit failure cannot allow |
| Contracts | `/search` field mapping and validated IR results | `/retrieve` 404, malformed JSON/schema, timeout, empty successful results |
| Insight evidence | Genuine rows satisfy required metric and scope | Text-only snippets are not treated as rows; empty/failed retrieval does not invoke generation |
| End-to-end | Correlation and delegated identity propagate through NLP→IR→Insight | Security denial stops every downstream call; provider failure returns safe error |

## 9. Review status and proposed decisions

No item below has been approved by the project owner. These are recommendations
for review; the current deny-by-default policy remains unchanged.

1. **PROPOSED — Initial orchestrator:** NLP is the initial orchestrator.

2. **PROPOSED — Service tuples accepted in principle:** the recommended exact
   tuples are:
   - `nlp-agent → nlp-agent / QUERY_DATA`
   - `nlp-agent → ir-agent / RETRIEVE_DATA`
   - `nlp-agent → insight-agent / GENERATE_INSIGHT`

   **BLOCKED — Enablement:** keep all three disabled until user authentication,
   delegation, target-side enforcement, and tenant scope are designed and
   approved. Acceptance in principle is not authorization to enable them.

3. **PROPOSED — User permissions:** create distinct `QUERY_DATA`,
   `RETRIEVE_DATA`, and `GENERATE_INSIGHT` permissions. Initially grant all
   three only to `ANALYST`. `USER` and `ADMIN` receive none by default. No
   permission seed or role grant has been changed.

4. **PROPOSED — Identity authority and delegation:** Security Agent remains the
   authority for end-user identity. Before implementation, define the
   delegation assertion's issuer, audience, subject, operation, tenant scope,
   expiry, signing-key management, and replay prevention. These values and
   controls are not finalized.

5. **BLOCKED — IR owner mapping:** define a trusted mapping from the verified
   Security user to IR's owner scope. Do not use a shared owner token across
   users and do not trust caller-supplied owner IDs. Retrieval authorization
   must enforce the mapped scope before any tuple is enabled.

6. **PROPOSED — NLP self-target semantics:** clarify whether
   `nlp-agent → nlp-agent / QUERY_DATA` represents entry-point authorization or
   a genuine internal service call. If it authorizes the entry point, the
   authenticated end-user evidence and NLP service identity must both be
   checked even though no downstream HTTP call occurs. If it represents an
   internal call, document the caller, receiving endpoint, and independent
   service/user authentication required at both sides. Do not treat the
   self-target tuple as a substitute for either identity check.

7. **BLOCKED — Retrieval evidence contract:** keep IR text snippets separate
   from structured business rows; no fabricated rows. Choose and approve either
   a structured retrieval adapter that returns actual rows compatible with
   Insight's metric calculations, or an explicitly approved text-only Insight
   path with suitable uncertainty behavior. Preserve retrieval identifiers and
   relevance scores in a defined evidence contract.

## 10. Decisions still requiring project-owner approval

- Confirm NLP as the initial orchestrator.
- Approve the three exact service tuples, with activation deferred until the
  identity, delegation, target enforcement, and tenant controls are complete.
- Approve the three separate permissions and the initial `ANALYST`-only grants.
- Approve Security Agent as identity authority and finalize all delegation
  assertion claims and security controls.
- Define the trusted Security-user-to-IR-owner mapping and tenant scope.
- Decide the meaning and authentication requirements of the NLP self-target
  tuple.
- Choose structured retrieval rows or an explicitly approved text-only Insight
  path.

**Phase 12D-2 remains blocked** until the required approvals and the identity,
delegation, target-enforcement, tenant/data-scope, and retrieval-evidence
designs are complete. No human decision is marked approved in this document.
