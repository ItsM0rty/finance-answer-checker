import io
import json

from mock_mcp.server import handle_request


def test_stdio_tools_list(capsys):
    msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    handle_request(msg)
    out = capsys.readouterr().out.strip()
    resp = json.loads(out.splitlines()[-1])
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "list_transactions" in names
