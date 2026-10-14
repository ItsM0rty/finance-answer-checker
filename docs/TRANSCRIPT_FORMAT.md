# Transcript format

A transcript is one JSON object describing an agent turn: tool calls, optional stated definition, and the final natural-language answer.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `final_answer` | string | Agent text from which numeric claims are extracted. |
| `tool_calls` | array | Ordered list of `{ "tool_call": {...}, "tool_output": {...} }` pairs. |

Each `tool_call` object should include at least `name` (tool name matching the adapter) and optional `args`.

## Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | string | Label for reports. |
| `as_of_date` | string | ISO date (`YYYY-MM-DD`) for window and overdue logic. Defaults to mock data as-of when omitted in examples only. |
| `stated_definition` | object | Definition the agent claims to use (see below). |
| `scenario_hire_cost_minor` | integer | Extra monthly cost in minor units for runway scenario checks. |
| `expected_verdict` | object | Map metric name to expected verdict (demo cases only). |

## `stated_definition` object

| Field | Default | Values |
|-------|---------|--------|
| `window_months` | 3 | 1, 3, 6 (search may use other windows in grid). |
| `include_pending` | false | Include pending transactions in burn. |
| `burn_basis` | net | `net` or `gross`. |
| `fx_policy` | transaction_date | `transaction_date`, `latest`, `none_mixed`. |
| `include_uncategorised` | true | Count uncategorised spend. |
| `source` | bank | `bank`, `ledger`, or `union`. |
| `exclude_one_offs` | false | Drop one-off transactions. |
| `union_dedupe` | true | When `source` is `union`, dedupe matched bank/ledger pairs. |

If the transcript omits `stated_definition`, pass flags on the CLI (`--window`, `--net`, `--exclude-pending`, etc.) or `--definition-file path.json`.

## Minimal example

See [examples/minimal_transcript.json](../examples/minimal_transcript.json) or run:

```powershell
python -m verifier init-example
```

## Check command

```powershell
python -m verifier check examples/minimal_transcript.json --adapter adapters/mock.yaml
python -m verifier check my.json --adapter adapters/mock.yaml --json
python -m verifier check my.json --window 3 --net --exclude-pending --fx transaction_date
```
