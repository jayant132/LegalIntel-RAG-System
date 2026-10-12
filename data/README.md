# Veridian Global Industries - Legal RAG Practice Corpus (FICTIONAL DATA)

Scenario: fictional multinational "Veridian Global Industries plc". Dataset "as of" 15 December 2024.
All people, companies and figures are invented.

## Folders
- contracts/        MSA (PDF, tables, schedules), DPA (PDF, sub-processor table), NDA (PDF)
- amendments/       Amendment 1 and 2 (DOCX) - they change and partly reverse each other
- hr/               Executive employment agreement + later variation letter (DOCX)
- policies/         Anti-bribery policy v4.0 (DOCX) and v3.1 (TXT, superseded), retention policy (HTML with web boilerplate)
- legal_internal/   Privileged legal memo (PDF), board minutes (DOCX)
- correspondence/   Email thread (quoted replies, typos), Slack export, rough meeting notes
- registers/        Contract register (XLSX, partly stale), SLA report (XLSX, 2 sheets)
- scanned/          Image-only scanned lease (needs OCR)
- eval/             document_manifest.csv (metadata + ACL groups), golden_questions.json (40 Q&A with sources)

## Difficulty features built in
1. Temporal reasoning: the answer depends on MSA -> A1 -> A2 order (latest wins, A2 reverses part of A1).
2. Stale data: the contract register disagrees with the contracts.
3. Non-authoritative sources: email, chat and notes contain wrong or non-binding statements.
4. Tables: fees, SLA bands, sub-processors, scorecards, retention periods.
5. Scanned PDF: skewed, noisy, stamped, image only.
6. Messy HTML: nav menus, cookie banner, footer.
7. Version conflict: two policy versions with different thresholds (filter on status).
8. Cross-references and defined terms (Critical Service Failure -> Schedule 2 para 4(b) -> clause 12.2(b)).
9. Calculations (service credits, caps, vested RSUs) and aggregation questions (better suited to SQL/pandas).
10. Access control: privileged / HR-restricted / board-restricted documents.
11. Unanswerable and trap questions (abstention, no hallucinated penalties, not over-abstaining).
