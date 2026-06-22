import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

SOURCE_ROOT_DEFAULT = Path("./dataset/augmented/images")
OUTPUT_ROOT_DEFAULT = Path("./dataset/preprocessed_augmented/images")
OUTPUT_META_DIR_DEFAULT = Path("./dataset/preprocessed_augmented/metadata")

# SOURCE_ROOT_DEFAULT = Path("./dataset/patches/images")
# OUTPUT_ROOT_DEFAULT = Path("./dataset/preprocessed/images")
# OUTPUT_META_DIR_DEFAULT = Path("./dataset/preprocessed/metadata")


def read_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def save_image_rgb(image_rgb: np.ndarray, save_path: Path) -> None:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(save_path), image_bgr)


def detect_holes(image_rgb: np.ndarray, v_threshold=60, min_area=10, closing_ksize=1) -> np.ndarray:
    image_uint8 = (np.clip(image_rgb, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2HSV)
    v_channel = hsv[:, :, 2]

    mask = (v_channel < v_threshold).astype(np.uint8)

    if closing_ksize > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_ksize, closing_ksize))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    clean_mask = np.zeros_like(mask)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            clean_mask[labels == i] = 1

    return clean_mask.astype(np.float32)


def detect_white_high_intensity_regions(
    image_rgb: np.ndarray,
    v_min=180,
    s_max=75,
    rgb_min=145,
    channel_diff_max=45,
    exclude_mask=None,
    closing_ksize=3,
    min_area=15,
) -> np.ndarray:
    image_uint8 = (np.clip(image_rgb, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2HSV)

    r_channel = image_uint8[:, :, 0]
    g_channel = image_uint8[:, :, 1]
    b_channel = image_uint8[:, :, 2]
    s_channel = hsv[:, :, 1]
    v_channel = hsv[:, :, 2]

    max_rgb = np.maximum.reduce([r_channel, g_channel, b_channel])
    min_rgb = np.minimum.reduce([r_channel, g_channel, b_channel])
    diff_rgb = max_rgb - min_rgb

    mask_white = (
        (v_channel >= v_min)
        & (s_channel <= s_max)
        & (r_channel >= rgb_min)
        & (g_channel >= rgb_min)
        & (b_channel >= rgb_min)
        & (diff_rgb <= channel_diff_max)
    ).astype(np.uint8)

    if exclude_mask is not None:
        mask_white[exclude_mask == 1] = 0

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_ksize, closing_ksize))
    mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_OPEN, kernel)
    mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_white, connectivity=8)
    clean_mask = np.zeros_like(mask_white)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            clean_mask[labels == i] = 1

    return clean_mask.astype(np.float32)


def paint_mask_solid_color(image_rgb: np.ndarray, mask: np.ndarray, color=(1.0, 0.0, 0.0)) -> np.ndarray:
    result = image_rgb.copy().astype(np.float32)
    result[mask == 1] = np.array(color, dtype=np.float32)
    return np.clip(result, 0, 1)


def preprocess_image(image_path: Path) -> tuple[np.ndarray, dict]:
    image_rgb = read_image(image_path).astype(np.float32) / 255.0

    mask_holes = detect_holes(image_rgb, v_threshold=60, min_area=10, closing_ksize=1)
    mask_white = detect_white_high_intensity_regions(
        image_rgb,
        v_min=180,
        s_max=75,
        rgb_min=145,
        channel_diff_max=45,
        exclude_mask=mask_holes,
        closing_ksize=3,
        min_area=15,
    )

    i_debug = image_rgb.copy().astype(np.float32)
    i_debug = np.clip(i_debug, 0, 1)
    i_debug[mask_holes == 1] = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    i_debug[mask_white == 1] = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    k_uint8 = (np.clip(i_debug, 0, 1) * 255).astype(np.uint8)
    khsv = cv2.cvtColor(k_uint8, cv2.COLOR_RGB2HSV)
    khsv[:, :, 2] = cv2.equalizeHist(khsv[:, :, 2])
    knew = cv2.cvtColor(khsv, cv2.COLOR_HSV2RGB)
    knew_float = knew.astype(np.float32) / 255.0

    metadata = {
        "source_path": str(image_path),
        "hole_pixels": int(mask_holes.sum()),
        "white_pixels": int(mask_white.sum()),
        "output_shape_h": int(knew_float.shape[0]),
        "output_shape_w": int(knew_float.shape[1]),
    }

    return (knew_float * 255).astype(np.uint8), metadata


def find_image_files(source_root: Path):
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.TIF", "*.TIFF"]
    files = []
    for pattern in patterns:
        files.extend(source_root.rglob(pattern))
    return sorted({p for p in files if p.is_file()})


def build_preprocessed_dataset(source_root: Path, output_root: Path, metadata_dir: Path, limit: int | None = None):
    image_files = find_image_files(source_root)
    if limit is not None:
        image_files = image_files[:limit]

    output_root.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for image_path in image_files:
        rel_path = image_path.relative_to(source_root)
        output_path = output_root / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        preprocessed, meta = preprocess_image(image_path)
        save_image_rgb(preprocessed, output_path)

        rows.append({
            "source_path": str(image_path),
            "output_path": str(output_path),
            "relative_path": str(rel_path),
            **meta,
        })

        print(f"Procesada: {rel_path}")

    df = pd.DataFrame(rows)
    csv_path = metadata_dir / "preprocessed.csv"
    json_path = metadata_dir / "preprocessed.json"
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    print("Dataset preprocesado generado.")
    print(f"Imágenes: {len(df)}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Preprocesa imágenes de patches con el flujo de EDA_analisys.ipynb.")
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT_DEFAULT, help="Carpeta de entrada (por defecto dataset/patches/images)")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT_DEFAULT, help="Carpeta de salida (por defecto dataset/preprocessed/images)")
    parser.add_argument("--metadata-dir", type=Path, default=OUTPUT_META_DIR_DEFAULT, help="Carpeta para metadata CSV/JSON")
    parser.add_argument("--limit", type=int, default=None, help="Procesar solo las primeras N imágenes para pruebas")
    return parser.parse_args()


def main():
    args = parse_args()
    build_preprocessed_dataset(args.source_root, args.output_root, args.metadata_dir, limit=args.limit)


if __name__ == "__main__":
    main()