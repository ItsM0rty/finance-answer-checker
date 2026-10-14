# Adapter mapping

ASSUMPTION: this schema and these tool names are a stand-in built from public product descriptions. Seapoint's real MCP tool names and schemas are not public (no docs, no public repo, not in the MCP registry).

## Purpose

The verifier consumes a **canonical** model (`Transaction`, `Invoice`, `Balance`). An adapter YAML maps each assumed tool's JSON shape into that model: list keys, field names, sign convention (`negative_outflow` means outflows are negative minor units), and optional embedded `fx_rates`.

## Editing for your MCP

1. Copy `adapters/mock.yaml` to e.g. `adapters/live.yaml`.
2. Under `tools`, set each value to the tool name your MCP exposes for that role (transactions, invoices, balances, FX).
3. Under `fields`, point each canonical field at the path/key in that tool's response (adjust `transactions_list`, date fields, amount in minor units).
4. Set `amount_sign` if the vendor uses positive outflows.
5. Run: `python -m verifier check path/to/transcript.json --adapter adapters/live.yaml`

If the live MCP returns no provenance (`source`, `status`, `matched`), the checker will mark some axes **UNCHECKABLE**. That is intentional; it surfaces which definition axes cannot be tested from raw numbers alone.
