#!/usr/bin/env python3

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vcpkg ci for a single triplet.")
    parser.add_argument("--vcpkg-root", required=True, type=Path)
    parser.add_argument("--triplet", required=True)
    parser.add_argument("--failure-dir", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def copy_toolchain_for_test_ports(vcpkg_root: Path) -> None:
    toolchain = vcpkg_root / "scripts" / "buildsystems" / "vcpkg.cmake"
    for destination in (
        vcpkg_root / "scripts" / "test_ports" / "cmake" / "vcpkg.cmake",
        vcpkg_root / "scripts" / "test_ports" / "cmake-user" / "vcpkg.cmake",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(toolchain, destination)


def vcpkg_executable(vcpkg_root: Path) -> Path:
    executable = "vcpkg.exe" if platform.system() == "Windows" else "vcpkg"
    path = vcpkg_root / executable
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}")
    return path


def triplet_argument(triplet: str) -> str:
    if triplet == "x64-windows-release":
        return f"--host-triplet={triplet}"
    return f"--triplet={triplet}"


def run_and_log(command: list[str], cwd: Path, log_path: Path, dry_run: bool) -> int:
    rendered = " ".join(command)
    print(rendered, flush=True)
    if dry_run:
        return 0

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"$ {rendered}\n")
        log_file.flush()

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)

        return process.wait()


def main() -> int:
    args = parse_args()
    vcpkg_root = args.vcpkg_root.resolve()
    failure_dir = args.failure_dir.resolve()
    work_dir = args.work_dir.resolve()
    log_path = failure_dir / "vcpkg-ci.log"

    failure_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    executable = vcpkg_executable(vcpkg_root)
    ci_baseline = vcpkg_root / "ci.baseline.txt"
    xunit_path = failure_dir / f"{args.triplet}-results.xml"
    hashes_path = failure_dir / "pr-hashes.json"

    copy_toolchain_for_test_ports(vcpkg_root)

    common_args = [
        f"--x-buildtrees-root={work_dir / 'buildtrees'}",
        f"--x-install-root={work_dir / 'installed'}",
        f"--x-packages-root={work_dir / 'packages'}",
        "--overlay-ports=scripts/test_ports",
    ]
    clean_command = [str(executable), "x-ci-clean", *common_args]
    ci_command = [
        str(executable),
        "ci",
        triplet_argument(args.triplet),
        f"--failure-logs={failure_dir}",
        f"--output-hashes={hashes_path}",
        f"--x-xunit={xunit_path}",
        f"--ci-baseline={ci_baseline}",
        *common_args,
    ]

    clean_exit_code = run_and_log(clean_command, vcpkg_root, log_path, args.dry_run)
    if clean_exit_code != 0:
        return clean_exit_code

    return run_and_log(ci_command, vcpkg_root, log_path, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
