# Cave Plan Georeferencer

Narzędzie webowe do georeferencji planów jaskiń. Pozwala przekształcić skan planu jaskini w plik GeoTIFF, który można otworzyć w programach GIS (QGIS, Google Earth Pro, mapy.cz).

**Demo:** https://dlubom.github.io/Polish-Cave-Data-Scraper/

## Idea

Plany jaskiń w bazach danych (np. CBDG) są zwykłymi obrazkami - nie zawierają informacji o położeniu geograficznym. Georeferencer rozwiązuje ten problem:

1. **Wskazujesz punkty kalibracyjne** na planie:
   - Otwór wejściowy (znamy jego współrzędne GPS)
   - Początek i koniec podziałki skali (znamy długość w metrach)
   - Opcjonalnie: strzałkę północy (dla planów z niestandardową orientacją)

2. **Narzędzie oblicza transformację** uwzględniając:
   - Skalę (piksele → metry)
   - Obrót (orientacja północy + konwergencja południkowa)
   - Przesunięcie (współrzędne wejścia)

3. **Generujesz pliki** do utworzenia GeoTIFF:
   - World File (`.jgw`, `.pgw`, `.tfw` - zależnie od formatu obrazu) z parametrami transformacji
   - Komendę GDAL do konwersji

## Ograniczenia

### Układ współrzędnych

Narzędzie domyślnie używa układu **PL-1992 (EPSG:2180)** z południkiem osiowym **19°E**. Oznacza to, że:

- Działa poprawnie dla większości Polski (Tatry, Sudety, Jura, Góry Świętokrzyskie)
- Dla jaskiń blisko granicy zachodniej (np. Karkonosze) błędy mogą być większe
- Można zmienić definicję PROJ4 w polu "Definicja projekcji" jeśli potrzeba innego układu

### Dokładność

Dokładność georeferencji zależy od:
- Jakości współrzędnych GPS wejścia (często ±10-50m w bazach danych)
- Precyzji kliknięcia punktów kalibracyjnych
- Dokładności podziałki skali na planie
- Deformacji skanu (rozciągnięcie, obrót)

Dla typowych planów można oczekiwać dokładności rzędu kilku-kilkunastu metrów.

## Co to jest World File?

World File to plik tekstowy zawierający 6 liczb opisujących transformację afiniczną obrazu:

```
0.1234567890    <- A: rozmiar piksela w osi X (metry) × cos(obrót)
0.0012345678    <- D: obrót w osi Y
0.0012345678    <- B: obrót w osi X
-0.1234567890   <- E: rozmiar piksela w osi Y (ujemny, bo Y rośnie w dół)
567890.123456   <- C: współrzędna X lewego górnego rogu
234567.890123   <- F: współrzędna Y lewego górnego rogu
```

**Ważne:** Rozszerzenie World File zależy od formatu obrazu:
- `.jgw` → dla `.jpg` / `.jpeg`
- `.pgw` → dla `.png`
- `.tfw` → dla `.tif` / `.tiff`
- `.gfw` → dla `.gif`
- `.bpw` → dla `.bmp`

GDAL automatycznie wykrywa World File jeśli ma taką samą nazwę jak obraz i prawidłowe rozszerzenie (np. `plan.jpg` + `plan.jgw`).

## Instalacja GDAL

### macOS (Homebrew)

```bash
brew install gdal
```

### Ubuntu/Debian

```bash
sudo apt-get install gdal-bin
```

### Windows

1. Pobierz OSGeo4W: https://trac.osgeo.org/osgeo4w/
2. Zainstaluj z opcją "GDAL"
3. Uruchom "OSGeo4W Shell" i użyj komend GDAL

### Conda

```bash
conda install -c conda-forge gdal
```

### Weryfikacja instalacji

```bash
gdal_translate --version
# GDAL 3.x.x, released ...
```

## Workflow

### 1. Wybierz jaskinię i załaduj plan

Plany jaskiń są hostowane w tym repozytorium:
- `caves/` - oryginalne skany z CBDG
- `caves_upscaled/` - powiększone i odszumione (2x, waifu2x)

Możesz też wgrać własny skan z dysku (przycisk "Wgraj plan z dysku").

**Obsługiwane formaty:**
- JPG, PNG - wszystkie przeglądarki
- TIFF - tylko Safari (w innych przeglądarkach najpierw przekonwertuj: `convert plan.tif plan.jpg`)

Aplikacja obsługuje duże pliki (testowane do 50 MB / 160 megapikseli). Bardzo duże obrazy są automatycznie skalowane na podglądzie, ale obliczenia World File używają oryginalnych wymiarów.

### 2. Kliknij punkty kalibracyjne

