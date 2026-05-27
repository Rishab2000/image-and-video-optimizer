#!/usr/bin/python3
import os
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

# Configuration
input_dir = "."  # Current directory
output_dir = "webp_output"
quality = 80
formats = {".jpg", ".jpeg", ".png", ".heic"}

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
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not copy metadata for {source_path.name}")
        return False

def convert_heic_to_jpeg(heic_path, jpeg_path):
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(heic_path), "--out", str(jpeg_path)],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting HEIC to JPEG: {e}")
        return False

def get_unique_output_path(base_path, output_dir):
    counter = 1
    output_path = Path(output_dir) / f"{base_path.stem}.webp"
    while output_path.exists():
        output_path = Path(output_dir) / f"{base_path.stem}_{counter}.webp"
        counter += 1
    return output_path

def write_report(results, output_dir, has_exiftool):
    report_path = Path(output_dir) / "conversion_log.txt"

    successful = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] == "FAILED"]

    with open(report_path, "w") as f:
        f.write("Image Conversion Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("SUMMARY\n")
        f.write(f"  Total found : {len(results)}\n")
        f.write(f"  Converted   : {len(successful)}\n")
        f.write(f"  Failed      : {len(failed)}\n")
        if has_exiftool:
            metadata_ok = sum(1 for r in successful if r.get("metadata_ok"))
            f.write(f"  Metadata OK : {metadata_ok} / {len(successful)}\n")
        f.write("\n")

        if failed:
            f.write("FAILED CONVERSIONS\n")
            for r in failed:
                f.write(f"  - {r['input']}\n")
                if r.get("error"):
                    f.write(f"    Reason: {r['error']}\n")
            f.write("\n")

        metadata_warnings = [r for r in successful if not r.get("metadata_ok", True)]
        if has_exiftool and metadata_warnings:
            f.write("METADATA WARNINGS\n")
            for r in metadata_warnings:
                f.write(f"  - {r['input']} → {Path(r['output']).name}\n")
            f.write("\n")

        f.write("ALL CONVERSIONS\n")
        f.write(f"  {'INPUT FILE':<40} {'OUTPUT FILE':<40} STATUS\n")
        f.write("  " + "-" * 90 + "\n")
        for r in results:
            output_name = Path(r["output"]).name if r["output"] else "-"
            status = r["status"]
            if r.get("renamed"):
                status += " (renamed)"
            if has_exiftool and r["status"] == "OK" and not r.get("metadata_ok", True):
                status += " (metadata warning)"
            f.write(f"  {r['input']:<40} {output_name:<40} {status}\n")

    return report_path


# ── Setup ──────────────────────────────────────────────────────────────────────

os.makedirs(output_dir, exist_ok=True)

has_exiftool = check_exiftool()
if not has_exiftool:
    print("Warning: exiftool not found. Metadata will not be preserved.")
    print("Install it with: brew install exiftool\n")

image_files = [
    f for f in Path(input_dir).iterdir()
    if f.is_file() and f.suffix.lower() in formats and f.parent.name != output_dir
]

print(f"Found {len(image_files)} images to convert\n")

# ── Conversion ─────────────────────────────────────────────────────────────────

results = []

for img_path in image_files:
    output_path = get_unique_output_path(img_path, output_dir)
    renamed = output_path.stem != img_path.stem
    record = {"input": img_path.name, "output": str(output_path), "renamed": renamed, "metadata_ok": None}

    try:
        if img_path.suffix.lower() == ".heic":
            temp_jpg = Path(output_dir) / f"{img_path.stem}_temp.jpg"

            if not convert_heic_to_jpeg(img_path, temp_jpg):
                raise Exception("HEIC to JPEG conversion failed")

            subprocess.run(
                ["cwebp", "-q", str(quality), "-metadata", "all", str(temp_jpg), "-o", str(output_path)],
                check=True, capture_output=True
            )
            temp_jpg.unlink()
        else:
            subprocess.run(
                ["cwebp", "-q", str(quality), "-metadata", "all", str(img_path), "-o", str(output_path)],
                check=True, capture_output=True
            )

        # Copy metadata from the original source (covers HEIC too)
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
        record["error"] = str(e)
        print(f"  ✗ {img_path.name} — conversion failed")
    except Exception as e:
        record["status"] = "FAILED"
        record["output"] = None
        record["error"] = str(e)
        print(f"  ✗ {img_path.name} — {e}")

    results.append(record)

# ── Summary ────────────────────────────────────────────────────────────────────

successful = [r for r in results if r["status"] == "OK"]
failed = [r for r in results if r["status"] == "FAILED"]

print(f"\nDone: {len(successful)}/{len(image_files)} converted", end="")
print(f"  |  {len(failed)} failed" if failed else "")

report_path = write_report(results, output_dir, has_exiftool)
print(f"\nFull report: {report_path}")
