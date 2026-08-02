from __future__ import annotations

import pytest

import mlip_cell_runner as runner


BASE_ARGS = [
    "run-cell",
    "--run-id", "run-a",
    "--cell-id", "run-a:baseline:energy_volume:chgnet",
    "--row-id", "energy_volume",
    "--mlip-id", "chgnet",
]


@pytest.mark.parametrize("flag", ["--run-id", "--cell-id", "--row-id", "--mlip-id"])
def test_duplicate_identity_flags_fail_closed(flag: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        runner.parse_args([*BASE_ARGS, flag, "attacker-controlled"])

    assert exc.value.code == 2
    assert f"duplicate {flag} argument" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--run-id", "--cell-id", "--row-id", "--mlip-id"])
def test_mixed_form_duplicate_identity_flags_fail_closed(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        runner.parse_args([*BASE_ARGS, f"{flag}=attacker-controlled"])

    assert exc.value.code == 2
    assert f"duplicate {flag} argument" in capsys.readouterr().err


def test_dangling_identity_flag_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        runner.parse_args(["run-cell", "--run-id"])

    assert exc.value.code == 2
    assert "expected one argument" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--run-i", "--cell-i", "--row-i", "--mlip-i"])
def test_abbreviated_identity_flags_cannot_override_validated_values(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        runner.parse_args([*BASE_ARGS, flag, "attacker-controlled"])

    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