1. **Otwór wejściowy** - punkt o znanych współrzędnych GPS
2. **Początek skali** - lewy/dolny koniec podziałki
3. **Koniec skali** - prawy/górny koniec podziałki
4. (Opcjonalnie) **Strzałka północy** - baza i grot strzałki

Współrzędne wejścia są automatycznie pobierane z bazy danych. Możesz je ręcznie poprawić jeśli masz dokładniejsze dane.

### 3. Pobierz pliki do jednego folderu

Po kalibracji kliknij:
- **Obraz** - pobiera oryginalny obraz z GitHub (np. `J.Olk.12.03.jpg`)
- **World File** - pobiera plik World File (np. `J.Olk.12.03.jgw` dla JPG)

**Oba pliki muszą być w tym samym folderze i mieć tę samą nazwę** (różne rozszerzenia). GDAL automatycznie je połączy.

Dla plików wgranych z dysku przycisk "Obraz" jest nieaktywny - masz już plik na dysku.

### 4. Uruchom komendę GDAL

Kliknij "Pokaż komendę GDAL" i skopiuj wygenerowaną komendę:

```bash
gdal_translate -of GTiff -a_srs EPSG:2180 -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES "J.Olk.12.03.jpg" "J.Olk.12.03_georef.tif"
```

Opcje:
- `-a_srs EPSG:2180` - przypisuje układ współrzędnych PL-1992
- `-co COMPRESS=DEFLATE` - kompresja bezstratna (mały rozmiar pliku)
- `-co PREDICTOR=2` - lepsza kompresja dla obrazów
- `-co TILED=YES` - kafelkowanie (szybsze wyświetlanie w GIS)

### 5. Użyj w programie GIS

Wynikowy plik `.tif` można otworzyć w:
- **QGIS** - File → Open → wybierz plik
- **Google Earth Pro** - File → Import
- **mapy.cz** - Mapy → Vlastní mapy → dodaj plik

## Struktura plików

```
Polish-Cave-Data-Scraper/
├── index.html              # Aplikacja Georeferencer
├── caves/                  # Oryginalne skany (z CBDG)
│   ├── 000390/
│   │   ├── image_19_zoom_10.jpg
│   │   └── ...
│   └── ...
├── caves_upscaled/         # Powiększone skany (2x, waifu2x)
│   └── ...
└── caves_transformed.jsonl # Dane jaskiń (współrzędne, metadane)
```

## Przykład

Dla Jaskini Mylnej (J.Tat.K-01.03):

1. Wyszukaj "Mylna" w liście jaskiń
2. Wybierz plan, załaduj
3. Kliknij otwór wejściowy (przy napisie "wejście")
4. Kliknij początek i koniec podziałki "50 m"
5. Pobierz `J.Tat.K-01.03.jpg` i `J.Tat.K-01.03.jgw`
6. Uruchom:
   ```bash
   cd ~/Downloads
   gdal_translate -of GTiff -a_srs EPSG:2180 -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES "J.Tat.K-01.03.jpg" "J.Tat.K-01.03_georef.tif"
   ```
7. Otwórz `J.Tat.K-01.03_georef.tif` w QGIS

## Rozwiązywanie problemów

### "Nie można pobrać obrazu"

Niektóre przeglądarki blokują pobieranie z innych domen. Rozwiązania:
- Użyj Chrome/Firefox
- Pobierz obraz ręcznie z GitHub: https://github.com/dlubom/Polish-Cave-Data-Scraper/tree/main/caves_upscaled

### GDAL nie widzi pliku World File / obraz nie ma georeferencji

Upewnij się, że:
- Oba pliki są w tym samym folderze
- Mają identyczne nazwy (wielkość liter ma znaczenie)
- **Rozszerzenie World File odpowiada formatowi obrazu:**
  - `.jpg` wymaga `.jgw` (nie `.tfw`!)
  - `.png` wymaga `.pgw`
  - `.tif` wymaga `.tfw`

Sprawdź czy GDAL widzi georeferencję:
```bash
gdalinfo twoj_obraz.jpg
```
Jeśli widzisz `GeoTransform =` z liczbami - działa. Jeśli widzisz `Corner Coordinates: Upper Left (0.0, 0.0)` - World File nie został wykryty.

### Plan jest obrócony/przesunięty w GIS

Sprawdź:
- Czy kliknięte punkty są w prawidłowych miejscach
- Czy wartość skali jest poprawna (metry, nie centymetry)
- Czy układ współrzędnych w GDAL odpowiada definicji PROJ4

## Licencja

Plany jaskiń pochodzą z Centralnej Bazy Danych Geologicznych (CBDG) i są udostępniane na zasadach określonych przez Państwowy Instytut Geologiczny.
