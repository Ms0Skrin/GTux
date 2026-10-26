#!/usr/bin/env bash
# Готовит пакет AUR для текущей версии: контрольная сумма архива с GitHub, .SRCINFO, пробная сборка.
# Нужен тег v<версия> на GitHub (git tag v0.7.0 && git push origin v0.7.0).
# Результат: packaging/aur/PKGBUILD и packaging/aur/.SRCINFO — их и заливают в репозиторий AUR.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python3 -c 'import gtux; print(gtux.__version__)')
AUR=packaging/aur
sed -i "s/^pkgver=.*/pkgver=$VERSION/; s/^pkgrel=.*/pkgrel=1/" "$AUR/PKGBUILD"

URL="https://github.com/Ms0Skrin/GTux/archive/refs/tags/v$VERSION.tar.gz"
SUM=$(curl -fsSL "$URL" | sha256sum | cut -d' ' -f1) || { echo "Нет архива $URL — тег v$VERSION залит на GitHub?" >&2; exit 1; }
sed -i "s/^sha256sums=.*/sha256sums=('$SUM')/" "$AUR/PKGBUILD"

BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT
cp "$AUR/PKGBUILD" "$BUILD/"
(cd "$BUILD" && makepkg --printsrcinfo > .SRCINFO && makepkg --force --clean --cleanbuild >/dev/null)
cp "$BUILD/.SRCINFO" "$AUR/.SRCINFO"
ls -la "$BUILD"/*.pkg.tar.zst
echo "Готово: $AUR/PKGBUILD и $AUR/.SRCINFO для версии $VERSION (sha256 $SUM)"
