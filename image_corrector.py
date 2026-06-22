import cv2
import numpy as np
import os
from pathlib import Path
from tqdm import tqdm

# Configuración de rutas
DATASET_DIR = './dataset'
RAW_DIR = os.path.join(DATASET_DIR, 'raw')
RAW_CORRECTED_DIR = os.path.join(DATASET_DIR, 'raw_corrected')

# Escalas a procesar
SCALES = ['scale_25um', 'scale_50um', 'scale_100um', 'scale_250um', 'scale_500um']

def inpaint_by_median(img, mask, max_radius=7):
    """Inpaint de píxeles enmascarados usando mediana de vecinos válidos."""
    img_out = img.copy().astype(np.float32)
    h, w = mask.shape
    mask_bool = (mask > 0)
    ys, xs = np.where(mask_bool)
    for y, x in zip(ys, xs):
        replaced = False
        for r in range(1, max_radius+1):
            y0 = max(0, y-r); y1 = min(h, y+r+1)
            x0 = max(0, x-r); x1 = min(w, x+r+1)
            patch = img_out[y0:y1, x0:x1]
            patch_mask = mask_bool[y0:y1, x0:x1]
            # seleccionar píxeles válidos (no en máscara)
            valid = patch[~patch_mask]
            if valid.size >= 3:
                med = np.median(valid.reshape(-1,3), axis=0)
                img_out[y, x] = med
                replaced = True
                break
        if not replaced:
            # fallback: usar inpaint de OpenCV cerca del punto
            pass
    return np.clip(img_out, 0, 255).astype(np.uint8)


def correct_image_outliers(img_rgb):
    """Aplica la corrección de outliers rojos a una imagen."""
    img_float = img_rgb.astype(np.float32)
    
    # --- 1. Detección de outliers por color ---
    mean_color = np.mean(img_float.reshape(-1,3), axis=0)
    dist = np.sqrt(np.sum((img_float - mean_color)**2, axis=2))
    threshold = np.percentile(dist, 99.5)
    mask_outliers = (dist > threshold).astype(np.uint8) * 255

    # --- 2. Detección de rojo en HSV ---
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    lower_red1 = np.array([0, 100, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 50])
    upper_red2 = np.array([180, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)

    # Limpiar la máscara HSV de rojo
    kernel_red_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
    mask_red_clean = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel_red_open, iterations=1)
    mask_red_clean = cv2.morphologyEx(mask_red_clean, cv2.MORPH_CLOSE, kernel_red_open, iterations=1)
    # Dilatar ligeramente en horizontal
    kernel_red_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,3))
    mask_red_clean = cv2.dilate(mask_red_clean, kernel_red_dilate, iterations=1)
    mask_red_clean = (mask_red_clean > 0).astype(np.uint8) * 255

    # Guardar la máscara HSV original
    mask_red_exact = mask_red.copy()

    # --- 3. Combinar máscaras ---
    mask_combined = cv2.bitwise_or(mask_outliers, mask_red)

    # --- 4. Limpiar máscara con morfología ---
    kernel = np.ones((3,3), np.uint8)
    mask_clean = cv2.morphologyEx(mask_combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel, iterations=1)
    # Dilatar un poco la máscara
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,9))
    mask_dilated = cv2.dilate(mask_clean, kernel_dilate, iterations=2)
    mask_dilated = (mask_dilated > 0).astype(np.uint8) * 255

    # --- 5. Aplicar inpaint por mediana ---
    mask_for_inpaint = mask_red_exact.astype(np.uint8)
    result_corrected = inpaint_by_median(img_rgb, mask_for_inpaint, max_radius=7)
    
    return result_corrected


def process_all_images():
    """Procesa todas las imágenes en las carpetas raw y guarda en raw_corrected."""
    
    # Crear directorio raw_corrected si no existe
    Path(RAW_CORRECTED_DIR).mkdir(parents=True, exist_ok=True)
    
    total_images = 0
    processed_images = 0
    
    # Contar total de imágenes
    for scale in SCALES:
        scale_dir = os.path.join(RAW_DIR, scale)
        if os.path.exists(scale_dir):
            total_images += len([f for f in os.listdir(scale_dir) if f.lower().endswith('.tif')])
    
    print(f"Total de imágenes a procesar: {total_images}")
    print(f"Procesando imágenes de: {RAW_DIR}")
    print(f"Guardando en: {RAW_CORRECTED_DIR}\n")
    
    # Procesar cada escala
    for scale in SCALES:
        scale_src = os.path.join(RAW_DIR, scale)
        scale_dst = os.path.join(RAW_CORRECTED_DIR, scale)
        
        if not os.path.exists(scale_src):
            print(f"[SKIP] {scale} - no existe")
            continue
        
        # Crear directorio de destino
        Path(scale_dst).mkdir(parents=True, exist_ok=True)
        
        # Procesar imágenes en esta escala
        image_files = [f for f in os.listdir(scale_src) if f.lower().endswith('.tif')]
        
        if not image_files:
            print(f"[SKIP] {scale} - no contiene imágenes")
            continue
        
        print(f"\nProcesando escala: {scale}")
        print(f"  Imágenes: {len(image_files)}")
        
        for img_name in tqdm(image_files, desc=f"  {scale}"):
            try:
                img_path = os.path.join(scale_src, img_name)
                out_path = os.path.join(scale_dst, img_name)
                
                # Leer imagen
                img_bgr = cv2.imread(img_path)
                if img_bgr is None:
                    print(f"    [ERROR] No se pudo leer: {img_name}")
                    continue
                
                # Convertir a RGB
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                
                # Aplicar corrección
                img_corrected_rgb = correct_image_outliers(img_rgb)
                
                # Convertir a BGR para guardar con OpenCV
                img_corrected_bgr = cv2.cvtColor(img_corrected_rgb, cv2.COLOR_RGB2BGR)
                
                # Guardar imagen
                cv2.imwrite(out_path, img_corrected_bgr)
                processed_images += 1
                
            except Exception as e:
                print(f"    [ERROR] {img_name}: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"Procesamiento completado!")
    print(f"Imágenes procesadas: {processed_images}/{total_images}")
    print(f"Directorio de salida: {RAW_CORRECTED_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    process_all_images()
