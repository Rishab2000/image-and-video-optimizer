# media-optimizer

A Python script that batch converts images to WebP and videos to HEVC (H.265), reducing storage by roughly 50% without losing quality or metadata.

---

## What it does

- Converts images to **WebP** at quality 80 (configurable)
- Converts videos to **HEVC / H.265 MP4** at CRF 28 (configurable)
- Preserves all original metadata (EXIF, date taken, GPS, etc.)
- Never overwrites files — duplicates are automatically renamed
- Shows a live progress bar during conversion
- Writes a `conversion_log.txt` so you can verify nothing was lost

---

## Requirements

| Tool | Purpose | Install |
|---|---|---|
| Python 3 | Run the script | Pre-installed on macOS |
| `cwebp` | Convert images to WebP | `brew install webp` |
| `ffmpeg` | Convert videos to HEVC | `brew install ffmpeg` |
| `exiftool` | Preserve metadata | `brew install exiftool` |
| `sips` | Decode RAW / HEIC images | Pre-installed on macOS |
| `tqdm` | Progress bar | `pip3 install tqdm` |

Install all at once:
```bash
brew install webp ffmpeg exiftool && pip3 install tqdm
```

> `exiftool` is optional but strongly recommended — without it, metadata (date taken, GPS, camera info) will not be copied to the output files.

> `tqdm` is optional — if not installed, the script runs normally without a progress bar.

---

## Usage

1. Clone the repo somewhere on your machine:
```bash
git clone https://github.com/your-username/media-optimizer.git ~/media-optimizer
```

2. Open Terminal and navigate to the folder you want to optimize:
```bash
cd ~/Desktop/my-photos
```

3. Run the script:
```bash
/usr/bin/python3 ~/media-optimizer/optimize.py
```

The script will process everything in the current folder and write output to two subfolders:

```
my-photos/
├── webp_output/        ← converted images
├── hevc_output/        ← converted videos
└── conversion_log.txt  ← full audit log
```

---

## Supported formats

**Images** → WebP
| Format | Extensions |
|---|---|
| JPEG | `.jpg` `.jpeg` |
| PNG | `.png` |
| HEIC | `.heic` |
| Adobe DNG | `.dng` |
| Canon RAW | `.cr2` `.cr3` |
| Nikon RAW | `.nef` `.nrw` |
| Sony RAW | `.arw` |
| Fujifilm RAW | `.raf` |
| Olympus RAW | `.orf` |
| Panasonic RAW | `.rw2` |
| Pentax RAW | `.pef` |
| Samsung RAW | `.srw` |

**Videos** → HEVC MP4
`.mov` `.mp4` `.avi` `.mkv`

> Extension matching is case-insensitive, so `.JPG`, `.Jpg`, and `.jpg` are all handled.

---

## Configuration

Open `optimize.py` and edit the values at the top of the file:

```python
image_quality = 80   # WebP quality: 0 (smallest) – 100 (best). 80 is a good default.
video_crf     = "28" # HEVC quality: 18 (best) – 51 (worst). 28 is a good default.
```

---

## Conversion log

After every run, `conversion_log.txt` is written to the folder you ran the script from. It shows exactly what happened to every file:

```
Media Optimizer Report
Generated: 2026-05-27 10:30:00
=================================================================

SUMMARY
  Images : 22 / 23 converted
  Videos : 4 / 4 converted
  Total  : 26 / 27 converted
  Metadata preserved: 26 / 26

FAILED
  - corrupted.jpg
    <reason>

IMAGES
  INPUT                                    OUTPUT                                   STATUS
  ------------------------------------------------------------------------------------------
  IMG_0001.HEIC                            IMG_0001.webp                            OK
  IMG_0001.JPG                             IMG_0001_1.webp                          OK (renamed)
  corrupted.jpg                            -                                        FAILED
```

---

## Notes

- Original files are never modified or deleted — the script only writes to `webp_output/` and `hevc_output/`
- RAW format support depends on macOS's built-in Camera RAW engine via `sips` — newer camera models may require an up-to-date macOS version
- For maximum compatibility with older devices, you can change the video encoder in `optimize.py` from `libx265` to `libx264`
- Processing time varies based on file count, file size, and your hardware
