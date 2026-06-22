# Resumen de la estructura del proyecto

## Objetivo general

El proyecto se ha orientado a la construcción de un **dataset de micrografías metalográficas** preparado para tareas futuras de:

- segmentación,
- clasificación,
- análisis por textura,
- y reconstrucción de la imagen original a partir de sus partes.

Hasta este punto, el flujo de trabajo ya contempla:

1. organización de imágenes originales por escala o aumento,
2. generación de *patches* o fragmentos,
3. trazabilidad completa entre cada parche y su imagen de origen,
4. y **data augmentation geométrico** sobre los parches generados.

---

## Principio de organización adoptado

Aunque varias imágenes comparten las mismas dimensiones en píxeles (`1280 x 960`), **no todas representan la misma escala física**.  
Por ejemplo:

- unas corresponden a `500 µm`, `250 µm`, `100 µm`, `50 µm`. `25 µm`
- y así sucesivamente.

Por esa razón, la organización del proyecto **no se hace solo por nombre de imagen**, sino también por **escala**. Esto evita mezclar patrones visuales que, aunque tengan el mismo tamaño en píxeles, representan realidades físicas distintas.

---

## Estructura general del proyecto

La estructura actual del proyecto puede resumirse así:

```text
dataset/
├── raw/
│   ├── scale_25um/
│   │   ├── MET0001.TIF
│   │   ├── MET0002.TIF
│   │   └── ...
│   ├── scale_500um/
│   │   ├── MET0001.TIF
│   │   ├── MET0002.TIF
│   │   └── ...
│   └── ...
│
├── patches/
│   ├── images/
│   │   ├── scale_25um/
│   │   │   ├── MET0001/
│   │   │   │   ├── MET0001_scale_25um_y0000_x0000.png
│   │   │   │   ├── MET0001_scale_25um_y0000_x0128.png
│   │   │   │   └── ...
│   │   │   ├── MET0002/
│   │   │   │   └── ...
│   │   ├── scale_500um/
│   │   │   ├── MET0001/
│   │   │   └── ...
│   │   └── ...
│   │
│   └── metadata/
│       ├── patches.csv
│       └── patches.json
│
├── augmented/
│   ├── images/
│   │   ├── scale_25um/
│   │   │   ├── MET0001/
│   │   │   │   ├── MET0001_scale_25um_y0000_x0000_rot90.png
│   │   │   │   ├── MET0001_scale_25um_y0000_x0000_rot180.png
│   │   │   │   ├── MET0001_scale_25um_y0000_x0000_rot270.png
│   │   │   │   ├── MET0001_scale_25um_y0000_x0000_flip_h.png
│   │   │   │   ├── MET0001_scale_25um_y0000_x0000_flip_v.png
│   │   │   │   └── ...
│   │   │   ├── MET0002/
│   │   │   │   └── ...
│   │   ├── scale_500um/
│   │   │   ├── MET0001/
│   │   │   └── ...
│   │   └── ...
│   │
│   └── metadata/
│       ├── augmented_patches.csv
│       └── augmented_patches.json
│
└── splits/
    ├── train.csv
    ├── val.csv
    └── test.csv
```

> **Nota:** la carpeta `splits/` representa la organización recomendada para las particiones del dataset.  
> Si aún no se ha generado, sigue siendo parte de la estructura prevista del proyecto.

---

## 1. Carpeta `raw/`: imágenes originales

Esta carpeta contiene las imágenes originales tal como provienen del microscopio, organizadas por escala.

### Ejemplo

```text
dataset/raw/scale_25um/
dataset/raw/scale_500um/
```

### Función

- conservar las imágenes fuente,
- separar las capturas según su escala física,
- evitar mezclar en una misma colección imágenes con aumentos distintos.

### Observación importante

Las imágenes pueden compartir nombres como `MET0001.TIF`, pero eso no genera conflicto porque están separadas por carpeta de escala.

---

## 2. Carpeta `patches/`: dataset base fragmentado

Esta carpeta contiene los **parches originales** generados a partir de cada imagen.

### Decisión tomada

Se definió una organización jerárquica:

