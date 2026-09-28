#!/usr/bin/env bash
# Create a separate Python environment for the optional SPOCK indicator (exostab check --spock).
#
#   scripts/make_spock_env.sh [target-folder]        # default: ~/.exostab-spock
#   export EXOSTAB_SPOCK_PYTHON=<target-folder>/bin/python
#
# SPOCK 2.1.1 needs REBOUND < 5, so it cannot share exostab's environment (DECISIONS.md, D23). Versions are
# pinned to the combination tested on 2026-09-28 (macOS arm64, Python 3.12). celmech and reboundx are built from
# source, so a C compiler is needed (Xcode command-line tools on macOS, gcc on Linux). On Linux, torch is taken
# from the CPU-only index to avoid about 3 GB of CUDA libraries. On macOS no libomp install is needed: the
# exostab worker uses the copy bundled with scikit-learn. Requires uv (https://docs.astral.sh/uv/).
set -euo pipefail
target="${1:-$HOME/.exostab-spock}"
uv venv --python 3.12 "$target"
extra=()
if [[ "$(uname -s)" == "Linux" ]]; then
  extra=(--extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match)
fi
uv pip install --python "$target/bin/python" ${extra[@]+"${extra[@]}"} \
  "spock==2.1.1" "rebound==4.6.0" "reboundx==4.6.2" "celmech==1.5.8" "xgboost==2.1.4" \
  "scikit-learn==1.5.2" "safetensors==0.4.5" pandas ipython
echo
echo "SPOCK environment ready. Use it with:"
echo "  export EXOSTAB_SPOCK_PYTHON=$target/bin/python"
echo "  exostab check \"TRAPPIST-1\" --spock"
