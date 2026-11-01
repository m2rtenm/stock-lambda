#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
package_dir="${script_dir}/package"

rm -rf "$package_dir"
mkdir -p "$package_dir"

python3 -m pip install \
  --disable-pip-version-check \
  --require-hashes \
  --only-binary=:all: \
  --platform manylinux_2_28_x86_64 \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --implementation cp \
  --abi cp312 \
  --target "$package_dir" \
  -r "${script_dir}/lambda-requirements.txt"

cp "${script_dir}/StockAnalyzer.py" "$package_dir/"
