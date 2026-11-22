#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

arch=(python3 doc/tools/arch/__main__.py)

run_check() {
    local label="$1" output status
    shift
    if output=$("$@" 2>&1); then
        return 0
    else
        status=$?
        printf 'ERROR %s (exit %s)\n%s\n' "$label" "$status" "$output" >&2
        return "$status"
    fi
}

check_read_only() {
    run_check "index freshness" "${arch[@]}" index check
    run_check "architecture and index" "${arch[@]}" validate --brief
    run_check "declared paths" "${arch[@]}" docs paths --check
}

copy_project() {
    local destination="$1"
    tar \
        --exclude='./.git' \
        --exclude='*/__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='./build' \
        --exclude='./dist' \
        --exclude='*.egg-info' \
        -cf - . | tar -C "$destination" -xf -
}

build_index_in() {
    local copy="$1" seed="$2" tmpdir="$3" output
    if ! output=$(cd "$copy" && TMPDIR="$tmpdir" PYTHONHASHSEED="$seed" \
        python3 doc/tools/arch/__main__.py index build 2>&1); then
        printf 'ERROR reproducible index: rebuild failed (PYTHONHASHSEED=%s)\n%s\n' "$seed" "$output" >&2
        return 1
    fi
}

check_index_reproducible() {
    local first second scratch output
    first=$(mktemp -d)
    second=$(mktemp -d)
    scratch=$(mktemp -d)
    mkdir -p "$scratch/a" "$scratch/b"
    if ! output=$(copy_project "$first" 2>&1) || ! output=$(copy_project "$second" 2>&1); then
        printf 'ERROR reproducible index: cannot copy project\n%s\n' "$output" >&2
        rm -rf "$first" "$second" "$scratch"
        return 1
    fi
    if ! build_index_in "$first" 0 "$scratch/a" || ! build_index_in "$second" 12345 "$scratch/b"; then
        rm -rf "$first" "$second" "$scratch"
        return 1
    fi
    if ! cmp -s doc/architecture/index.json "$first/doc/architecture/index.json"; then
        printf 'ERROR reproducible index: rebuild with PYTHONHASHSEED=0 differs from doc/architecture/index.json\n' >&2
        rm -rf "$first" "$second" "$scratch"
        return 1
    fi
    if ! cmp -s doc/architecture/index.json "$second/doc/architecture/index.json"; then
        printf 'ERROR reproducible index: rebuild with PYTHONHASHSEED=12345 differs from doc/architecture/index.json\n' >&2
        rm -rf "$first" "$second" "$scratch"
        return 1
    fi
    if ! cmp -s "$first/doc/architecture/index.json" "$second/doc/architecture/index.json"; then
        printf 'ERROR reproducible index: rebuilds with different hash seeds differ from each other\n' >&2
        rm -rf "$first" "$second" "$scratch"
        return 1
    fi
    rm -rf "$first" "$second" "$scratch"
}

run_gate() {
    check_read_only
    run_check "reproducible index" check_index_reproducible
    run_check "unit tests" python3 -m unittest discover -s doc/tools/tests -q
    run_check "acceptance tests" python3 -m unittest discover -s doc/tests -p 'test_*.py' -q
    run_check "UI-0001 fixture" "${arch[@]}" task validate UI-0001
}

case "${1:-}" in
    --brief)
        check_read_only
        run_check "unit tests" python3 -m unittest discover -s doc/tools/tests -q
        run_check "acceptance tests" python3 -m unittest discover -s doc/tests -p 'test_*.py' -q
        run_check "UI-0001 fixture" "${arch[@]}" task validate UI-0001
        printf 'OK: architecture, index, paths, unit tests, acceptance tests, UI-0001\n'
        exit 0
        ;;
    --index-only)
        check_read_only
        run_check "reproducible index" check_index_reproducible
        printf 'OK: index freshness and reproducibility\n'
        exit 0
        ;;
    --gate)
        run_gate
        printf 'OK: index freshness, reproducibility, paths, unit tests, acceptance tests, UI-0001\n'
        exit 0
        ;;
    --in-copy)
        shift
        copy=$(mktemp -d)
        status=0
        if copy_project "$copy"; then
            (cd "$copy" && bash doc/tests/run.sh "${@:---gate}") || status=$?
        else
            printf 'ERROR in-copy: cannot copy project\n' >&2
            status=1
        fi
        rm -rf "$copy"
        exit "$status"
        ;;
    "") ;;
    *)
        printf 'Usage: bash doc/tests/run.sh [--brief|--index-only|--gate|--in-copy [mode]]\n' >&2
        exit 2
        ;;
esac

python3 -m unittest discover -s doc/tools/tests -v
python3 -m unittest discover -s doc/tests -p 'test_*.py' -v
check_read_only
"${arch[@]}" task validate UI-0001 >/dev/null
printf '\nAll environment acceptance tests passed.\n'
