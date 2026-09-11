# yt-dlp GUI (CustomTkinter)

Windows için **yt-dlp** grafik arayüzü. Tüketiciler için kurulum yok: uygulama ilk çalıştırmada `yt-dlp.exe`, `ffmpeg` ve **Deno** (YouTube JS çalışma zamanı) araçlarını kendisi indirir. Yapmanız gereken tek şey URL yapıştırıp **İndir**e basmak.

## Windows .exe (önerilen)

Python kurmanıza gerek yok:

1. [Releases](https://github.com/zekig13/yt-dlp-gui/releases) sayfasından `yt-dlp-gui-windows-x64.zip` indirin
2. Zip'i açın
3. `yt-dlp-gui.exe` dosyasına çift tıklayın

İlk açılışta uygulama yt-dlp, ffmpeg ve Deno'yu `%LOCALAPPDATA%\yt-dlp-gui\bin\` altına indirir (YouTube için JS runtime). Çökme olursa log: `%LOCALAPPDATA%\yt-dlp-gui\crash.log`.

## Kaynaktan çalıştırma

```powershell
cd C:\Users\B\yt-dlp-gui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

İlk açılışta durum çubuğunda **«Araçlar hazırlanıyor…»** görürsünüz. Ardından:

1. URL yapıştırın  
2. **İndir**e basın  

Ses+video birleştirmesi (merge) için ffmpeg yolu otomatik `PATH`e eklenir. YouTube için Deno da aynı klasöre kurulur ve `--js-runtimes deno:<yol>` ile geçilir.

## Gereksinimler

- **Release .exe:** yalnızca Windows x64 + internet (ilk çalıştırma)
- **Kaynak:** Python 3.10+ (önerilen 3.13+)
- **Manuel ffmpeg, yt-dlp veya Deno kurulumu gerekmez**

İsteğe bağlı: çerez dosyası (`--cookies`) gelişmiş alanda seçilebilir.

## Özellikler

- Ana akış: URL → **İndir**
- Varsayılan çıktı klasörü: Kullanıcı `Downloads`
- Yönetilen araçlar: `%LOCALAPPDATA%\yt-dlp-gui\bin\` (`yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `deno.exe`)
- Gelişmiş: özel yt-dlp yolu, çerezler, tüm `yt-dlp` seçenek kataloğu, canlı komut önizlemesi
- Alt süreç ile indirme; log; **İptal** Windows’ta `taskkill /F /T`
- Ayarlar: `%APPDATA%\yt-dlp-gui\settings.json`

## Araçları yenileme

Arayüzdeki **Araçları Yenile** düğmesi yt-dlp / ffmpeg / Deno'yu yeniden indirir. Kaynaklar:

- yt-dlp: resmi GitHub `releases/latest` (`yt-dlp.exe`)
- ffmpeg: gyan.dev essentials zip (yedek: BtbN win64)
- Deno: denoland/deno `releases/latest` (`deno-x86_64-pc-windows-msvc.zip`)

## Windows .exe derleme (geliştiriciler)

```powershell
pip install -r requirements.txt pyinstaller
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Çıktı:

- `dist\yt-dlp-gui\yt-dlp-gui.exe` (onedir, çift tıklanabilir)
- `release\yt-dlp-gui-windows-x64.zip` (Release yüklemesi için)

`dist/`, `build/`, `release/` ve `*.exe` git'e commit edilmez. yt-dlp/ffmpeg/Deno exe içine gömülmez; uygulama ilk çalıştırmada LocalAppData'ya indirir.

## Katalog yenileme (geliştiriciler)

```powershell
& "$env:LOCALAPPDATA\yt-dlp-gui\bin\yt-dlp.exe" --help > yt-dlp-help.txt
python scripts\generate_catalog.py --help-file yt-dlp-help.txt --output app\options_catalog.json
```

`yt-dlp.exe`, ffmpeg ikilileri, medya ve çerez dosyaları commit edilmemelidir.

## Proje yapısı

```
main.py
build.ps1
app/
  catalog.py
  command_builder.py
  deps.py          # otomatik yt-dlp + ffmpeg + Deno kurulumu
  runner.py
  settings.py
  options_catalog.json
  ui/
    main_window.py
    option_widgets.py
scripts/
  generate_catalog.py
requirements.txt
```