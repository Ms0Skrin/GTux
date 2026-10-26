#!/usr/bin/env bash
# Снимки окна для README на невидимом дисплее Broadway (на экран ничего не выводится).
# Запуск из корня проекта: scripts/gui_screenshots.sh
set -euo pipefail
OUT=docs/screenshots
mkdir -p "$OUT"
gtk4-broadwayd :9 >/dev/null 2>&1 &
BROADWAY=$!
trap 'kill $BROADWAY' EXIT
sleep 1

shot() {  # shot <файл> [переменные окружения...] [-- аргументы main.py]
    local file=$1; shift
    env GDK_BACKEND=broadway BROADWAY_DISPLAY=:9 DOCTOR_GUI_SNAPSHOT="$OUT/$file" "$@" \
        timeout 60 python3 main.py --gui ${LANG_ARG:-}
}

LANG_ARG="--lang ru" shot overview-light.png DOCTOR_GUI_SCHEME=light DOCTOR_GUI_DEMO=1
LANG_ARG="--lang ru" shot overview-dark.png  DOCTOR_GUI_SCHEME=dark  DOCTOR_GUI_DEMO=1
LANG_ARG="--lang ru" shot games-dark.png     DOCTOR_GUI_SCHEME=dark  DOCTOR_GUI_PAGE=games
LANG_ARG="--lang ru" shot launch-options.png DOCTOR_GUI_SCHEME=dark DOCTOR_GUI_PAGE=launch
LANG_ARG="--lang en" shot vulkan-en.png      DOCTOR_GUI_SCHEME=light DOCTOR_GUI_DEMO=1 DOCTOR_GUI_PAGE=vulkan
# fix-dialog.png снимается только на настоящем экране: на Broadway без подключённого браузера
# окно не пересчитывает раскладку, и всплывающий диалог в снимок не попадает:
#   DOCTOR_GUI_DEMO=1 DOCTOR_GUI_OPEN_FIX=1 DOCTOR_GUI_SCHEME=light \
#   DOCTOR_GUI_SNAPSHOT=docs/screenshots/fix-dialog.png python3 main.py --gui --lang ru
ls -la "$OUT"