1. por escala,
2. luego por imagen de origen,
3. y dentro de cada imagen, todos sus parches.

### Ejemplo

```text
dataset/patches/images/scale_25um/MET0001/
dataset/patches/images/scale_25um/MET0002/
```

### Ventajas de esta decisión

- permite identificar fácilmente qué parches pertenecen a una imagen concreta,
- facilita auditoría visual,
- ayuda a reconstruir la imagen original a partir de sus fragmentos,
- evita mezclar sin control los parches de varias imágenes.

---

## 3. Tamaño de parche y stride utilizados

Para la creación del dataset de parches se adoptó como configuración base:

- **patch size:** `256 x 256`
- **stride:** `128`

### Justificación

Se eligió `256 x 256` porque:

- es un tamaño estándar en visión por computador,
- facilita el uso posterior en arquitecturas tipo CNN o U-Net,
- mantiene contexto suficiente de la microestructura.

Se eligió `stride = 128` porque:

- introduce un solapamiento del 50%,
- mejora la cobertura espacial,
- ayuda a disminuir artefactos en los bordes de patch,
- y resulta útil si posteriormente se desea reconstruir la imagen a partir de predicciones por parche.

---

## 4. Padding aplicado

Como las dimensiones originales no siempre encajan exactamente con el tamaño del parche y el stride, el proyecto contempla un **padding automático** para ajustar la imagen.

### Tipo de padding usado

Se empleó:

- `cv2.BORDER_REFLECT`

### Finalidad

- completar borde inferior y/o derecho cuando sea necesario,
- garantizar que toda la imagen pueda recorrerse sistemáticamente con el stride definido,
- evitar pérdida de información por recortes bruscos.

---

## 5. Convención de nombres de patches

Cada parche generado incluye en su nombre información suficiente para rastrear su origen.

### Formato base

```text
<image_id>_<scale_name>_yYYYY_xXXXX.png
```

### Ejemplo

```text
MET0001_scale_25um_y0128_x0384.png
```

### Información codificada

- `image_id`: imagen original,
- `scale_name`: escala de captura,
- `y`: coordenada vertical del parche,
- `x`: coordenada horizontal del parche.

Esto permite que cada parche sea **único, interpretable y reconstruible**.

---

## 6. Metadata de los patches

Además de guardar las imágenes, el proyecto registra un archivo de metadatos.

### Archivos generados

```text
dataset/patches/metadata/patches.csv
dataset/patches/metadata/patches.json
```

### Contenido típico

Cada fila describe un parche con campos como:

- `patch_id`
- `image_id`
- `scale`
- `source_path`
- `patch_path`
- `patch_folder`
- `orig_h`
- `orig_w`
- `padded_h`
- `padded_w`
- `pad_h`
- `pad_w`
- `patch_size`
- `stride`
- `x`
- `y`
- `patch_index`
- `augmentation`

### Utilidad

Estos metadatos permiten:

- rastrear el origen exacto de cada fragmento,
- reconstruir una imagen completa a partir de sus parches,
- filtrar el dataset por escala o imagen,
- enlazar posteriormente imágenes, máscaras y predicciones.

---

## 7. Limpieza de barra de escala e información roja

Se identificó que varias imágenes contienen:

- barra de escala,
- texto rojo con la medida,
- y líneas rojas superpuestas.

### Problema detectado

Estos elementos pueden convertirse en **artefactos aprendibles** para un modelo, es decir:

- el modelo podría aprender la presencia del texto o la barra,
- en lugar de aprender realmente la microestructura.

Se deberían eliminar, sin embargo, no se ha aplicado una forma hasta el momento que lo haga correctamente.

---

## 8. Carpeta `augmented/`: dataset aumentado

Después de generar los patches base, se añadió una etapa de **data augmentation geométrico**.

### Tipo de augmentation aplicado

Hasta este punto, el augmentation aplicado fue **únicamente geométrico**:

- rotación 90°
- rotación 180°
- rotación 270°
- flip horizontal
- flip vertical

### Qué no se aplicó todavía

No se incorporaron aún transformaciones fotométricas como:

- cambio de brillo,
- cambio de contraste,
- ruido gaussiano.

