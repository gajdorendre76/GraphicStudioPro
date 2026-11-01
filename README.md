# Graphic Studio Pro 10.0

Graphic Studio Pro is a collection of creative tools for Arch Linux, combining a shared project workspace with color palette design, brand design, and batch image processing.

## Included applications

- **Graphic Studio Pro:** central project dashboard and shared workspace.
- **BrandStudio 13.0:** branding and layout editor.
- **Color Palette Studio 8:** palette creation and color selection.
- **ImageBatch Pro 1.0:** batch image processing.

## Installation on Arch Linux

Download the source code and extract it. From the extracted directory run:

```bash
chmod +x telepites.sh
./telepites.sh
```

Launch the application from Fuzzel or with:

```bash
~/.local/bin/grafikai-studio-pro
```

**Back up existing projects before reinstalling.** Application data is stored under `~/.local/share/grafikai-studio-pro`.

## Version 10.0 highlights

- Home dashboard with editor shortcuts and recent projects.
- Project search with `Ctrl+K`.
- Editor navigation with `Ctrl+1`, `Ctrl+2`, and `Ctrl+3`.
- Project file management and ZIP export.
- BrandStudio project saving and recovery snapshots.
- Session-level JavaScript error log with text export.

## Notes and limitations

The shared browser workspace uses a local server bound to `127.0.0.1`. Full graphical operation under niri/Wayland has not yet been independently verified. Error logs capture errors from the shared JavaScript interface, not the complete output of the separate ImageBatch window. Keyboard shortcuts may behave differently when an embedded editor has focus.

The application is undergoing an English-language interface review. Some interface text may still contain Hungarian or mixed-language labels.

## Release status

Version 10.0 source is available. A packaged, verified release has not yet been published. No open-source license has been selected; please do not assume permission to redistribute or modify the code beyond applicable law.
