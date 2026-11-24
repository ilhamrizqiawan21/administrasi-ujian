# System blueprint — visual maps
Render Mermaid in GitHub or compatible Markdown viewer. This is a planning artifact, not executable schema.

## Application architecture
```mermaid
flowchart TD
  U[Operator / Panitia] --> W[Windows desktop: pywebview + WebView2]
  W --> R[React + TypeScript UI]
  R --> B[Typed bridge / allowlisted invoke]
  B --> S[Application services / validation / transaction]
  S --> M[Exam and roster domains]
  S --> A[Allocation and scheduling engines]
  S --> D[Document and template factory]
  S --> F[Operations, finance, LPJ]
  S --> J[Bounded job worker]
  M --> DB[(SQLite / SQLAlchemy / Alembic)]
  A --> DB
  D --> DB
  F --> DB
  J --> DB
  J --> FS[Local assets, reports, backups]
  D --> FS
  FS --> O[DOCX / PDF / XLSX / ZIP]
```
## Data lineage
```mermaid
flowchart LR
  M[Master data] --> E[Exam snapshot]
  E --> R[Requirements and groups]
  R --> P[Draft plan]
  P --> S[Sessions and room seats]
  S --> I[Invigilator assignments]
  I --> V{Independent validation}
  V -->|Conflict| P
  V -->|Valid| PUB[Published plan version]
  PUB --> DOC[Cards, seating, schedules, letters]
  PUB --> ACT[Actual attendance and incidents]
  ACT --> BA[Minutes and handovers]
  ACT --> H[Approved honorarium]
  H --> FIN[Posted finance ledger]
  BA --> L[LPJ]
  FIN --> L
  L --> ARC[Immutable archive]
  DOC --> ARC
```
## Core entity relationships (simplified)
```mermaid
erDiagram
  INSTITUTIONS ||--o{ EXAMS : owns
  INSTITUTIONS ||--o{ STUDENTS : registers
  EXAMS ||--o{ EXAM_PEOPLE : snapshots
  EXAM_PEOPLE ||--o| EXAM_PARTICIPANTS : eligible
  EXAMS ||--o{ PLANS : versions
  PLANS ||--o{ SESSIONS : schedules
  SESSIONS ||--o{ ROOM_SESSIONS : occupies
  EXAM_ROOMS ||--o{ ROOM_SESSIONS : hosts
  EXAM_PARTICIPANTS ||--o{ PARTICIPANT_SITTINGS : attends
  ROOM_SESSIONS ||--o{ PARTICIPANT_SITTINGS : contains
  ROOM_SESSIONS ||--o{ INVIGILATION_SLOTS : requires
  INVIGILATION_SLOTS ||--o| INVIGILATIONS : assigns
  PARTICIPANT_SITTINGS ||--o| PARTICIPANT_ATTENDANCE : records
  ROOM_SESSIONS ||--o| SESSION_REPORTS : documents
  EXAMS ||--o{ TASKS : tracks
  EXAMS ||--o{ SUBMISSION_ITEMS : expects
  EXAMS ||--o{ LEDGER_ENTRIES : accounts
  EXAMS ||--o{ DOCUMENT_RUNS : generates
```
Refer to `03-DATABASE.md` for authoritative logical table names, FK cardinality details and invariants. These diagrams intentionally omit support entities and show only main flows.

## Release flow
```mermaid
flowchart LR
  A[Approved issue] --> B[Branch + failing test]
  B --> C[Implementation]
  C --> D[Unit and integration tests]
  D --> E[Independent review]
  E --> F[Windows native smoke]
  F --> G[Owner approval / merge]
  G --> H[Offline installer / pilot]
  H --> I[UAT and release gate]
```
