import os
import cv2
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
RAW_DIR = Path("./dataset/raw_corrected")
PATCH_DIR = Path("./dataset/patches/images")
META_DIR = Path("./dataset/patches/metadata")

PATCH_SIZE = 256
STRIDE = 128
SAVE_EXT = ".png"

PATCH_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)


def read_image(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


def pad_image_to_fit_stride(image, patch_size=256, stride=128):
    """
    Añade padding al borde inferior/derecho para que la imagen pueda recorrerse
    completamente con el stride dado.
    """
    h, w = image.shape[:2]

    if h <= patch_size:
        new_h = patch_size
    else:
        new_h = patch_size + math.ceil((h - patch_size) / stride) * stride

    if w <= patch_size:
        new_w = patch_size
    else:
        new_w = patch_size + math.ceil((w - patch_size) / stride) * stride

    pad_h = new_h - h
    pad_w = new_w - w

    padded = cv2.copyMakeBorder(
        image,
        0, pad_h,
        0, pad_w,
        borderType=cv2.BORDER_REFLECT
    )
    return padded, pad_h, pad_w


def extract_patches(image, patch_size=256, stride=128):
    h, w = image.shape[:2]
    patches = []

    for y in range(0, h - patch_size + 1, stride):
        for x in range(0, w - patch_size + 1, stride):
            patch = image[y:y + patch_size, x:x + patch_size]
            patches.append((patch, x, y))

    return patches


def save_patch_rgb(patch, save_path):
    patch_bgr = cv2.cvtColor(patch, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(save_path), patch_bgr)


def process_scale_folder(scale_folder):
    scale_name = scale_folder.name
    output_scale_dir = PATCH_DIR / scale_name
    output_scale_dir.mkdir(parents=True, exist_ok=True)

    metadata_rows = []

    image_files = sorted(list(scale_folder.glob("*.TIF")) + list(scale_folder.glob("*.tif")))

    for image_path in image_files:
        image_id = image_path.stem

        # carpeta exclusiva para los patches de esta imagen
        output_image_dir = output_scale_dir / image_id
        output_image_dir.mkdir(parents=True, exist_ok=True)

        image = read_image(image_path)
        orig_h, orig_w = image.shape[:2]

        padded_img, pad_h, pad_w = pad_image_to_fit_stride(
            image,
            patch_size=PATCH_SIZE,
            stride=STRIDE
        )

        patches = extract_patches(
            padded_img,
            patch_size=PATCH_SIZE,
            stride=STRIDE
        )

        for idx, (patch, x, y) in enumerate(patches):
            patch_id = f"{image_id}_{scale_name}_y{y:04d}_x{x:04d}"
            patch_filename = patch_id + SAVE_EXT
            patch_path = output_image_dir / patch_filename

            save_patch_rgb(patch, patch_path)

            metadata_rows.append({
                "patch_id": patch_id,
                "image_id": image_id,
                "scale": scale_name,
                "source_path": str(image_path),
                "patch_path": str(patch_path),
                "patch_folder": str(output_image_dir),
                "orig_h": orig_h,
                "orig_w": orig_w,
                "padded_h": padded_img.shape[0],
                "padded_w": padded_img.shape[1],
                "pad_h": pad_h,
                "pad_w": pad_w,
                "patch_size": PATCH_SIZE,
                "stride": STRIDE,
                "x": x,
                "y": y,
                "patch_index": idx,
                "augmentation": "none"
            })

    return metadata_rows


def build_patch_dataset():
    all_rows = []

    scale_folders = [p for p in RAW_DIR.iterdir() if p.is_dir()]
    for scale_folder in scale_folders:
        rows = process_scale_folder(scale_folder)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)

    csv_path = META_DIR / "patches.csv"
    json_path = META_DIR / "patches.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    print("Dataset de parches generado.")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Total de parches: {len(df)}")


if __name__ == "__main__":
    build_patch_dataset()