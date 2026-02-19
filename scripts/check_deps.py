"""
Dependency check — verifies all Python packages and system tools needed
for Stage 1. Prints a clear pass/fail for each.

Usage:
    python3 scripts/check_deps.py
    python3 scripts/check_deps.py -v    # also print versions
"""

import argparse
import importlib
import shutil
import subprocess
import sys


def check(label: str, ok: bool, detail: str = "", fix: str = "") -> bool:
    status = "OK  " if ok else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f"  ({detail})", end="")
    print()
    if not ok and fix:
        print(f"         fix: {fix}")
    return ok


def python_version(verbose: bool) -> bool:
    v = sys.version_info
    ok = v >= (3, 11)
    detail = f"{v.major}.{v.minor}.{v.micro}" if verbose else ""
    return check("Python >= 3.11", ok, detail, "upgrade Python")


def pkg(name: str, import_name: str, verbose: bool, fix_cmd: str) -> bool:
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", "?") if verbose else ""
        return check(f"pip: {name}", True, version)
    except ImportError:
        return check(f"pip: {name}", False, fix=f"pip install {fix_cmd}")


def cmd(label: str, binary: str, version_flag: str, verbose: bool, fix_cmd: str) -> bool:
    path = shutil.which(binary)
    if not path:
        return check(label, False, fix=fix_cmd)
    if verbose:
        try:
            out = subprocess.check_output(
                [binary, version_flag], stderr=subprocess.STDOUT, text=True
            ).strip().splitlines()[0]
        except Exception:
            out = path
    else:
        out = ""
    return check(label, True, out)


def db_reachable(verbose: bool) -> bool:
    try:
        sys.path.insert(0, ".")
        from src.db import get_conn
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0].split(",")[0] if verbose else ""
        conn.close()
        return check("Postgres reachable", True, ver)
    except Exception as exc:
        return check("Postgres reachable", False, str(exc) if verbose else "",
                     fix="start Postgres: colima start  (or: brew services start postgresql@16)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Stage 1 dependencies.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print versions and paths.")
    args = parser.parse_args()
    v = args.verbose

    results = []

    print("\n=== Python ===")
    results.append(python_version(v))

    print("\n=== Python packages ===")
    results.append(pkg("requests",        "requests",  v, "requests"))
    results.append(pkg("psycopg2",        "psycopg2",  v, "psycopg2-binary"))
    results.append(pkg("pytest",          "pytest",    v, "pytest"))

    print("\n=== System tools ===")
    results.append(cmd("docker CLI",    "docker",      "version", v,
                        "brew install colima docker && colima start"))
    results.append(cmd("docker compose","docker",      "compose version", v,
                        "brew install docker-compose"))
    results.append(cmd("psql (optional)","psql",       "--version", v,
                        "brew install libpq"))

    print("\n=== Database ===")
    results.append(db_reachable(v))

    passed = sum(results)
    total  = len(results)
    print(f"\n{'=' * 40}")
    print(f"  {passed}/{total} checks passed")
    if passed < total:
        print("  Run with -v for version details and fix hints.")
    print()
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
