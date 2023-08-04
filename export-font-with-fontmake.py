# MenuTitle: Export with fontmake
# Copyright 2023 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__doc__ = """Export with fontmake

This script exports the current font using a self-contained copy of fontmake that
doesn't interfere with Glyphs.app's Python environment, nor requires a virtualenv.
It only requires that Python 3.11 is installed via the official Glyphs.app plugin:
https://glyphsapp.com/learn/extending-glyphs
"""

import io
import re
import subprocess
import shlex
import sys
from pathlib import Path


FONTMAKE_ARGS = [
    # this builds a TrueType-flavored variable font
    "-o",
    "variable",  # or e.g. "ttf" for static, see fontmake -h for other formats
    # Add any extra arguments here, e.g.:
    # "--no-check-compatibility",
    # "--interpolate",
    # "--verbose=DEBUG",
    # "--filter=DecomposeTransformedComponentsFilter",
    # "--filter=FlattenComponentsFilter",
    # "--ttf-curves=mixed",
]
FONTMAKE_VERSION = "3.7.0"
GLYHPS_PYTHON_EXE = Path.home() / (
    "Library/Application Support/Glyphs 3/Repositories/"
    "GlyphsPythonPlugin/Python.framework/Versions/Current/bin/python3"
)
FONTMAKE_SCRIPT = Path(__file__).parent / f"fontmake-{FONTMAKE_VERSION}.pyz"


def run_subprocess_in_macro_window(
    command, check=False, clear_log=True, show_window=True, capture_output=False
):
    if clear_log:
        Glyphs.clearLog()
    if show_window:
        Glyphs.showMacroWindow()

    print(f"$ {' '.join(shlex.quote(str(arg)) for arg in command)}")

    # Start the subprocess asynchronously and redirect output to a pipe
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirect stderr to stdout
        text=True,
        bufsize=1,  # Line-buffered
    )

    # Read the output line by line and write to Glyphs.app's Macro output window
    output = io.StringIO() if capture_output else None
    while process.poll() is None:
        for line in process.stdout:
            sys.stdout.write(line)
            if output is not None:
                output.write(line)

    returncode = process.wait()

    if check and returncode != 0:
        # Raise an exception if the process returned an error code
        raise subprocess.CalledProcessError(
            returncode, process.args, process.stdout, process.stderr
        )

    if capture_output:
        return subprocess.CompletedProcess(
            process.args, returncode, output.getvalue(), ""
        )

    return subprocess.CompletedProcess(process.args, returncode, None, None)


def reveal_file_in_finder(path):
    quoted_path = shlex.quote(str(path))
    subprocess.run(f"[ -e {quoted_path} ] && open -R {quoted_path}", shell=True)


def main():
    font = Glyphs.font
    if font is None:
        return Message("Open a font first.\n", title="Export with fontmake")

    python_exe = GLYHPS_PYTHON_EXE
    if not python_exe.exists():
        return Message(
            f"Python 3 plugin could not be found at {GLYHPS_PYTHON_EXE!r}\n"
            "Please make sure it is installed and try again.",
            title="Export with fontmake",
        )

    source_path = font.filepath
    if not source_path:
        return Message(
            f"The font has not been saved yet.\nPlease save it and then try again.",
            title="Export with fontmake",
        )
    if font.parent.isDocumentEdited():
        return Message(
            f"The font may contain unsaved changes.\n"
            "Please save it and then try again.",
            title="Export with fontmake",
        )
    source_path = Path(source_path)

    proposed_name = f"{source_path.stem}"
    if {"variable", "variable-cff2"}.intersection(FONTMAKE_ARGS):
        proposed_name += "-VF"

    save_dialog = GetFolder(message="Export with fontmake")
    if save_dialog is None:
        return
    output_dir = Path(save_dialog)

    fontmake_command = (
        [
            python_exe,
            FONTMAKE_SCRIPT,
        ]
        + FONTMAKE_ARGS
        + [
            "--output-dir",
            output_dir,
            source_path,
        ]
    )

    result = run_subprocess_in_macro_window(fontmake_command, capture_output=True)
    if result.returncode == 0:
        print("Done!")
    else:
        Message(
            f"Subprocess failed (exit code: {result.returncode}).\n"
            "Check the Macro window for details.",
            title="Export with fontmake",
        )

    output_paths = re.findall(
        r"^INFO:fontmake.font_project:Saving (.*)$", result.stdout, flags=re.M
    )
    if output_paths:
        # there may be more than one outputs, only reveal the last one
        reveal_file_in_finder(output_paths[-1])


main()
