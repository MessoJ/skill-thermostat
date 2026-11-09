"""Unit tests for Milestone 4 Step 1: Multi-Language Friction (Python AST & Go) and External Target Adapter."""
from __future__ import annotations

from skill_thermostat.cli import main as cli_main
from skill_thermostat.friction import (
    LEVEL_FULL,
    LEVEL_PROBE_FAULT,
    LEVEL_SKELETON,
    apply_with_metadata,
)
from skill_thermostat.ledger import Ledger
from skill_thermostat.workspace import (
    REFERENCE_GO_SOURCE,
    REFERENCE_TARGET_SOURCE,
    inject_on_disk_intervention,
    restore_reference_target,
    verify_physical_edit,
)


def test_go_skeleton_strips_function_bodies_to_panic():
    res = apply_with_metadata(REFERENCE_GO_SOURCE, mode=LEVEL_SKELETON, language="go")
    assert res.mode == LEVEL_SKELETON
    assert res.metadata["language"] == "go"
    assert res.metadata["mutated"] is True
    assert res.metadata["stripped_functions"] == 2
    assert "VerifyChainWindow" in res.metadata["functions_stripped"]
    assert "ClampQuotaWindow" in res.metadata["functions_stripped"]
    assert 'panic("thermostat: complete unassisted")' in res.code
    assert "func VerifyChainWindow(scores []float64, floor float64, minCount int) bool {" in res.code


def test_go_probe_fault_flips_boundary_operator_and_records_metadata():
    res = apply_with_metadata(
        REFERENCE_GO_SOURCE,
        mode=LEVEL_PROBE_FAULT,
        seed=0,
        target_function="VerifyChainWindow",
        language="go",
    )
    assert res.mode == LEVEL_PROBE_FAULT
    assert res.metadata["language"] == "go"
    assert res.metadata["mutated"] is True
    assert res.metadata["function_name"] == "VerifyChainWindow"
    assert res.metadata["original_sym"] in ("<", "<=", "==", "!=", ">", ">=")
    assert res.metadata["mutated_sym"] != res.metadata["original_sym"]
    assert res.metadata["lineno"] >= 1
    assert res.code != REFERENCE_GO_SOURCE


