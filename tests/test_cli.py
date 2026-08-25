from pathlib import Path

import pytest

from lobmm.cli import build_parser, main


def test_cli_simulate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "simulation"
    result = main(
        [
            "--config",
            "configs/baseline.toml",
            "simulate",
            "--seed",
            "9",
            "--events",
            "50",
            "--output",
            str(output),
        ]
    )
    assert result == 0
    assert (output / "summary.json").exists()
    assert '"seed": 9' in capsys.readouterr().out


def test_cli_sweep_commands(tmp_path: Path) -> None:
    for command, filename in (
        ("spread-sweep", "spread-sweep.csv"),
        ("gamma-sweep", "gamma-sweep.csv"),
    ):
        assert (
            main(
                [
                    command,
                    "--runs",
                    "1",
                    "--events",
                    "20",
                    "--workers",
                    "1",
                    "--output",
                    str(tmp_path / command),
                ]
            )
            == 0
        )
        assert (tmp_path / command / "raw" / filename).exists()


def test_parser_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
