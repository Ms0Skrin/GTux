#!/usr/bin/env bash
# GTux в контейнерах других дистрибутивов (podman, без root): тесты + запуск проверки + план исправления.
# Видеокарты и Steam в контейнере нет — проверяется распознавание системы, пакетный менеджер, имена пакетов.
# Запуск из корня проекта: scripts/distro_test.sh [debian|ubuntu|fedora ...]
set -euo pipefail
cd "$(dirname "$0")/.."
declare -A IMAGE=(
  [debian]=docker.io/library/debian:trixie
  [ubuntu]=docker.io/library/ubuntu:26.04
  [fedora]=registry.fedoraproject.org/fedora:latest
)
declare -A SETUP=(
  [debian]="export DEBIAN_FRONTEND=noninteractive && apt-get update -qq && apt-get install -y -qq python3 python3-rich >/dev/null"
  [ubuntu]="export DEBIAN_FRONTEND=noninteractive && apt-get update -qq && apt-get install -y -qq python3 python3-rich >/dev/null"
  [fedora]="dnf install -y -q python3 python3-rich >/dev/null"
)
for name in "${@:-debian ubuntu fedora}"; do
  for distro in $name; do
    echo "=== $distro (${IMAGE[$distro]})"
    podman run --rm -v "$PWD:/src:ro,Z" -w /src -e HOME=/tmp -e LANG=C.UTF-8 "${IMAGE[$distro]}" sh -c "
      ${SETUP[$distro]} &&
      python3 -m unittest discover -s tests -t . 2>&1 | tail -1 &&
      python3 main.py --json --no-history --lang ru > /tmp/gtux.json; python3 scripts/distro_summary.py < /tmp/gtux.json"
  done
done
