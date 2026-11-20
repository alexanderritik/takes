#!/bin/sh
# Installs takes from the latest release on GitHub, for Linux and macOS.
#
#   curl -fsSL https://raw.githubusercontent.com/alexanderritik/takes/main/install.sh | sh
#
# TAKES_VERSION=v1.0.0 picks a release (default: the latest).
# TAKES_INSTALL_DIR=/usr/local/bin picks where it goes (default: ~/.local/bin).
set -eu

repo="alexanderritik/takes"
version="${TAKES_VERSION:-latest}"
dir="${TAKES_INSTALL_DIR:-$HOME/.local/bin}"

fail() { echo "install.sh: $*" >&2; exit 1; }

case "$(uname -s)" in
  Linux) os=linux ;;
  Darwin) os=darwin ;;
  *) fail "this script is for Linux and macOS; on Windows, download the .zip from https://github.com/$repo/releases" ;;
esac
case "$(uname -m)" in
  x86_64 | amd64) arch=amd64 ;;
  arm64 | aarch64) arch=arm64 ;;
  *) fail "no build for $(uname -m)" ;;
esac

if [ "$version" = latest ]; then
  base="https://github.com/$repo/releases/latest/download"
else
  base="https://github.com/$repo/releases/download/$version"
fi
file="takes_${os}_${arch}.tar.gz"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "Downloading $file ($version)"
curl -fsSL -o "$tmp/$file" "$base/$file" || fail "could not download $base/$file"
curl -fsSL -o "$tmp/checksums.txt" "$base/checksums.txt" || fail "could not download $base/checksums.txt"

want="$(grep " $file\$" "$tmp/checksums.txt" | cut -d' ' -f1)"
[ -n "$want" ] || fail "$file is not in checksums.txt"
if command -v sha256sum >/dev/null; then
  got="$(sha256sum "$tmp/$file" | cut -d' ' -f1)"
else
  got="$(shasum -a 256 "$tmp/$file" | cut -d' ' -f1)"
fi
[ "$got" = "$want" ] || fail "checksum mismatch for $file; not installed"

tar -xzf "$tmp/$file" -C "$tmp" takes
mkdir -p "$dir"
mv "$tmp/takes" "$dir/takes"
chmod +x "$dir/takes"
echo "Installed $("$dir/takes" version) to $dir/takes"

case ":$PATH:" in
  *":$dir:"*) ;;
  *) echo "Add $dir to your PATH to run takes from anywhere." ;;
esac
if ! command -v ffprobe >/dev/null; then
  echo "takes needs ffprobe, which comes with ffmpeg: apt install ffmpeg / brew install ffmpeg"
fi
