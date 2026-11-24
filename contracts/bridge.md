# Bridge API blueprint
Use single exposed `invoke(request)` or explicitly enumerated methods; choose during spike, never expose arbitrary Python objects. Request `{method,request_id, payload}`. Response `{ok:true,request_id,data}` or `{ok:false,request_id,error:{code,message,field_errors?,details?,retryable}}`. Version handshake; no raw exceptions or stack traces. Pydantic method-specific schemas, TS generated from JSON schema or maintained with contract tests. IDs strings, date ISO, amount IDR integer. Validation and scope enforced server-side; `expected_revision` required for changes to mutable resources. Unknown method returns METHOD_NOT_ALLOWED. `request_id` correlation not idempotency by itself; mutations needing retry use operation_key persisted. List endpoints support page/page_size <=200, sort allowlist and query/filter. Long ops return job_id; poll status, cancel. File dialogs return opaque handle not unrestricted path; backend rechecks extension and scope. No network endpoints.

| Method | Payload summary | Result | Rules |
|---|---|---|---|
| app.info | none | version/schema/bridge | compatibility |
| institution.list/create/update | profile/revision | scoped profile | validate identity |
| master.list/save/archive | kind, institution, fields/revision | row/page | allowed kind, reference check |
| imports.preview | kind, file_handle, mapping | preview_id, errors, counts | no write |
| imports.commit | preview_id, policy, revision | job_id | stale rejection |
| exams.create/transition/clone | config/id/state/revision | exam | lifecycle |
| plans.create/validate/publish | exam_id, plan_id, revision | validation/plan | independent hard check |
| solver.start | plan_id, kind, rules, seed, limit | job_id | draft only |
| seats.swap | plan_id, source_slot, dest_slot, revision | plan revision | lock/constraint checks |
| assignments.replace | slot_id, person_id, revision | assignment | overlap check |
| committee.save/tasks.save/submissions.receive | scoped fields | updated record | valid states |
| attendance.save | room_session_id, records, revision | counts | actual only |
| reports.finalize | room_session_id, revision | report | derived counts |
| finance.post/reverse | entry, operation_key, revision | ledger entry | approvals/idempotency |
| documents.preview | doc_type, scope, template_id, plan_id | preview asset, warnings | no numbering |
| documents.generate | context, output_format, operation_key | job_id | scope & version |
| jobs.status/cancel | job_id | job | owned scope |
| files.pick | purpose | handle | native dialog, allowlist |
| backup.create/restore | workspace/handle | job_id | verify & stage |
| licensing.activate | handle | entitlement | offline signature |

Error codes: VALIDATION, NOT_FOUND, CONFLICT, STALE_REVISION, INFEASIBLE, PERMISSION_DENIED, STORAGE_FULL, FILE_INVALID, TEMPLATE_INVALID, CANCELLED, TIMEOUT, INTERNAL. Message Indonesian, detailed field errors; internal log redacted correlation. Contract schema file covers envelope only; actual per-method schemas must be added as backlog tasks are implemented.
