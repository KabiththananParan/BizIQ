# IR-01 — Retrieval Accuracy

- **Test objective:** Verify that the IR Agent retrieves the most relevant evidence for a known query.
- **Component:** IR Agent `POST /search` (`http://127.0.0.1:8002/search`).
- **Preconditions:** A reachable local IR service, a populated synthetic datasource, and credentials accepted by that service.
- **Input / attack scenario:** `Product Alpha revenue January`.
- **Expected behaviour:** The datasource containing matching Product Alpha January revenue evidence is returned with an appropriate rank and score.
- **Actual behaviour:** **No HTTP response.** The health probe to `http://127.0.0.1:8002/health` failed to connect (`curl.exe` exit status 7). The `/search` request was not sent, so there is no response body, ranking, or score to report. No datasource or credential was verified against a running service.
- **Evidence:** Local probe to `http://127.0.0.1:8002/health` on 2026-10-09 (Asia/Colombo); output: `curl: (7) Failed to connect to 127.0.0.1:8002 ... Could not connect to server`.
- **Observations:** The IR source defines `/search` as a bearer-authenticated endpoint returning `{query, results}`; each result includes `datasource_id`, `name`, `snippet`, cosine `score`, and `matched_terms`. The documented development fallback token is not evidence of an accepted credential, and no synthetic datasource was populated for this run. Retrieval quality therefore remains unassessed.
- **Outcome:** **INCONCLUSIVE** — service unreachable; expected preconditions were not met.
- **Vulnerability identified:** None. This run provides no retrieval or security behavior evidence.
- **Impact:** No impact finding can be made from this run.
- **Likelihood:** Not assessed; no issue was demonstrated.
- **Severity:** Informational (test execution blocked; not a vulnerability rating).
- **Recommended mitigation:** Start the IR service on port 8002 using an isolated test database; populate it with a synthetic Product Alpha January revenue datasource and at least one nonmatching distractor; configure a dedicated test bearer token; capture the `/search` HTTP status and JSON response, including result order, scores, and matched terms. Do not use production data or credentials.
- **Retest result:** Pending; rerun after the service and test fixtures are available.
