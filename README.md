# Graphic Studio Pro 10.0

Új kezdőimageernyő: három editor gyorsindítója, recent projects, az aktív project utolsó öt backup savee és direct restorei lehetőség.

A korábbi 8.0 funkciói (projectfiles, colorátadás, ImageBatch, direct BrandStudio save, backup backups) megmaradtak.

## Arch Linux telepítés

A kicsomagolt mappában: `chmod +x telepites.sh && ./telepites.sh`

Launch: `~/.local/bin/grafikai-studio-pro` vagy Fuzzel.

Az adatok a `~/.local/share/grafikai-studio-pro` mappában találhatók. Telepítés előtt érdemes menteni ezt a mappát.

A böngészőben futó közös munkaterület helyi 127.0.0.1 kiszolgálót használ. A teljes niri grafikus működést külön ellenőrizni kell.


## 10.0 újdonságok
- Projectkeresés a kezdőlapon (Ctrl+K).
- Billentyűparancsok: Ctrl+1/2/3 lapváltás; Ctrl+S BrandStudio pages savee projectbe.
- Böngészős hibák helyi munkamenetnaplója, TXT export és delete.
- A errornapló csak a közös felület JavaScript-hibáit rögzíti, nem a külön ImageBatch ablak teljes errorkimenetét.
- A Ctrl+S a BrandStudio editor saját billentyűfókuszában eltérően viselkedhet.

**Tesztelés:** szintaxis, csomag és helyi HTTP alapteszt; niri alatti GUI-teszt szükséges.
