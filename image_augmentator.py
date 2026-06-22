import cv2
import json
import pandas as pd
from pathlib import Path

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
PATCHES_DIR = Path("./dataset/patches/images")
AUG_DIR = Path("./dataset/augmented/images")
AUG_META_DIR = Path("./dataset/augmented/metadata")

SAVE_EXT = ".png"

AUG_META_DIR.mkdir(parents=True, exist_ok=True)
AUG_DIR.mkdir(parents=True, exist_ok=True)


def read_image_rgb(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def save_image_rgb(image_rgb, save_path):
    save_path.parent.mkdir(parents=True, exist_ok=True)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(save_path), image_bgr)


# -----------------------------
# AUGMENTATIONS
# -----------------------------
def aug_rot90(img):
    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)


def aug_rot180(img):
    return cv2.rotate(img, cv2.ROTATE_180)


def aug_rot270(img):
    return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)


def aug_flip_h(img):
    return cv2.flip(img, 1)   # horizontal


def aug_flip_v(img):
    return cv2.flip(img, 0)   # vertical


AUGMENTATIONS = {
    "rot90": aug_rot90,
    "rot180": aug_rot180,
    "rot270": aug_rot270,
    "flip_h": aug_flip_h,
    "flip_v": aug_flip_v,
}


def process_patch_file(patch_path, scale_name, image_id):
    """
    Genera augmentations para un patch individual.
    """
    image = read_image_rgb(patch_path)
    patch_stem = patch_path.stem

    output_dir = AUG_DIR / scale_name / image_id
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for aug_name, aug_fn in AUGMENTATIONS.items():
        aug_img = aug_fn(image)

        aug_patch_id = f"{patch_stem}_{aug_name}"
        aug_filename = aug_patch_id + SAVE_EXT
        aug_path = output_dir / aug_filename

        save_image_rgb(aug_img, aug_path)

        rows.append({
            "aug_patch_id": aug_patch_id,
            "original_patch_id": patch_stem,
            "image_id": image_id,
            "scale": scale_name,
            "source_patch_path": str(patch_path),
            "aug_patch_path": str(aug_path),
            "augmentation": aug_name
        })

    return rows


def process_image_folder(image_folder, scale_name):
    """
    Procesa todos los patches de una imagen.
    """
    image_id = image_folder.name
    rows = []

    patch_files = sorted(list(image_folder.glob("*.png")) + list(image_folder.glob("*.tif")) + list(image_folder.glob("*.TIF")))

    for patch_path in patch_files:
        patch_rows = process_patch_file(patch_path, scale_name, image_id)
        rows.extend(patch_rows)

    return rows


def process_scale_folder(scale_folder):
    """
    Procesa todas las carpetas de imágenes dentro de una escala.
    """
    scale_name = scale_folder.name
    rows = []

    image_folders = [p for p in scale_folder.iterdir() if p.is_dir()]

    for image_folder in sorted(image_folders):
        image_rows = process_image_folder(image_folder, scale_name)
        rows.extend(image_rows)

    return rows


def build_augmented_dataset():
    all_rows = []

    scale_folders = [p for p in PATCHES_DIR.iterdir() if p.is_dir()]

    for scale_folder in sorted(scale_folders):
        rows = process_scale_folder(scale_folder)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)

    csv_path = AUG_META_DIR / "augmented_patches.csv"
    json_path = AUG_META_DIR / "augmented_patches.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    print("Dataset aumentado generado.")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Total de patches augmentados: {len(df)}")


if __name__ == "__main__":
    build_augmented_dataset()