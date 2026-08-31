import json

from risk_generator.client import StreamResult, load_jsonl, write_results


def test_jsonl_io(tmp_path) -> None:
    source = tmp_path / "transactions.jsonl"
    source.write_text('{"transactionId":"TX-1"}\n{"transactionId":"TX-2"}\n')
    assert [row["transactionId"] for row in load_jsonl(source)] == ["TX-1", "TX-2"]

    output = tmp_path / "results.jsonl"
    write_results(output, [StreamResult("TX-1", "created", 201, 1, {"status": "ALLOW"})])
    assert json.loads(output.read_text())["outcome"] == "created"
