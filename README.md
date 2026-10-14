# finance-answer-checker

Independent definition checker for agents that answer finance questions through an MCP-style connector. Runway, burn, and overdue totals depend on choices that are often left implicit (gross vs net, trailing window, pending vs posted, FX date, bank vs ledger). This tool makes the definition explicit and checkable by recomputing under the stated definition and a grid of alternatives, then naming the likely definitional cause when the agent figure fits a different variant.

## Assumptions

The MCP server here is a mock, and its schema is my assumption. Tool names such as `list_transactions` and the field shapes in `adapters/mock.yaml` are invented. I don't know whether a real finance MCP returns raw or precomputed numbers, or whether it includes timestamps and sources per figure. Everything in `cases/` is a synthetic transcript written to show common definitional mistakes, not behaviour observed from any product.

## The problem

The same question ("what is our runway?") can yield several defensible answers from the same underlying transactions. On the mock Nimbus SaaS dataset as of 2026-10-01, with GBP 12,000 cash at the bank:

| Definition (short) | Net burn / month | Runway |
|--------------------|------------------|--------|
| 3-month bank net, posted only (typical stated) | GBP 2,206.66 | 5.44 mo |
| 1-month bank net | GBP 6,350.00 | 1.89 mo |
| 3-month bank net, pending included | GBP 2,356.66 | 5.09 mo |
| 3-month ledger net (stale cash source) | GBP 406.66 | 25.82 mo |

An agent can pick one row without saying which. The checker extracts the figure from the answer, recomputes under the definition the agent claims (if any), and searches other variants when numbers disagree.

## Run it

```powershell
pip install -r requirements.txt
python -m verifier demo
python -m pytest -q
```

Makefile targets (optional on Windows, use the `python -m` lines above instead):

```text
make install
make demo
make test
make check T=cases/01_correct_stated.json
```

## What the demo shows

```text
Case                        Metric     Agent answer   Recomputed     Verdict                   Likely cause
-----------------------------------------------------------------------------------------------------------------------------------------------
01_correct_stated           net_burn   GBP 2,206.66   GBP 2,206.66   MATCHES_STATED_DEFINITION Stated definition
01_correct_stated           runway     5.44 mo        5.44 mo        MATCHES_STATED_DEFINITION Stated definition
01_correct_stated           cash       GBP 12,000.00  GBP 12,000.00  MATCHES_STATED_DEFINITION Stated definition
02_trailing_window_1mo      net_burn   GBP 6,350.00   GBP 2,206.66   MATCHES_OTHER_DEFINITION  trailing 1 month instead of 3
03_gross_vs_net             net_burn   GBP 2,726.66   GBP 2,206.66   MATCHES_OTHER_DEFINITION  Figure matches gross burn under the stated
                                                                                               window, not net burn.
04_pending_included         net_burn   GBP 2,356.66   GBP 2,206.66   MATCHES_OTHER_DEFINITION  pending included
05_fx_latest_rate           net_burn   GBP 2,351.66   GBP 2,206.66   MATCHES_OTHER_DEFINITION  pending included; FX policy latest instead of
                                                                                               transaction_date
06_fx_not_converted         net_burn   GBP 2,083.33   GBP 2,206.66   MATCHES_OTHER_DEFINITION  FX policy none_mixed instead of transaction_date
07_uncategorised_dropped    net_burn   GBP 2,156.66   GBP 2,206.66   MATCHES_OTHER_DEFINITION  uncategorised excluded
08_union_double_count       gross_burn GBP 3,633.33   GBP 2,726.66   MATCHES_OTHER_DEFINITION  source union instead of bank; bank+ledger union
                                                                                               without dedupe
09_ledger_stale_runway      runway     25.82 mo       5.44 mo        MATCHES_OTHER_DEFINITION  source ledger instead of bank
10_overdue_includes_future  overdue    GBP 1,464.00   GBP 1,064.00   MATCHES_OTHER_DEFINITION  overdue includes not-yet-due invoices
11_overdue_wrong_asof       overdue    GBP 0.00       GBP 1,064.00   MATCHES_OTHER_DEFINITION  Overdue total matches an as-of date between
                                                                                               2026-07-03 and 2026-09-01 rather than
                                                                                               2026-10-01.
12_vat_on_gross             vat        GBP 1,636.00   GBP 1,363.33   MATCHES_OTHER_DEFINITION  20% applied to VAT-inclusive spend (VAT not
                                                                                               extracted)
13_arithmetic_slip          net_burn   GBP 2,251.66   GBP 2,206.66   MATCHES_NO_DEFINITION     Arithmetic slip: close to the stated-definition
                                                                                               recompute but outside tolerance.
14_fabricated               net_burn   GBP 99,999.99  GBP 2,206.66   MATCHES_NO_DEFINITION     No tested definition reproduces this figure
                                                                                               within tolerance; likely fabrication or an
                                                                                               unstated definition outside the grid.
15_one_off_excluded         net_burn   GBP 540.00     GBP 2,206.66   MATCHES_OTHER_DEFINITION  one-offs excluded
16_scenario_hire            runway     5.44 mo        1.46 mo        MATCHES_OTHER_DEFINITION  scenario hire cost omitted from runway
17_raw_no_provenance        net_burn   GBP 2,206.66   n/a            UNCHECKABLE               Missing provenance in tool output
17_raw_no_provenance        cash       GBP 12,000.00  n/a            UNCHECKABLE               Missing provenance in tool output
18_no_definition_stated     net_burn   GBP 2,206.66   n/a            MATCHES_OTHER_DEFINITION  Unstated definition (ambiguous)

Demo completed in 0.14s (21 claims)
```

