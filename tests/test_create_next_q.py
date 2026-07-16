import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / ".vscode" / "create_next_q.py"

spec = importlib.util.spec_from_file_location("create_next_q", MODULE_PATH)
create_next_q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_next_q)


class CreateNextQTests(unittest.TestCase):
    def test_resolve_path_uses_repo_root_for_relative_inputs(self):
        relative_path = "questions_output/Class-XII/Haloalkanes/q_00001.md"
        resolved = create_next_q.resolve_active_path(relative_path, REPO_ROOT)

        self.assertEqual(
            resolved,
            REPO_ROOT / "questions_output" / "Class-XII" / "Haloalkanes" / "q_00001.md",
        )

    def test_resolve_path_converts_windows_unc_paths(self):
        windows_path = r"\\wsl.localhost\Ubuntu\home\ranga\qnbk\questions_output\Class-XII\Haloalkanes\q_00012.md"
        resolved = create_next_q.resolve_active_path(windows_path, REPO_ROOT)

        self.assertEqual(
            resolved,
            REPO_ROOT / "questions_output" / "Class-XII" / "Haloalkanes" / "q_00012.md",
        )

    def test_resolve_path_converts_single_slash_unnormalized_unc_paths(self):
        windows_path = r"/wsl.localhost/Ubuntu/home/ranga/qnbk/questions_output/Class-XII/Haloalkanes/q_00012.md"
        resolved = create_next_q.resolve_active_path(windows_path, REPO_ROOT)

        self.assertEqual(
            resolved,
            REPO_ROOT / "questions_output" / "Class-XII" / "Haloalkanes" / "q_00012.md",
        )

    def test_resolve_directory_target_from_workspace_relative_path(self):
        directory_path = "questions_output/Class-XII/Haloalkanes"
        resolved = create_next_q.resolve_target_directory(directory_path, REPO_ROOT)

        self.assertEqual(resolved, REPO_ROOT / "questions_output" / "Class-XII" / "Haloalkanes")
