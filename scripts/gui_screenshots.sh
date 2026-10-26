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
    env GDK_BACKEND=broadway BROADWAY_DISPLAY=:9 GTUX_GUI_SNAPSHOT="$OUT/$file" "$@" \
        timeout 60 python3 main.py --gui ${LANG_ARG:-}
}

LANG_ARG="--lang ru" shot overview-light.png GTUX_GUI_SCHEME=light GTUX_GUI_DEMO=1
LANG_ARG="--lang ru" shot overview-dark.png  GTUX_GUI_SCHEME=dark  GTUX_GUI_DEMO=1
LANG_ARG="--lang ru" shot games-dark.png     GTUX_GUI_SCHEME=dark  GTUX_GUI_PAGE=games
LANG_ARG="--lang ru" shot library.png        GTUX_GUI_SCHEME=light GTUX_GUI_PAGE=library
LANG_ARG="--lang ru" shot launch-options.png GTUX_GUI_SCHEME=dark GTUX_GUI_PAGE=launch GTUX_GUI_GAME=1771300
LANG_ARG="--lang en" shot vulkan-en.png      GTUX_GUI_SCHEME=light GTUX_GUI_DEMO=1 GTUX_GUI_PAGE=vulkan
# fix-dialog.png снимается только на настоящем экране: на Broadway без подключённого браузера
# окно не пересчитывает раскладку, и всплывающий диалог в снимок не попадает:
#   GTUX_GUI_DEMO=1 GTUX_GUI_OPEN_FIX=1 GTUX_GUI_SCHEME=light \
#   GTUX_GUI_SNAPSHOT=docs/screenshots/fix-dialog.png python3 main.py --gui --lang ru
ls -la "$OUT"