Esto se dejó así para preservar mejor la fidelidad visual de la microestructura en una primera versión del dataset.

---

## 9. Organización del augmentation

La estructura del augmentation replica la del dataset base:

1. por escala,
2. por imagen,
3. por parche transformado.

### Ejemplo

```text
dataset/augmented/images/scale_25um/MET0001/
```

Dentro de esta carpeta se guardan las variantes aumentadas de los patches pertenecientes a `MET0001`.

### Ejemplo de nombres

```text
MET0001_scale_25um_y0000_x0000_rot90.png
MET0001_scale_25um_y0000_x0000_rot180.png
MET0001_scale_25um_y0000_x0000_rot270.png
MET0001_scale_25um_y0000_x0000_flip_h.png
MET0001_scale_25um_y0000_x0000_flip_v.png
```

### Ventaja de esta organización

- se preserva la trazabilidad,
- cada imagen sigue conservando su conjunto propio,
- se puede saber exactamente de qué parche nació cada variante aumentada.

---

## 10. Metadata del augmentation

También se generan metadatos específicos para las imágenes aumentadas.

### Archivos

```text
dataset/augmented/metadata/augmented_patches.csv
dataset/augmented/metadata/augmented_patches.json
```

### Campos típicos

- `aug_patch_id`
- `original_patch_id`
- `image_id`
- `scale`
- `source_patch_path`
- `aug_patch_path`
- `augmentation`

### Utilidad

Con esta metadata es posible:

- conocer la relación entre un parche original y su versión aumentada,
- reconstruir el historial de transformaciones,
- y filtrar por tipo de augmentación.

---

## 11. Trazabilidad y reconstrucción futura

Uno de los principios fuertes del proyecto es que el dataset no solo sirva para entrenar modelos, sino también para **volver a ensamblar la imagen original** a partir de sus partes.

Esto es posible porque cada parche conserva:

- la imagen original de donde proviene,
- la escala,
- su posición `x, y`,
- el tamaño de parche,
- y el stride.

### Implicación práctica

Si más adelante se segmenta parche por parche, será posible:

- volver a ubicar cada predicción en su posición correcta,
- reconstruir la predicción de la imagen completa,
- y combinar zonas solapadas mediante promedio, votación o fusión ponderada.

---

## 12. Regla metodológica para particiones del dataset

Se estableció una regla importante para evitar fuga de información:

### El split no debe hacerse por parche
No conviene mezclar parches de una misma imagen entre `train`, `val` y `test`.

### El split correcto debe hacerse por imagen original
Es decir:

- una imagen completa va a `train`,
- otra imagen completa va a `val`,
- otra imagen completa va a `test`.

### Razón

Si parches vecinos de una misma imagen caen en conjuntos diferentes, el modelo vería información casi idéntica en entrenamiento y validación, lo que falsearía la evaluación.

---

## 13. Estado actual del proyecto

Hasta este punto, el proyecto ya cuenta con:

- imágenes originales organizadas por escala,
- lógica de extracción de patches,
- padding automático para cobertura completa,
- encarpetado por imagen dentro de cada escala,
- metadata de patches,
- estrategia para remover barras de escala,
- augmentation geométrico,
- metadata del augmentation,
- y una estructura preparada para futuros splits y reconstrucción.

---

## 14. Próximos pasos naturales

Con la estructura actual, los siguientes pasos recomendados serían:

1. generar formalmente `train.csv`, `val.csv` y `test.csv` por imagen original,
2. aplicar augmentation solo sobre `train`,
3. incorporar máscaras cuando exista una estrategia de segmentación válida,
4. entrenar modelo de segmentación o clasificación,
5. y reconstruir la imagen completa a partir de las predicciones sobre parches.

---

## Conclusión

La estructura actual del proyecto ya está organizada con un criterio sólido de:

- **separación por escala**,
- **trazabilidad por imagen de origen**,
- **fragmentación controlada en patches**,
- **augmentation geométrico reproducible**,
- y **preparación para reconstrucción posterior**.

Esto deja una base muy adecuada para evolucionar hacia un pipeline de segmentación supervisada o análisis de microestructuras por aprendizaje automático.
