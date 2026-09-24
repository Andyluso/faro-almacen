> Consulta CORRECCIONES.md para acceso, respaldos privados y almacenamiento permanente en Railway. Las instalaciones nuevas requieren configurar el acceso y la nube en el servidor.

# Sistema de Control de Inventario y Catálogo Fotográfico - Seven Seven

Sistema web y móvil diseñado para la gestión de auditorías de inventario de **Tienda y Bodega** (Lunes y Miércoles) en tiendas Seven Seven.

---

## 🚀 ¿Cómo Iniciar el Sistema?

Simplemente haz **doble clic** sobre el archivo:
```text
iniciar_sistema.bat
```
El sistema:
1. Iniciará el servidor local.
2. Abrirá automáticamente la aplicación en tu navegador web (`http://localhost:8000`).
3. Te mostrará en pantalla la dirección IP para que también puedas abrirlo en tu **celular o tablet** conectado al Wi-Fi de la tienda.

---

## 📱 ¿Cómo usarlo desde el Celular para Tomar Fotos?
1. Asegúrate de que tu celular esté conectado a la misma red Wi-Fi que el computador.
2. En la barra superior de la app, haz clic en el botón de **Celular con ícono azul**.
3. Escanea con tu celular el **código QR** que aparece en pantalla (o escribe la dirección que te muestra en Chrome/Safari, ej: `http://192.168.1.50:8000`).
4. ¡Listo! Al tocar una prenda sin foto, podrás activar directamente la **cámara de tu celular** para tomar la foto en el perchero o en la bodega.

---

## 📋 Funcionalidades Principales

### 1. Carga Inteligente de Excel (.xlsx / .xls)
- Sube el archivo Excel que te envían al correo cada lunes y miércoles.
- El sistema detecta automáticamente las columnas, incluso si tienen nombres variados:
  - **Referencia** (`REF`, `REFERENCIA`, `COD_REF`)
  - **Nombre Prenda** (`DESCRIPCION`, `NOMBRE`, `PRENDA`)
  - **Talla** y **Color**
  - **Código de Barras** (`EAN`, `CODIGO_BARRAS`, `BARCODE`)
  - **Lectura Tienda** y **Lectura Bodega**
  - **Stock Teórico / Esperado**
  - **Diferencias** (calcula automáticamente si faltan o sobran)

### 2. Detección de Prendas Reincidentes (Prioritarias)
- El sistema guarda el historial de todas las lecturas previas.
- Si una prenda ha tenido diferencias en auditorías anteriores, se marca con la insignia 🔥 **Repetida (X veces)**.
- Puedes usar el filtro **"Reincidentes"** para revisar y solucionar primero las prendas con problemas crónicos.

### 3. Visor de Prenda en Pantalla Completa
- Haz clic en cualquier prenda para verla a pantalla completa.
- Muestra el desglose exacto:
  - Conteo Tienda
  - Conteo Bodega
  - Físico Total vs Teórico
  - Diferencia neta resaltada en rojo (faltante) o verde (sobrante).
- Historial con línea de tiempo de cómo se comportó esa prenda en inventarios pasados.
- Botones **"Anterior"**, **"Siguiente"** y **"Siguiente Pendiente"** para avanzar rápido por las 200+ referencias.

### 4. Captura Obligatoria de Fotos y Catálogo Maestro
- Si una referencia no tiene foto en el sistema, aparecerá una alerta destacada y la aplicación te solicitará tomarle foto o subirla antes de validar.
- **Catálogo Permanente**: Una vez le tomes foto a una referencia, queda guardada para siempre. En los inventarios de las próximas semanas, si esa referencia vuelve a salir, la foto ya aparecerá lista automáticamente.

### 5. Validación de Diferencias
- Selecciona rápidamente el motivo real del descuadre:
  - ❌ Faltante Real (Hurto o pérdida confirmada)
  - ➕ Sobrante Real (Mercancía no registrada)
  - 🔄 Error de Lectura / Mal Conteo (Se recontó y cuadró)
  - 🔍 Prenda Refundida / Encontrada
  - 🏷️ Trocada de Talla o Color
  - 📝 Otro Motivo
- Agrega observaciones detalladas (ej. *"Se encontró 1 unidad en el mueble de rebajas"*).

### 6. Copiar Formato para Correo y Exportar a Excel
- **Botón "Para Correo"**: Genera una tabla limpia y profesional con colores institucionales. Con un solo clic la copias al portapapeles y la pegas con `Ctrl + V` directamente en Outlook o Gmail.
- **Botón "Exportar Excel"**: Descarga un archivo `.xlsx` actualizado con todas las columnas originales más el estado de validación, motivos y notas.

---

## 📂 Archivos de Muestra Incluidos
En la carpeta `sample_data/` encontrarás dos archivos de prueba con más de 200 referencias reales de Seven Seven:
- `sample_data/inventario_lunes_muestra.xlsx`
- `sample_data/inventario_miercoles_muestra.xlsx`

Puedes arrastrar cualquiera de ellos en el botón **"Subir Excel"** para probar la aplicación de inmediato.
