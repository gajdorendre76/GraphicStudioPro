#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sudo pacman -S --needed python python-pillow tk ttf-dejavu
DEST="$HOME/.local/share/grafikai-studio-pro"
mkdir -p "$DEST" "$HOME/.local/bin" "$HOME/.local/share/applications"
cp -a "$SOURCE/." "$DEST/"
cat > "$HOME/.local/bin/grafikai-studio-pro" <<'EOF'
#!/usr/bin/env bash
exec /usr/bin/python "$HOME/.local/share/grafikai-studio-pro/studio.py" "$@"
EOF
chmod +x "$HOME/.local/bin/grafikai-studio-pro"
cat > "$HOME/.local/share/applications/grafikai-studio-pro.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Graphic Studio Pro
Comment=Közös grafikai munkaterület és projectpaletták
Exec=$HOME/.local/bin/grafikai-studio-pro
Icon=applications-graphics
Terminal=false
Categories=Graphics;
EOF
echo "Telepítve. Launch: ~/.local/bin/grafikai-studio-pro"
