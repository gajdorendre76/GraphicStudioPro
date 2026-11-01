# ImageBatch Pro 1.0

Hungarian nyelvű, offline kötegelt imagefeldolgozó Arch Linuxra (niri/Wayland alatt is használható).

## Telepítés

```bash
cd imagebatch_pro_1_0
chmod +x telepites.sh
./telepites.sh
```

Launch: `~/.local/bin/imagebatch`, vagy Fuzzel menü → ImageBatch Pro.

## Funkciók

- Tömeges JPEG/PNG/WebP konvertálás és méretezés; aránytartó, kitöltés, torzítás
- Forgatás, fényerő, kontraszt, preview
- Textes és logos vízjel 9 pozícióban, fedettséggel
- JPG/PNG DPI metaadat; JPEG/WebP minőség és optimalizálás
- EXIF/ICC megőrzési opciók (formátumfüggő)
- Processingi profilok JSON-ba; előtag, utótag, sorszámozás
- Megszakítás images között; TXT feldolgozási napló a kimeneti mappában
- Az eredeti files nem változnak

## Korlátok

A DPI csak felbontás-metaadat, nem változtatja a imagepontszámot. A WEBP DPI-értéket a Pillow savee nem garantálja. A meglévő ICC-profil megőrzése nem egyenlő colorprofil-konverzióval. A textes vízjel elhelyezése szélsőségesen hosszú textnél kilóghat. A megszakítás az aktuális image befejezése után lép életbe.
