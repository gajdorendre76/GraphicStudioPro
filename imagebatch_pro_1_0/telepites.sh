#!/usr/bin/env bash
set -euo pipefail
sudo pacman -S --needed python python-pillow tk ttf-dejavu
mkdir -p "$HOME/.local/share/imagebatch" "$HOME/.local/bin" "$HOME/.local/share/applications"
cp "$(dirname "$(realpath "$0")")/imagebatch.py" "$HOME/.local/share/imagebatch/imagebatch.py"
cat > "$HOME/.local/bin/imagebatch" <<'EOF'
#!/usr/bin/env bash
exec /usr/bin/python "$HOME/.local/share/imagebatch/imagebatch.py" "$@"
EOF
chmod +x "$HOME/.local/bin/imagebatch"
cat > "$HOME/.local/share/applications/imagebatch.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ImageBatch Pro
Comment=Hungarian nyelvű tömeges imagefeldolgozó
Exec=$HOME/.local/bin/imagebatch
Icon=image-x-generic
Terminal=false
Categories=Graphics;Photography;
EOF
echo 'Telepítve. Launch: ~/.local/bin/imagebatch vagy Fuzzel → ImageBatch'
