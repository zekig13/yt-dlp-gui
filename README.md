# yt-dlp GUI (CustomTkinter)

Windows için **yt-dlp** grafik arayüzü. Türkçe etiketler, İngilizce CLI bayrakları; `yt-dlp --help` çıktısından üretilmiş tam seçenek kataloğu.

## Gereksinimler

- Python 3.13+ (3.10+ da çalışır)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (`C:\yt-dlp\yt-dlp.exe` varsayılan)
- İsteğe bağlı: `C:\yt-dlp\cookies.txt`

## Kurulum

```powershell
cd C:\Users\B\yt-dlp-gui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma

```powershell
python main.py
```

## Özellikler

- Ana panel: URL(ler), çıktı klasörü (`-P`), çıktı şablonu (`-o`), biçim kısayolu, çerezler, yt-dlp yolu
- Tüm `yt-dlp` seçenekleri (yardım metninden): bölümler halinde, aranabilir, kaydırılabilir
- Canlı komut önizlemesi
- Alt süreç ile indirme; log akışı; **İptal** Windows’ta `taskkill /F /T` ile süreç ağacını öldürür
- Ayarlar: `%APPDATA%\yt-dlp-gui\settings.json`

## Katalog yenileme

`yt-dlp.exe --help` çıktısını kaydedip kataloğu yeniden üretin:

```powershell
& C:\yt-dlp\yt-dlp.exe --help > yt-dlp-help.txt
python scripts\generate_catalog.py --help-file yt-dlp-help.txt --output app\options_catalog.json
```

Üretilen `app/options_catalog.json` repoda tutulabilir; `yt-dlp.exe`, medya ve çerez dosyaları commit edilmemelidir.

## Proje yapısı

```
main.py
app/
  catalog.py
  command_builder.py
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
