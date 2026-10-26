#!/usr/bin/env bash
# Собирает пакет pacman из закоммиченного состояния репозитория.
# Результат: dist/gtux-<версия>-1-any.pkg.tar.zst
# Установка (нужен sudo): sudo pacman -U dist/gtux-*.pkg.tar.zst
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python3 -c 'import gtux; print(gtux.__version__)')
PKGVER=$(grep -Po '^pkgver=\K.*' packaging/arch/PKGBUILD)
if [[ "$VERSION" != "$PKGVER" ]]; then
    echo "Версия в gtux/__init__.py ($VERSION) не совпадает с pkgver в PKGBUILD ($PKGVER)" >&2
    exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Внимание: есть незакоммиченные изменения — в пакет попадёт только то, что в git (HEAD)." >&2
fi

BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT
git archive --format=tar.gz --prefix="gtux-$VERSION/" -o "$BUILD/gtux-$VERSION.tar.gz" HEAD
cp packaging/arch/PKGBUILD "$BUILD/"
(cd "$BUILD" && makepkg --nodeps --force --clean >/dev/null)
mkdir -p dist
mv "$BUILD"/*.pkg.tar.zst dist/
ls -la dist/
