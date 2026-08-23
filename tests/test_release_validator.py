from __future__ import annotations

import importlib.util
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_release_candidate.py"

SPEC = importlib.util.spec_from_file_location("release_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
release_validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_validator)


class ReleaseValidatorTests(unittest.TestCase):
    def test_run_validation_executes_each_check_once(self) -> None:
        validator_names = (
            "validate_required_files",
            "validate_file_shape",
            "validate_text_safety",
            "validate_metadata",
            "validate_json_artifacts",
            "validate_logo_provenance",
            "validate_evidence_bindings",
            "validate_sample_receipt",
            "validate_demo",
            "validate_activation_golden",
            "validate_publication_outcome_gate",
        )

        with ExitStack() as stack:
            validators = {
                name: stack.enter_context(mock.patch.object(release_validator, name, return_value=[]))
                for name in validator_names
            }
            png_validator = stack.enter_context(
                mock.patch.object(
                    release_validator,
                    "validate_png_assets",
                    return_value=(["icon.png: expected 512x512, got 256x256"], {}),
                )
            )
            result = release_validator.run_validation()

        for validator in validators.values():
            validator.assert_called_once_with()
        png_validator.assert_called_once_with()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["root"], ".")
        self.assertEqual(result["checks"]["png_assets"], "fail")
        self.assertEqual(result["errors"], ["icon.png: expected 512x512, got 256x256"])

    def test_missing_metadata_prerequisites_return_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = root / "plugins" / "agent-routekit"
            with (
                mock.patch.object(release_validator, "ROOT", root),
                mock.patch.object(release_validator, "PLUGIN", plugin),
            ):
                errors = release_validator.validate_metadata()

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("metadata JSON failed:"), errors)

    def test_missing_png_prerequisite_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected = {"plugins/agent-routekit/assets/icon.png": (512, 512, False)}
            with (
                mock.patch.object(release_validator, "ROOT", root),
                mock.patch.object(release_validator, "EXPECTED_PNGS", expected),
            ):
                errors, hashes = release_validator.validate_png_assets()

        self.assertEqual(errors, ["PNG asset is missing: plugins/agent-routekit/assets/icon.png"])
        self.assertEqual(hashes, {})

    def test_product_revision_excludes_validation_receipts(self) -> None:
        baseline = release_validator.product_revision_sha256()
        receipt = REPO_ROOT / "validation" / "temporary-test-receipt.json"
        receipt.write_text('{"status":"pass"}\n', encoding="utf-8")
        try:
            self.assertEqual(release_validator.product_revision_sha256(), baseline)
        finally:
            receipt.unlink()

    def test_product_revision_normalizes_text_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = root / "README.md"
            text.write_bytes(b"one\ntwo\n")
            with mock.patch.object(release_validator, "ROOT", root):
                lf_revision = release_validator.product_revision_sha256()
                text.write_bytes(b"one\r\ntwo\r\n")
                crlf_revision = release_validator.product_revision_sha256()

        self.assertEqual(lf_revision, crlf_revision)

    def test_file_shape_ignores_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / ".git" / "objects" / "pack" / "candidate.pack"
            pack.parent.mkdir(parents=True)
            pack.write_bytes(b"x" * (release_validator.MAX_FILE_BYTES + 1))
            with mock.patch.object(release_validator, "ROOT", root):
                errors = release_validator.validate_file_shape()

        self.assertEqual(errors, [])

    def test_evidence_binding_rejects_stale_product_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            validation = root / "validation"
            validation.mkdir()
            for relative in release_validator.REQUIRED_EVIDENCE:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"status":"pass","product_revision_sha256":"stale"}', encoding="utf-8")
            with mock.patch.object(release_validator, "ROOT", root):
                errors = release_validator.validate_evidence_bindings()

        self.assertEqual(len(errors), len(release_validator.REQUIRED_EVIDENCE))
        self.assertTrue(all("stale product revision evidence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