def test_cli_attach_inject_and_restore_on_external_go_and_python_files(tmp_path):
    db_path = tmp_path / ".thermostat.db"
    ext_go = tmp_path / "ledger_guard.go"
    ext_py = tmp_path / "parser_util.py"

    ext_go.write_text(REFERENCE_GO_SOURCE, encoding="utf-8")
    py_clean = (
        "def parse_frame_length(header_len: int, min_len: int = 4) -> bool:\n"
        "    if header_len < min_len:\n"
        "        return False\n"
        "    return header_len == min_len\n"
    )
    ext_py.write_text(py_clean, encoding="utf-8")

    # 1. Attach external Go file via CLI
    rc_attach = cli_main(
        [
            "attach",
            str(ext_go),
            "--repo-path",
            str(tmp_path),
            "--domain",
            "go:ledger",
            "--test-cmd",
            "go test ./...",
            "--db",
            str(db_path),
        ]
    )
    assert rc_attach == 0
    ledger = Ledger(db_path=db_path)
    att = ledger.get_attachment()
    assert att is not None
    assert att["domain"] == "go:ledger"
    assert att["target_file"] == str(ext_go)

    # 2. Inject skeleton into Go file via CLI
    rc_go_skel = cli_main(
        [
            "inject",
            "--target",
            str(ext_go),
            "--mode",
            "skeleton",
            "--domain",
            "go:ledger",
            "--db",
            str(db_path),
        ]
    )
    assert rc_go_skel == 0
    assert 'panic("thermostat: complete unassisted")' in ext_go.read_text(encoding="utf-8")

    # 3. Restore Go file from clean snapshot and inject probe fault
    rc_go_rest = cli_main(["restore", "--target", str(ext_go), "--db", str(db_path)])
    assert rc_go_rest == 0
    assert ext_go.read_text(encoding="utf-8") == REFERENCE_GO_SOURCE

    rc_go_probe = cli_main(
        [
            "inject",
            "--target",
            str(ext_go),
            "--mode",
            "probe",
            "--domain",
            "go:ledger",
            "--seed",
            "1",
            "--db",
            str(db_path),
        ]
    )
    assert rc_go_probe == 0
    go_mutated = ext_go.read_text(encoding="utf-8")
    assert go_mutated != REFERENCE_GO_SOURCE

    active_go = ledger.get_active_intervention()
    assert active_go is not None
    assert active_go["domain"] == "go:ledger"
    assert active_go["clean_hash"] != ""
    assert active_go["fault_metadata"]["language"] == "go"

    # Verify physical edit detection on Go file (unedited fail vs repaired pass)
    phys_unedited = verify_physical_edit(
        served_code=go_mutated,
        current_code=go_mutated,
        mode=LEVEL_PROBE_FAULT,
        fault_metadata=active_go["fault_metadata"],
        test_exit_code=1,
        time_to_green_sec=12.0,
    )
    assert phys_unedited["edit_distance_ratio"] == 0.0
    assert phys_unedited["verification_status"] == "PROBE_FAILED_UNEDITED"

    phys_repaired = verify_physical_edit(
        served_code=go_mutated,
        current_code=REFERENCE_GO_SOURCE,
        mode=LEVEL_PROBE_FAULT,
        fault_metadata=active_go["fault_metadata"],
        test_exit_code=0,
        time_to_green_sec=14.5,
    )
    assert phys_repaired["edit_distance_ratio"] > 0.0
    assert phys_repaired["probe_caught"] is True
    assert phys_repaired["verification_status"] == "VERIFIED_PROBE_CATCH"

    # Restore Go file cleanly
    restore_reference_target(ext_go, ledger=ledger)
    assert ext_go.read_text(encoding="utf-8") == REFERENCE_GO_SOURCE

    # 4. Inject probe and skeleton into external Python file under py:parser domain
    rc_py_probe = cli_main(
        [
            "inject",
            "--target",
            str(ext_py),
            "--mode",
            "probe",
            "--domain",
            "py:parser",
            "--db",
            str(db_path),
        ]
    )
    assert rc_py_probe == 0
    assert ext_py.read_text(encoding="utf-8") != py_clean
    active_py = ledger.get_active_intervention()
    assert active_py is not None
    assert active_py["domain"] == "py:parser"
    assert active_py["fault_metadata"]["language"] == "py"

    rc_py_rest = cli_main(["restore", "--target", str(ext_py), "--db", str(db_path)])
    assert rc_py_rest == 0
    assert ext_py.read_text(encoding="utf-8") == py_clean


def test_export_field_log_jsonl_and_sha256_chain_verification(tmp_path):
    from tools.export_field_log import export_field_log

    db_path = tmp_path / ".thermostat.db"
    out_jsonl = tmp_path / "dogfood_telemetry_v1.jsonl"
    summary = export_field_log(db_path=db_path, out_jsonl=out_jsonl)

    assert out_jsonl.exists()
    assert summary["total_events"] >= 14
    assert summary["chain_verification"]["verified"] is True

    domains = {r["domain"] for r in summary["domain_rows"]}
    assert {"py:algo", "go:ledger", "py:parser"}.issubset(domains)

    # Verify raw paths are stripped to path_sha256:...
    for rec in summary["records"]:
        assert str(rec["target_path_sha256"]).startswith("path_sha256:")


def test_export_loi_metrics_10_portal_fields_word_count_lock(tmp_path):
    from tools.export_loi_metrics import (
        PORTAL_FIELD_ORDER,
        assert_portal_word_counts,
        export_loi_file,
    )

    db_path = tmp_path / ".thermostat.db"
    out_md = tmp_path / "MOZILLA_LOI_DRAFT.md"
    sections, md = export_loi_file(db_path=db_path, out_path=out_md)
    assert out_md.exists()
    assert_portal_word_counts(sections)

    pf = sections["portal_fields"]
    assert len(pf) == 10
    for key in PORTAL_FIELD_ORDER:
        assert key in pf
        assert 0 < pf[key]["word_count"] <= pf[key]["limit"]

