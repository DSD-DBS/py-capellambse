#!/bin/bash -e
# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
set -o pipefail
export CAPELLAMBSE_UUID_SEED=0

cd "${0%/*}/../docs/source/examples"

function celloutputs() {
  jq -r '.cells[] | select(.cell_type=="code") | .outputs[] | (.text, .data["text/plain"]) | .[]?' <"$1" |
    grep -v '^$' |
    sed -e 's/ at 0x[0-9a-fA-F]\+/ at 0x0/'
}

if [[ "$CI" != true ]]; then
  sync_args=(--inexact)
fi
uv sync --all-extras "${sync_args[@]}"

ok=true
for file in *.ipynb; do
  outfile="_${file%.ipynb}_tmp_verify.ipynb"
  old_outputs="$(celloutputs "$file")"
  if ! uv run --no-sync jupyter nbconvert --to notebook --execute "$file" --output "$outfile" --ExecutePreprocessor.timeout "${NOTEBOOK_TIMEOUT_SEC:-300}"; then
    ok=false
  else
    new_outputs="$(celloutputs "$file")"
    if ! diff -u3 <(echo "$old_outputs") <(echo "$new_outputs"); then
      ok=false
    fi
  fi
  rm -fv "$outfile"

  if [[ "$ok" != true && "$CI" != true ]]; then
    break
  fi
done

$ok
