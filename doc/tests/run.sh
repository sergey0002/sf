#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m unittest discover -s doc/tools/tests -v
python3 -m unittest discover -s doc/tests -p 'test_*.py' -v
python3 doc/tools/arch/__main__.py index build
python3 doc/tools/arch/__main__.py validate
python3 doc/tools/arch/__main__.py index check
python3 doc/tools/arch/__main__.py docs paths --check
python3 -m json.tool doc/tasks/UI-0001/task.json >/dev/null
printf '\nAll environment acceptance tests passed.\n'
