# yt-dlp GUI (CustomTkinter)

Windows için **yt-dlp** grafik arayüzü. Tüketiciler için kurulum yok: uygulama ilk çalıştırmada `yt-dlp.exe` ve `ffmpeg` araçlarını kendisi indirir. Yapmanız gereken tek şey URL yapıştırıp **İndir**e basmak.

## Hızlı başlangıç

```powershell
cd C:\Users\B\yt-dlp-gui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

İlk açılışta durum çubuğunda **«Araçlar hazırlanıyor…»** görürsünüz. yt-dlp ve ffmpeg `%LOCALAPPDATA%\yt-dlp-gui\bin\` altına iner (yönetici yetkisi gerekmez). Ardından:

1. URL yapıştırın  
2. **İndir**e basın  

Ses+video birleştirmesi (merge) için ffmpeg yolu otomatik `PATH`e eklenir.

## Gereksinimler

- Python 3.10+ (önerilen 3.13+)
- İnternet (yalnızca ilk çalıştırma / araç yenileme)
- **Manuel ffmpeg veya yt-dlp kurulumu gerekmez**

İsteğe bağlı: çerez dosyası (`--cookies`) gelişmiş alanda seçilebilir.

## Özellikler

- Ana akış: URL → **İndir**
- Varsayılan çıktı klasörü: Kullanıcı `Downloads`
- Yönetilen araçlar: `%LOCALAPPDATA%\yt-dlp-gui\bin\` (`yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`)
- Gelişmiş: özel yt-dlp yolu, çerezler, tüm `yt-dlp` seçenek kataloğu, canlı komut önizlemesi
- Alt süreç ile indirme; log; **İptal** Windows’ta `taskkill /F /T`
- Ayarlar: `%APPDATA%\yt-dlp-gui\settings.json`

## Araçları yenileme

Arayüzdeki **Araçları Yenile** düğmesi yt-dlp / ffmpeg’i yeniden indirir. Kaynaklar:

- yt-dlp: resmi GitHub `releases/latest` (`yt-dlp.exe`)
- ffmpeg: gyan.dev essentials zip (yedek: BtbN win64)

## Katalog yenileme (geliştiriciler)

```powershell
& "$env:LOCALAPPDATA\yt-dlp-gui\bin\yt-dlp.exe" --help > yt-dlp-help.txt
python scripts\generate_catalog.py --help-file yt-dlp-help.txt --output app\options_catalog.json
```

`yt-dlp.exe`, ffmpeg ikilileri, medya ve çerez dosyaları commit edilmemelidir.

## Proje yapısı

```
main.py
app/
  catalog.py
  command_builder.py
  deps.py          # otomatik yt-dlp + ffmpeg kurulumu
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