## Bring your own transcript

Save a JSON file with `final_answer` and a list of `tool_call` / `tool_output` pairs. Optional fields: `stated_definition`, `as_of_date`, `scenario_hire_cost_minor`. Full schema: [docs/TRANSCRIPT_FORMAT.md](docs/TRANSCRIPT_FORMAT.md). Minimal sample: [examples/minimal_transcript.json](examples/minimal_transcript.json) (or `python -m verifier init-example`).

```powershell
python -m verifier check examples/minimal_transcript.json --adapter adapters/mock.yaml
python -m verifier check my.json --window 3 --net --exclude-pending --fx transaction_date --json
```

To map a different MCP JSON shape, copy and edit `adapters/mock.yaml` per [adapters/ADAPTER.md](adapters/ADAPTER.md).

## What it catches and what it doesn't

- Claim extraction uses **heuristic regex** on the final answer, not structured model output.
- Matching uses a **0.5% tolerance**; several definitions can land near the same number (residual ambiguity).
- Search is over a **fixed definition grid** (window, pending, gross/net, FX policy, source, union dedupe, uncategorised, one-offs, overdue basis, VAT basis, scenario hire). Custom business rules may sit outside the grid.
- It does **not** verify categorisation correctness against ground truth.
- VAT is a **single-rate simplification** (20% on spend in window).
- Reporting is **single-currency** (GBP with dated FX tables in the adapter).
- It assumes tool outputs are **complete** for the axes being tested.
- A match to an alternative definition is **evidence**, not proof the agent intended that definition.

## Layout

- `mock_mcp/` - deterministic dummy company and stdio JSON-RPC mock server
- `adapters/` - YAML mapping and adapter notes
- `verifier/` - models, metrics, definition search, CLI (`demo`, `check`, `list-cases`, `init-example`)
- `cases/` - 18 synthetic transcripts and `generate.py`
- `docs/` - transcript JSON schema
- `examples/` - minimal transcript for BYO runs
- `tests/` - pytest suite

## Inspiration

Seapoint launched an MCP server in October 2026 that connects agents to live bank and accounting data. It made me think about a small problem. An agent can answer "what is our runway" with a precise-sounding number, but the definition behind it (gross or net burn, which months, pending or posted, which FX rate) is usually invisible. I wanted to see how hard it is to make that definition explicit and checkable.
