# Smell-check eval — results

**Overall verdict-match accuracy:** 14/17 = 82.4%


## Accuracy by ground-truth label


| Label | Total | Match | Accuracy |
|---|---|---|---|
| SLICE | 8 | 8 | 100.0% |
| CONSIDER | 4 | 3 | 75.0% |
| NO_SLICE | 3 | 1 | 33.3% |
| HALT | 2 | 2 | 100.0% |

## Per-case results


| Case | Label | Domain | Predicted | Actual | Match | Notes |
|---|---|---|---|---|---|---|
| ADMIN-001 | CONSIDER | admin | `consider` | `consider` | ✓ | +mixed_crud |
| ADMIN-002 | NO_SLICE | admin | `no-slice` | `no-slice` | ✓ | — |
| API-001 | SLICE | api | `slice` | `slice` | ✓ | −sprawling_description |
| API-002 | HALT | api | `halt-fix-schema` | `halt-fix-schema` | ✓ | — |
| AUTH-001 | SLICE | auth | `slice` | `slice` | ✓ | +mixed_crud; −sprawling_description |
| AUTH-002 | CONSIDER | auth | `consider` | `consider` | ✓ | −sprawling_description |
| DOC-001 | SLICE | document | `slice` | `slice` | ✓ | −sprawling_description |
| DOC-002 | NO_SLICE | document | `no-slice` | `consider` | ✗ | +compound_gwt, multiple_personas |
| IMPORT-001 | SLICE | data-import | `slice` | `slice` | ✓ | −mixed_crud, sprawling_description |
| MOBILE-001 | SLICE | mobile | `slice` | `slice` | ✓ | +multiple_personas; −sprawling_description |
| MOBILE-002 | HALT | mobile | `halt-fix-schema` | `halt-fix-schema` | ✓ | — |
| NOTIF-001 | SLICE | notifications | `slice` | `slice` | ✓ | −sprawling_description |
| NOTIF-002 | CONSIDER | notifications | `consider` | `consider` | ✓ | +multiple_personas; −sprawling_description |
| ONBOARD-001 | SLICE | onboarding | `slice` | `slice` | ✓ | +multiple_personas; −sprawling_description |
| REPORT-001 | SLICE | reporting | `slice` | `slice` | ✓ | −sprawling_description |
| REPORT-002 | CONSIDER | reporting | `consider` | `slice` | ✗ | +multi_verb_title |
| SEARCH-001 | NO_SLICE | search | `no-slice` | `slice` | ✗ | +compound_gwt, mixed_crud, multi_verb_title, multiple_personas |

## Mismatch analysis


### DOC-002
- Predicted: `no-slice`
- Actual: `consider`
- Triggered smells (with evidence):
  - **compound_gwt**: 1 compound clause(s) found — AC #1 'then': 'the document is rendered to PDF and downloads with the filename matching the document title'
  - **multiple_personas**: 2 distinct personas in Given clauses: permission, user

### REPORT-002
- Predicted: `consider`
- Actual: `slice`
- Triggered smells (with evidence):
  - **multi_verb_title**: title contains 2 distinct action verbs: add, export
  - **compound_gwt**: 1 compound clause(s) found — AC #1 'then': "a CSV is generated containing all rows matching the filters and using the report's column ordering and currency/date formatting, and the file downloads with a name including the filter date range"

### SEARCH-001
- Predicted: `no-slice`
- Actual: `slice`
- Triggered smells (with evidence):
  - **multi_verb_title**: title contains 2 distinct action verbs: add, search
  - **compound_gwt**: 1 compound clause(s) found — AC #1 'then': 'the input is cleared and the search results refresh to show the unfiltered list'
  - **multiple_personas**: 2 distinct personas in Given clauses: bar, user
  - **mixed_crud**: 3 CRUD operations present: create, delete, read
