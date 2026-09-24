"""Regression tests for the CutePy compiler.

The compiler writes its output to fixed file names ("intermediate code.int"
and "final code.asm") in the current directory, so every test runs it inside
a temporary directory.

- Examples: each examples/<name>.cpy must compile, and the generated output
  must match examples/<name>.int and examples/<name>.asm.
- Errors: each tests/errors/<name>.cpy must be rejected with a non-zero exit
  code and the error message listed in EXPECTED_ERRORS.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPILER = ROOT / "compilers.py"
EXAMPLES = ROOT / "examples"
ERRORS = Path(__file__).resolve().parent / "errors"

EXPECTED_ERRORS = {
    "bad_main_name": "Main function is expected to have a main_ like name in line 1",
    "identifier_too_long": "String abcdefghijklmnopqrstuvwxyz12345 too long in line 3",
    "illegal_character": "Illegal character @ in line: 4",
    # The missing "#}" is noticed only when the parser reaches the next "if".
    "missing_block_end": "( expected after if in line 6",
    "missing_relational_operator": "Relational operator expected after expression in line 5",
    "missing_semicolon": "; expected after expression in line 4",
    "nested_main_function": "Main function cannot be declared in another main function 4",
    "number_out_of_range": "Number 4294967296 out of range in line 4",
    "undeclared_variable": "y is not declared",
}


def run_compiler(workdir, *args):
    return subprocess.run(
        [sys.executable, str(COMPILER), *args],
        cwd=workdir,
        capture_output=True,
        text=True,
    )


def compile_file(source, workdir):
    shutil.copy(source, workdir)
    return run_compiler(workdir, source.name)


def read_text(path):
    # Text mode normalizes line endings, so the checks pass on Windows and Linux.
    return Path(path).read_text()


class ExampleProgramsTest(unittest.TestCase):
    def test_examples_match_expected_output(self):
        sources = sorted(EXAMPLES.glob("*.cpy"))
        self.assertTrue(sources, "no example programs found")
        for source in sources:
            with self.subTest(example=source.name), tempfile.TemporaryDirectory() as tmp:
                result = compile_file(source, tmp)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    read_text(Path(tmp) / "intermediate code.int"),
                    read_text(source.with_suffix(".int")),
                )
                self.assertEqual(
                    read_text(Path(tmp) / "final code.asm"),
                    read_text(source.with_suffix(".asm")),
                )


class ErrorCasesTest(unittest.TestCase):
    def test_every_error_case_has_an_expected_message(self):
        found = {path.stem for path in ERRORS.glob("*.cpy")}
        self.assertEqual(found, set(EXPECTED_ERRORS))

    def test_invalid_programs_are_rejected(self):
        for name, message in EXPECTED_ERRORS.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                result = compile_file(ERRORS / f"{name}.cpy", tmp)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


class CommandLineTest(unittest.TestCase):
    def test_no_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_compiler(tmp)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No file for compilation given.", result.stderr)

    def test_wrong_file_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_compiler(tmp, "program.txt")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Not supported file type.", result.stderr)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_compiler(tmp, "missing.cpy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("File missing.cpy not found.", result.stderr)


if __name__ == "__main__":
    unittest.main()
