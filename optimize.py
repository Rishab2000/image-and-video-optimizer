#!/usr/bin/python3
import os
import subprocess
from pathlib import Path
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
input_dir        = "."
image_output_dir = "webp_output"
video_output_dir = "hevc_output"
image_quality    = 80   # WebP quality (0–100)
video_crf        = "28" # HEVC CRF — lower = better quality, larger file

image_formats = {
    # Standard
    ".jpg", ".jpeg", ".png", ".heic",
    # RAW formats
    ".dng",          # Adobe / generic
    ".cr2", ".cr3",  # Canon
    ".nef", ".nrw",  # Nikon
    ".arw",          # Sony
    ".raf",          # Fujifilm
    ".orf",          # Olympus
    ".rw2",          # Panasonic
    ".pef",          # Pentax
    ".srw",          # Samsung
}
video_formats = {".mov", ".mp4", ".avi", ".mkv"}

# ── Shared helpers ─────────────────────────────────────────────────────────────

def check_tool(name):
    try:
        subprocess.run([name, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run([name, "-ver"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

def check_exiftool():
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def copy_metadata(source_path, dest_path):
    try:
        subprocess.run([
            "exiftool",
            "-TagsFromFile", str(source_path),
            "-all:all",
            "-overwrite_original",
            str(dest_path)
        ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print(f"  Warning: Could not copy metadata for {source_path.name}")
        return False

def get_unique_output_path(base_path, out_dir, ext):
    counter = 1
    output_path = Path(out_dir) / f"{base_path.stem}{ext}"
    while output_path.exists():
        output_path = Path(out_dir) / f"{base_path.stem}_{counter}{ext}"
        counter += 1
    return output_path

# ── Image conversion ───────────────────────────────────────────────────────────

def convert_heic_to_jpeg(heic_path, jpeg_path):
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(heic_path), "--out", str(jpeg_path)],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error converting HEIC to JPEG: {e}")
        return False

def convert_image(img_path, has_exiftool):
    output_path = get_unique_output_path(img_path, image_output_dir, ".webp")
    renamed = output_path.stem != img_path.stem
    record = {
        "input": img_path.name,
        "output": str(output_path),
        "renamed": renamed,
        "metadata_ok": None,
        "type": "image",
    }

    try:
        raw_formats = {".heic", ".dng", ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".raf", ".orf", ".rw2", ".pef", ".srw"}
        if img_path.suffix.lower() in raw_formats:
            temp_jpg = Path(image_output_dir) / f"{img_path.stem}_temp.jpg"
            if not convert_heic_to_jpeg(img_path, temp_jpg):
                raise Exception("HEIC to JPEG conversion failed")
            subprocess.run(
                ["cwebp", "-q", str(image_quality), "-metadata", "all", str(temp_jpg), "-o", str(output_path)],
                check=True, capture_output=True
            )
            temp_jpg.unlink()
        else:
            subprocess.run(
                ["cwebp", "-q", str(image_quality), "-metadata", "all", str(img_path), "-o", str(output_path)],
                check=True, capture_output=True
            )

        if has_exiftool:
            record["metadata_ok"] = copy_metadata(img_path, output_path)

        record["status"] = "OK"
        label = f"  ✓ {img_path.name} → {output_path.name}"
        if renamed:
            label += "  (renamed to avoid duplicate)"
        print(label)

    except subprocess.CalledProcessError as e:
        record["status"] = "FAILED"
        record["output"] = None
        record["error"] = e.stderr.decode().strip() if e.stderr else str(e)
        print(f"  ✗ {img_path.name} — conversion failed")
    except Exception as e:
        record["status"] = "FAILED"
        record["output"] = None
        record["error"] = str(e)
        print(f"  ✗ {img_path.name} — {e}")

    return record

# ── Video conversion ───────────────────────────────────────────────────────────

def convert_video(vid_path, has_exiftool):
    output_path = get_unique_output_path(vid_path, video_output_dir, ".mp4")
    renamed = output_path.stem != vid_path.stem
    record = {
        "input": vid_path.name,
        "output": str(output_path),
        "renamed": renamed,
        "metadata_ok": None,
        "type": "video",
    }

    try:
        subprocess.run([
            "ffmpeg",
            "-loglevel", "error",
            "-i", str(vid_path),
            "-c:v", "libx265", "-tag:v", "hvc1",
            "-crf", video_crf,
            "-c:a", "copy",
            str(output_path)
        ], check=True, capture_output=True)

        if has_exiftool:
            record["metadata_ok"] = copy_metadata(vid_path, output_path)

        record["status"] = "OK"
        label = f"  ✓ {vid_path.name} → {output_path.name}"
        if renamed:
            label += "  (renamed to avoid duplicate)"
        print(label)

    except subprocess.CalledProcessError as e:
        record["status"] = "FAILED"
        record["output"] = None
        record["error"] = e.stderr.decode().strip() if e.stderr else str(e)
        # Clean up partial output file if ffmpeg created one
        if output_path.exists():
            output_path.unlink()
        print(f"  ✗ {vid_path.name} — conversion failed")
    except Exception as e:
        record["status"] = "FAILED"
        record["output"] = None
        record["error"] = str(e)
        print(f"  ✗ {vid_path.name} — {e}")

    return record

# ── Report ─────────────────────────────────────────────────────────────────────

def write_report(image_results, video_results, has_exiftool):
    report_path = Path(input_dir) / "conversion_log.txt"

    all_results  = image_results + video_results
    successful   = [r for r in all_results if r["status"] == "OK"]
    failed       = [r for r in all_results if r["status"] == "FAILED"]
    img_ok       = [r for r in image_results if r["status"] == "OK"]
    vid_ok       = [r for r in video_results if r["status"] == "OK"]

    with open(report_path, "w") as f:
        f.write("Media Optimizer Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 65 + "\n\n")

        f.write("SUMMARY\n")
        if image_results:
            f.write(f"  Images : {len(img_ok)} / {len(image_results)} converted\n")
        if video_results:
            f.write(f"  Videos : {len(vid_ok)} / {len(video_results)} converted\n")
        f.write(f"  Total  : {len(successful)} / {len(all_results)} converted\n")
        if has_exiftool and successful:
            metadata_ok = sum(1 for r in successful if r.get("metadata_ok"))
            f.write(f"  Metadata preserved: {metadata_ok} / {len(successful)}\n")
        f.write("\n")

        if failed:
            f.write("FAILED\n")
            for r in failed:
                f.write(f"  - {r['input']}\n")
                if r.get("error"):
                    f.write(f"    {r['error']}\n")
            f.write("\n")

        metadata_warnings = [r for r in successful if r.get("metadata_ok") is False]
        if has_exiftool and metadata_warnings:
            f.write("METADATA WARNINGS\n")
            for r in metadata_warnings:
                f.write(f"  - {r['input']} → {Path(r['output']).name}\n")
            f.write("\n")

        for section_label, results in [("IMAGES", image_results), ("VIDEOS", video_results)]:
            if not results:
                continue
            f.write(f"{section_label}\n")
            f.write(f"  {'INPUT':<40} {'OUTPUT':<40} STATUS\n")
            f.write("  " + "-" * 90 + "\n")
            for r in results:
                output_name = Path(r["output"]).name if r["output"] else "-"
                status = r["status"]
                if r.get("renamed"):
                    status += " (renamed)"
                if has_exiftool and r["status"] == "OK" and r.get("metadata_ok") is False:
                    status += " (metadata warning)"
                f.write(f"  {r['input']:<40} {output_name:<40} {status}\n")
            f.write("\n")

    return report_path

# ── Main ───────────────────────────────────────────────────────────────────────

os.makedirs(image_output_dir, exist_ok=True)
os.makedirs(video_output_dir, exist_ok=True)

has_exiftool = check_exiftool()
if not has_exiftool:
    print("Warning: exiftool not found — metadata will not be preserved.")
    print("Install: brew install exiftool\n")

all_files = [f for f in Path(input_dir).iterdir() if f.is_file()]

image_files = [f for f in all_files if f.suffix.lower() in image_formats]
video_files = [f for f in all_files if f.suffix.lower() in video_formats]

print(f"Found {len(image_files)} image(s) and {len(video_files)} video(s)\n")

image_results = []
video_results = []

if image_files:
    print("── Images ────────────────────────────────────────────────────")
    for img_path in image_files:
        image_results.append(convert_image(img_path, has_exiftool))

if video_files:
    print("\n── Videos ────────────────────────────────────────────────────")
    for vid_path in video_files:
        video_results.append(convert_video(vid_path, has_exiftool))

all_results = image_results + video_results
successful  = [r for r in all_results if r["status"] == "OK"]
failed      = [r for r in all_results if r["status"] == "FAILED"]

print(f"\nDone: {len(successful)}/{len(all_results)} converted", end="")
print(f"  |  {len(failed)} failed" if failed else "")

report_path = write_report(image_results, video_results, has_exiftool)
print(f"Full report: {report_path}")
