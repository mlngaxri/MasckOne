import json
from pathlib import Path
import tempfile
import unittest

from masck_one.release_package import (
    ExportValidationError,
    MANIFEST_NAME,
    development_readiness,
    publish_package,
    validate_checks,
    verify_package,
)


class ReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "package"

    @staticmethod
    def writer(stage):
        (stage / "part.step").write_text("synthetic STEP bytes for file-integrity test\n")
        (stage / "build_report.json").write_text('{"build_scope":"DEVELOPMENT_ONLY"}\n')

    def test_package_hashes_detect_changed_or_missing_step(self):
        publish_package(self.output, self.writer)
        manifest = verify_package(self.output)
        self.assertEqual(set(manifest["files"]), {"part.step", "build_report.json"})
        (self.output / "part.step").write_text("changed")
        with self.assertRaises(ExportValidationError):
            verify_package(self.output)
        (self.output / "part.step").unlink()
        with self.assertRaises(ExportValidationError):
            verify_package(self.output)

    def test_failed_serialization_preserves_previous_completed_package(self):
        publish_package(self.output, self.writer)
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}

        def failed_writer(stage):
            (stage / "part.step").write_text("partial replacement")
            raise RuntimeError("kernel export failed")

        with self.assertRaisesRegex(RuntimeError, "kernel export failed"):
            publish_package(self.output, failed_writer)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})
        verify_package(self.output)

    def test_failed_first_build_creates_no_completed_output(self):
        def failed_writer(stage):
            raise RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            publish_package(self.output, failed_writer)
        self.assertFalse(self.output.exists())

    def test_stale_step_prevents_publication_without_deleting_user_file(self):
        self.output.mkdir()
        stale = self.output / "obsolete.STEP"
        stale.write_text("old source")
        with self.assertRaisesRegex(ExportValidationError, "unlisted STEP"):
            publish_package(self.output, self.writer)
        self.assertEqual(stale.read_text(), "old source")
        self.assertFalse((self.output / MANIFEST_NAME).exists())

    def test_verifier_rejects_extra_step_and_missing_completion_manifest(self):
        publish_package(self.output, self.writer)
        (self.output / "unlisted.stp").write_text("old")
        with self.assertRaisesRegex(ExportValidationError, "Unlisted STEP"):
            verify_package(self.output)
        (self.output / MANIFEST_NAME).unlink()
        with self.assertRaises(OSError):
            verify_package(self.output)

    def test_unrelated_files_survive_publication(self):
        self.output.mkdir()
        (self.output / "review-notes.txt").write_text("preserve")
        publish_package(self.output, self.writer)
        self.assertEqual((self.output / "review-notes.txt").read_text(), "preserve")
        verify_package(self.output)

    def test_manifest_cannot_escape_package_or_claim_production_scope(self):
        publish_package(self.output, self.writer)
        valid_manifest = verify_package(self.output)
        path = self.output / MANIFEST_NAME

        escaped_manifest = json.loads(json.dumps(valid_manifest))
        escaped_manifest["files"]["../outside.step"] = escaped_manifest["files"].pop("part.step")
        path.write_text(json.dumps(escaped_manifest))
        with self.assertRaisesRegex(ExportValidationError, "inside package"):
            verify_package(self.output)

        production_manifest = json.loads(json.dumps(valid_manifest))
        production_manifest["scope"] = "PRODUCTION"
        path.write_text(json.dumps(production_manifest))
        with self.assertRaisesRegex(ExportValidationError, "DEVELOPMENT_ONLY"):
            verify_package(self.output)

    def test_symlink_cannot_redirect_artifact_replacement(self):
        self.output.mkdir()
        target = Path(self.tmp.name) / "original.step"
        target.write_text("preserve")
        (self.output / "part.step").symlink_to(target)
        with self.assertRaises(ExportValidationError):
            publish_package(self.output, self.writer)
        self.assertEqual(target.read_text(), "preserve")

    def test_failed_unknown_empty_or_duplicate_checks_cannot_export(self):
        for checks in ([], [{"id": "A", "status": "FAIL"}],
                       [{"id": "A", "status": "SKIP"}],
                       [{"id": "A", "status": "PASS"}] * 2):
            with self.subTest(checks=checks), self.assertRaises(ExportValidationError):
                validate_checks(checks)

    def test_all_pass_does_not_approve_unfinished_development_model(self):
        checks = [{"id": "A", "status": "PASS", "message": "digital only"}]
        report = development_readiness(checks, [{"name": "shell", "status": "CAD_BASELINE"}])
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIs(report["production_ready"], False)
        self.assertTrue(report["required_release_evidence"])


if __name__ == "__main__":
    unittest.main()
