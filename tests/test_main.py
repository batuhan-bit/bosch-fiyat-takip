import json

import pytest

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


def test_error_logging_failure_does_not_hide_original_error(monkeypatch, capsys) -> None:
    class FailingSheetsClient:
        def read_reference_data(self):
            raise RuntimeError("asıl hata")

        def log_error(self, stage, message):
            raise RuntimeError("kayıt hatası")

    monkeypatch.setattr(main_module, "MediaMarktSource", FakeMediaMarktSource)
    monkeypatch.setattr(main_module, "GoogleSheetsClient", FailingSheetsClient)

    with pytest.raises(RuntimeError, match="asıl hata"):
        main_module.run(dry_run=False, output_json=None)

    assert "kayıt hatası" in capsys.readouterr().err
