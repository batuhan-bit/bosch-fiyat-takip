import json

from bosch_tracker import main as main_module


class FakeMediaMarktSource:
    def __init__(self, client) -> None:
        self.client = client

    def fetch_all(self) -> list:
        return []


def test_dry_run_does_not_require_local_price_lists(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main_module, "MediaMarktSource", FakeMediaMarktSource)

    main_module.run(dry_run=True, output_json=None)

    assert json.loads(capsys.readouterr().out) == {"products": 0}
