# Demo case transcripts

ASSUMPTION: this schema and these tool names are a stand-in built from public product descriptions. Seapoint's real MCP tool names and schemas are not public (no docs, no public repo, not in the MCP registry).

These JSON files are synthetic agent transcripts built from `mock_mcp` dummy data via `cases/generate.py`. They illustrate definitional mismatches (wrong trailing window, gross/net mix-up, pending/FX/provenance axes). They are not observed behaviour from Seapoint or any live MCP.

| File | Scenario | Primary metric |
|------|----------|----------------|
| `01_correct_stated.json` | Correct under stated 3mo bank net burn | net_burn, runway |
| `02_trailing_window_1mo.json` | 1-month window vs stated 3-month | net_burn |
| `03_gross_vs_net.json` | Gross burn quoted as net | net_burn |
| `04_pending_included.json` | Pending SaaS included | net_burn |
| `05_fx_latest_rate.json` | FX at latest rate | net_burn |
| `06_fx_not_converted.json` | FX none_mixed (foreign minor summed) | net_burn |
| `07_uncategorised_dropped.json` | Uncategorised lines excluded | net_burn |
| `08_union_double_count.json` | Bank+ledger union without dedupe | gross_burn |
| `09_ledger_stale_runway.json` | Stale ledger cash in runway | runway_months |
| `10_overdue_includes_future.json` | Not-yet-due invoice in overdue | overdue_total |
| `11_overdue_wrong_asof.json` | Overdue as-of wrong date | overdue_total |
| `12_vat_on_gross.json` | VAT on gross spend | vat_estimate |
| `13_arithmetic_slip.json` | Small arithmetic error | net_burn |
| `14_fabricated.json` | Plausible but wrong figure | net_burn |
| `15_one_off_excluded.json` | One-off handling differs | net_burn |
| `16_scenario_hire.json` | Scenario hire omitted from runway | runway_months |
| `17_raw_no_provenance.json` | Raw tool mode, no provenance | UNCHECKABLE |
| `18_no_definition_stated.json` | No stated definition | ambiguity |

Regenerate: `python cases/generate.py`
