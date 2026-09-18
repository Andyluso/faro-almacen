import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from backend.excel_parser import decode_seven_seven_reference, SEVEN_SEVEN_GARMENT_TYPES
except ImportError:
    from excel_parser import decode_seven_seven_reference, SEVEN_SEVEN_GARMENT_TYPES

try:
    from backend.cloud_adapter import (
        is_supabase_enabled, cloud_create_audit,
        cloud_update_item_validation, cloud_delete_audit,
        cloud_save_catalog_photo, cloud_delete_catalog_photo,
        cloud_upload_photo, get_client, get_storage_bucket
    )
except ImportError:
    try:
        from cloud_adapter import (
            is_supabase_enabled, cloud_create_audit,
            cloud_update_item_validation, cloud_delete_audit,
            cloud_save_catalog_photo, cloud_delete_catalog_photo,
            cloud_upload_photo, get_client, get_storage_bucket
        )
    except ImportError:
        is_supabase_enabled = lambda: False
        cloud_create_audit = None
        cloud_update_item_validation = None
        cloud_delete_audit = None
        cloud_save_catalog_photo = None
        cloud_delete_catalog_photo = None
        cloud_upload_photo = None

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "inventario.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def extract_base_reference(reference: str, size: str = "") -> str:
    """
    Extrae el código base o de modelo de una prenda.
    Ejemplo: '77-BUZ-303-XL' con talla 'XL' -> '77-BUZ-303'
    Esto permite que la foto sea universal para todas las tallas de la misma referencia.
    """
    if not reference:
        return ""
    ref = str(reference).strip()

    # Si la referencia es un código numérico de 11 dígitos (o > 8 dígitos), recortar a los 8 primeros números
    digits_only = re.sub(r'\D', '', ref)
    if len(digits_only) >= 11:
        return digits_only[:8]
    elif len(ref) > 8 and ref.isdigit():
        if len(ref) - 3 >= 8:
            return ref[:-3]
        return ref[:8]

    # Si la referencia termina en -TALLA, /TALLA, _TALLA o ' TALLA'
    if size and str(size).strip() not in ["-", ""]:
        s = str(size).strip()
        pattern = rf'[-_/ ]+{re.escape(s)}$'
        cleaned = re.sub(pattern, '', ref, flags=re.IGNORECASE).strip()
        if cleaned:
            return cleaned

    # Patrón general para sufijos comunes de tallas (XS, S, M, L, XL, XXL, 28, 30, etc.)
    cleaned = re.sub(r'[-_/ ]+(XS|S|M|L|XL|XXL|XXXL|28|30|32|34|36|38|40|42|UN|UNICA)$', '', ref, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else ref

def init_db():
    """Inicializa la base de datos con las tablas requeridas."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de auditorías / lecturas de inventario (Lunes y Miércoles)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        filename TEXT NOT NULL,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_items INTEGER DEFAULT 0,
        total_faltantes INTEGER DEFAULT 0,
        total_sobrantes INTEGER DEFAULT 0,
        total_validados INTEGER DEFAULT 0
    )
    """)

    # Tabla de items leídos en cada auditoría
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id INTEGER NOT NULL,
        reference TEXT NOT NULL,
        base_reference TEXT,
        name TEXT NOT NULL,
        size TEXT,
        color TEXT,
        barcode TEXT,
        store_count INTEGER DEFAULT 0,
        warehouse_count INTEGER DEFAULT 0,
        theoretical_count INTEGER DEFAULT 0,
        difference INTEGER DEFAULT 0,
        category TEXT DEFAULT 'General',
        status TEXT DEFAULT 'pendiente', -- 'pendiente', 'validada'
        validation_verdict TEXT DEFAULT '',
        validation_notes TEXT DEFAULT '',
        validated_at DATETIME,
        FOREIGN KEY (audit_id) REFERENCES audits (id) ON DELETE CASCADE
    )
    """)

    # Migración de columna base_reference si no existe
    cursor.execute("PRAGMA table_info(audit_items)")
    cols = [col[1] for col in cursor.fetchall()]
    if "base_reference" not in cols:
        cursor.execute("ALTER TABLE audit_items ADD COLUMN base_reference TEXT")

    # Migración de columnas oficiales Seven Seven (gender, garment_code, garment_type)
    if "gender" not in cols:
        cursor.execute("ALTER TABLE audit_items ADD COLUMN gender TEXT DEFAULT ''")
    if "garment_code" not in cols:
        cursor.execute("ALTER TABLE audit_items ADD COLUMN garment_code TEXT DEFAULT ''")
    if "garment_type" not in cols:
        cursor.execute("ALTER TABLE audit_items ADD COLUMN garment_type TEXT DEFAULT ''")

    # Poblar base_reference en items existentes
    cursor.execute("SELECT id, reference, size FROM audit_items WHERE base_reference IS NULL OR base_reference = ''")
    existing_items = cursor.fetchall()
    for row in existing_items:
        b_ref = extract_base_reference(row["reference"], row["size"])
        cursor.execute("UPDATE audit_items SET base_reference = ? WHERE id = ?", (b_ref, row["id"]))

    # Poblar gender, garment_code y garment_type en items existentes
    cursor.execute("SELECT id, reference, name, category FROM audit_items WHERE gender IS NULL OR gender = '' OR garment_type IS NULL OR garment_type = ''")
    pending_decode = cursor.fetchall()
    for row in pending_decode:
        g, c, t = decode_seven_seven_reference(row["reference"], row["name"])
        final_type = t if t else (row["category"] or "General")
        cursor.execute("UPDATE audit_items SET gender = ?, garment_code = ?, garment_type = ? WHERE id = ?", (g, c, final_type, row["id"]))

    # Migración de columna audit_date en audits si no existe
    cursor.execute("PRAGMA table_info(audits)")
    audit_cols = [col[1] for col in cursor.fetchall()]
    if "audit_date" not in audit_cols:
        cursor.execute("ALTER TABLE audits ADD COLUMN audit_date TEXT")
        cursor.execute("UPDATE audits SET audit_date = substr(uploaded_at, 1, 10) WHERE audit_date IS NULL OR audit_date = ''")

    # Normalizar referencias de 11 dígitos a 8 dígitos en items existentes si existieran
    cursor.execute("SELECT id, reference, size FROM audit_items WHERE length(reference) >= 11 AND reference GLOB '[0-9]*'")
    long_ref_items = cursor.fetchall()
    for row in long_ref_items:
        r = row["reference"]
        digits = re.sub(r'\D', '', r)
        if len(digits) >= 11:
            new_ref = digits[:8]
            b_ref = extract_base_reference(new_ref, row["size"])
            cursor.execute("UPDATE audit_items SET reference = ?, base_reference = ? WHERE id = ?", (new_ref, b_ref, row["id"]))

    # Catálogo maestro de fotos (vinculado universalmente por referencia o modelo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalog_photos (
        reference TEXT PRIMARY KEY,
        photo_url TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Sincronización automática de fotos existentes para que sean universales por modelo y nombre
    cursor.execute("SELECT reference, photo_url FROM catalog_photos")
    existing_photos = cursor.fetchall()
    for p in existing_photos:
        ref = p["reference"]
        p_url = p["photo_url"]
        b_ref = extract_base_reference(ref)
        if b_ref and b_ref != ref:
            cursor.execute("""
            INSERT INTO catalog_photos (reference, photo_url, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(reference) DO UPDATE SET photo_url = excluded.photo_url
            """, (b_ref, p_url))
        
        cursor.execute("SELECT name FROM audit_items WHERE reference = ? OR base_reference = ? LIMIT 1", (ref, b_ref))
        name_row = cursor.fetchone()
        if name_row and name_row["name"]:
            cursor.execute("""
            INSERT INTO catalog_photos (reference, photo_url, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(reference) DO UPDATE SET photo_url = excluded.photo_url
            """, (name_row["name"].strip(), p_url))

    # Índices para consultas rápidas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_audit ON audit_items(audit_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_ref ON audit_items(reference)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_baseref ON audit_items(base_reference)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_barcode ON audit_items(barcode)")

    conn.commit()
    conn.close()

def create_audit(name: str, filename: str, items: List[Dict[str, Any]], audit_date: Optional[str] = None) -> int:
    """Crea una auditoría y guarda todos sus items con su referencia base calculada."""
    conn = get_connection()
    cursor = conn.cursor()

    total_faltantes = sum(1 for item in items if (item.get("difference") or 0) < 0)
    total_sobrantes = sum(1 for item in items if (item.get("difference") or 0) > 0)

    if not audit_date or not str(audit_date).strip():
        audit_date = datetime.now().strftime("%Y-%m-%d")
    else:
        audit_date = str(audit_date).strip()[:10]

    cursor.execute("""
    INSERT INTO audits (name, filename, audit_date, total_items, total_faltantes, total_sobrantes, total_validados)
    VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (name, filename, audit_date, len(items), total_faltantes, total_sobrantes))
    
    audit_id = cursor.lastrowid

    items_to_sync = []
    for item in items:
        ref = str(item.get("reference", "")).strip()
        digits_only = re.sub(r'\D', '', ref)
        if len(digits_only) >= 11:
            ref = digits_only[:8]
        elif len(ref) > 8 and ref.isdigit():
            ref = ref[:-3] if len(ref) - 3 >= 8 else ref[:8]

        size = str(item.get("size", "")).strip()
        base_ref = extract_base_reference(ref, size)
        obs_notes = str(item.get("observation") or "").strip()

        gender = item.get("gender")
        garment_code = item.get("garment_code")
        garment_type = item.get("garment_type")
        if not gender or not garment_type:
            g, c, t = decode_seven_seven_reference(ref, item.get("name", ""))
            gender = gender or g
            garment_code = garment_code or c
            garment_type = garment_type or t

        category = str(item.get("category") or garment_type or "General").strip()

        cursor.execute("""
        INSERT INTO audit_items (
            audit_id, reference, base_reference, name, size, color, barcode,
            store_count, warehouse_count, theoretical_count, difference, category,
            gender, garment_code, garment_type, validation_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            ref,
            base_ref,
            str(item.get("name", "")).strip(),
            size,
            str(item.get("color", "")).strip(),
            str(item.get("barcode", "")).strip(),
            int(item.get("store_count") or 0),
            int(item.get("warehouse_count") or 0),
            int(item.get("theoretical_count") or 0),
            int(item.get("difference") or 0),
            category,
            gender,
            garment_code,
            garment_type if garment_type else category,
            obs_notes
        ))
        item_id = cursor.lastrowid
        item_sync = dict(item)
        item_sync["id"] = item_id
        item_sync["reference"] = ref
        item_sync["base_reference"] = base_ref
        item_sync["category"] = category
        item_sync["gender"] = gender
        item_sync["garment_code"] = garment_code
        item_sync["garment_type"] = garment_type if garment_type else category
        item_sync["observation"] = obs_notes
        items_to_sync.append(item_sync)

    conn.commit()
    conn.close()

    # Sincronizar automáticamente con Supabase Cloud
    if is_supabase_enabled() and cloud_create_audit:
        try:
            cloud_create_audit(name, filename, items_to_sync, audit_date, audit_id=audit_id)
        except Exception as e:
            print(f"[Supabase Sync] Error al sincronizar auditoría #{audit_id}: {e}")

    return audit_id

def list_audits(search: Optional[str] = None, date: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista todas las auditorías con sus métricas resumidas y soporte de filtros por fecha o búsqueda."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT 
        a.id, a.name, a.filename, a.uploaded_at,
        COALESCE(a.audit_date, substr(a.uploaded_at, 1, 10)) as audit_date,
        a.total_items, a.total_faltantes, a.total_sobrantes,
        COUNT(CASE WHEN i.status = 'validada' THEN 1 END) as total_validados
    FROM audits a
    LEFT JOIN audit_items i ON a.id = i.audit_id
    WHERE 1=1
    """
    params = []

    if date and str(date).strip():
        d = str(date).strip()
        query += " AND (a.audit_date = ? OR substr(a.uploaded_at, 1, 10) = ?)"
        params.extend([d, d])

    if date_from and str(date_from).strip():
        df = str(date_from).strip()
        query += " AND (COALESCE(a.audit_date, substr(a.uploaded_at, 1, 10)) >= ?)"
        params.append(df)

    if date_to and str(date_to).strip():
        dt = str(date_to).strip()
        query += " AND (COALESCE(a.audit_date, substr(a.uploaded_at, 1, 10)) <= ?)"
        params.append(dt)

    if search and str(search).strip():
        s = f"%{str(search).strip()}%"
        query += " AND (a.name LIKE ? OR a.filename LIKE ? OR a.audit_date LIKE ? OR a.uploaded_at LIKE ?)"
        params.extend([s, s, s, s])

    query += """
    GROUP BY a.id
    ORDER BY COALESCE(a.audit_date, substr(a.uploaded_at, 1, 10)) DESC, a.id DESC
    """

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_audit(audit_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una auditoría específica con sus métricas."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM audits WHERE id = ?", (audit_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    audit = dict(row)

    # Conteo actualizado de validados
    cursor.execute("SELECT COUNT(*) FROM audit_items WHERE audit_id = ? AND status = 'validada'", (audit_id,))
    audit["total_validados"] = cursor.fetchone()[0]

    conn.close()
    return audit

def get_audit_size_summary(audit_id: int) -> List[Dict[str, Any]]:
    """Obtiene el consolidado de faltantes y sobrantes por cada talla en la auditoría."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        size,
        COUNT(*) as total_refs,
        SUM(CASE WHEN difference < 0 THEN ABS(difference) ELSE 0 END) as faltante_units,
        SUM(CASE WHEN difference < 0 THEN 1 ELSE 0 END) as faltante_items,
        SUM(CASE WHEN difference > 0 THEN difference ELSE 0 END) as sobrante_units,
        SUM(CASE WHEN difference > 0 THEN 1 ELSE 0 END) as sobrante_items,
        SUM(difference) as net_difference
    FROM audit_items
    WHERE audit_id = ?
    GROUP BY size
    ORDER BY 
        CASE UPPER(TRIM(size))
            WHEN 'XS' THEN 1
            WHEN 'S' THEN 2
            WHEN 'M' THEN 3
            WHEN 'L' THEN 4
            WHEN 'XL' THEN 5
            WHEN 'XXL' THEN 6
            WHEN '28' THEN 7
            WHEN '30' THEN 8
            WHEN '32' THEN 9
            WHEN '34' THEN 10
            WHEN '36' THEN 11
            WHEN 'UN' THEN 12
            WHEN 'UNICA' THEN 13
            ELSE 14
        END, size
    """, (audit_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_audit_items_with_history(audit_id: int) -> List[Dict[str, Any]]:
    """
    Obtiene todos los items de una auditoría, cruzándolos con el catálogo de fotos,
    calculando las reincidencias históricas y agrupando las demás tallas del mismo modelo.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        i.*,
        COALESCE(p_exact.photo_url, p_base.photo_url, p_name.photo_url) as photo_url
    FROM audit_items i
    LEFT JOIN catalog_photos p_exact ON i.reference = p_exact.reference
    LEFT JOIN catalog_photos p_base ON (i.base_reference IS NOT NULL AND i.base_reference != '' AND i.base_reference = p_base.reference)
    LEFT JOIN catalog_photos p_name ON (i.name IS NOT NULL AND i.name != '' AND i.name = p_name.reference)
    WHERE i.audit_id = ?
    ORDER BY 
        CASE WHEN i.difference < 0 THEN 0 ELSE 1 END,
        ABS(i.difference) DESC
    """, (audit_id,))

    items = [dict(row) for row in cursor.fetchall()]

    # Para cada item, calculamos reincidencia histórica e identificamos tallas hermanas con sus fotos universales
    for item in items:
        ref = item["reference"]
        base_ref = item.get("base_reference") or extract_base_reference(ref, item.get("size", ""))
        item["base_reference"] = base_ref
        item_id = item["id"]
        item_name = item["name"]

        # 1. Historial en auditorías pasadas
        cursor.execute("""
        SELECT 
            a.id as audit_id,
            a.name as audit_name,
            a.filename as audit_filename,
            COALESCE(a.audit_date, substr(a.uploaded_at, 1, 10)) as audit_date,
            a.uploaded_at,
            i.difference,
            i.size,
            i.store_count,
            i.warehouse_count,
            i.theoretical_count,
            i.validation_verdict,
            i.validation_notes
        FROM audit_items i
        JOIN audits a ON i.audit_id = a.id
        WHERE (i.reference = ? OR (i.base_reference IS NOT NULL AND i.base_reference = ?) OR (i.name = ? AND length(i.name) > 3))
          AND a.id != ?
        ORDER BY a.uploaded_at DESC
        LIMIT 20
        """, (ref, base_ref, item_name, audit_id))

        history = [dict(r) for r in cursor.fetchall()]
        item["history"] = history
        item["unique_audits_count"] = len(set(r["audit_id"] for r in history))
        item["recurrence_count"] = len(history)
        item["is_recurrent"] = len(history) > 0

        # 2. Tallas hermanas de este mismo modelo en ESTA auditoría (unificación de diferencias)
        cursor.execute("""
        SELECT 
            id, reference, base_reference, name, size, color, barcode,
            store_count, warehouse_count, theoretical_count, difference, status, validation_verdict, validation_notes,
            gender, garment_code, garment_type
        FROM audit_items
        WHERE audit_id = ? AND (
            (base_reference IS NOT NULL AND base_reference != '' AND base_reference = ?) OR
            (name IS NOT NULL AND name != '' AND name = ?) OR
            reference = ?
        )
        ORDER BY 
            CASE UPPER(TRIM(size))
                WHEN 'XS' THEN 1 WHEN 'S' THEN 2 WHEN 'M' THEN 3
                WHEN 'L' THEN 4 WHEN 'XL' THEN 5 WHEN 'XXL' THEN 6
                WHEN '28' THEN 7 WHEN '30' THEN 8 WHEN '32' THEN 9
                WHEN '34' THEN 10 WHEN '36' THEN 11
                WHEN 'UN' THEN 12 WHEN 'UNICA' THEN 13
                ELSE 14
            END, size
        """, (audit_id, base_ref, item_name, ref))

        siblings = [dict(r) for r in cursor.fetchall()]
        for s in siblings:
            s["photo_url"] = item.get("photo_url")
            if not s.get("gender") or not s.get("garment_type"):
                sg, sc, st = decode_seven_seven_reference(s.get("reference", ""), s.get("name", ""))
                s["gender"] = s.get("gender") or sg
                s["garment_code"] = s.get("garment_code") or sc
                s["garment_type"] = s.get("garment_type") or st or s.get("category", "")
        item["sibling_sizes"] = siblings

        # Asegurar decodificación Seven Seven en el item principal
        if not item.get("gender") or not item.get("garment_type"):
            g, c, t = decode_seven_seven_reference(ref, item_name)
            item["gender"] = item.get("gender") or g
            item["garment_code"] = item.get("garment_code") or c
            item["garment_type"] = item.get("garment_type") or t or item.get("category", "")

    conn.close()
    return items

def update_item_validation(item_id: int, verdict: str, notes: str) -> bool:
    """Actualiza la validación de un item."""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE audit_items
    SET status = 'validada',
        validation_verdict = ?,
        validation_notes = ?,
        validated_at = ?
    WHERE id = ?
    """, (verdict, notes, now, item_id))

    success = cursor.rowcount > 0
    if success:
        # Actualizar contador de validados en la auditoría
        cursor.execute("""
        UPDATE audits
        SET total_validados = (
            SELECT COUNT(*) FROM audit_items WHERE audit_id = (
                SELECT audit_id FROM audit_items WHERE id = ?
            ) AND status = 'validada'
        )
        WHERE id = (SELECT audit_id FROM audit_items WHERE id = ?)
        """, (item_id, item_id))

    conn.commit()
    conn.close()

    if success and is_supabase_enabled() and cloud_update_item_validation:
        try:
            cloud_update_item_validation(item_id, "validada", verdict, notes)
        except Exception as e:
            print(f"[Supabase Sync] Error al sincronizar validación de item #{item_id}: {e}")

    return success

def save_catalog_photo(reference: str, photo_url: str, base_reference: Optional[str] = None, name: Optional[str] = None):
    """Guarda o actualiza la foto de una referencia en el catálogo permanente de forma universal."""
    conn = get_connection()
    cursor = conn.cursor()

    refs_to_save = {reference.strip()}
    if base_reference and base_reference.strip():
        refs_to_save.add(base_reference.strip())
    else:
        b_ref = extract_base_reference(reference)
        if b_ref:
            refs_to_save.add(b_ref)

    if name and name.strip():
        refs_to_save.add(name.strip())

    for r in refs_to_save:
        cursor.execute("""
        INSERT INTO catalog_photos (reference, photo_url, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(reference) DO UPDATE SET
            photo_url = excluded.photo_url,
            updated_at = CURRENT_TIMESTAMP
        """, (r, photo_url))

    conn.commit()
    conn.close()

    # Sincronizar catálogo con Supabase Cloud si está habilitado
    if is_supabase_enabled() and cloud_save_catalog_photo:
        try:
            cloud_url = photo_url
            # Si es un archivo local (/uploads/...), intentar subirlo al Storage de Supabase
            if photo_url.startswith("/uploads/") and cloud_upload_photo:
                fname = os.path.basename(photo_url)
                local_fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", fname)
                if os.path.exists(local_fpath):
                    with open(local_fpath, "rb") as f:
                        uploaded_url = cloud_upload_photo(f.read(), fname)
                        if uploaded_url:
                            cloud_url = uploaded_url

            for r in refs_to_save:
                cloud_save_catalog_photo(r, cloud_url)
        except Exception as e:
            print(f"[Supabase Sync] Error al sincronizar foto de {reference}: {e}")

def delete_catalog_photo(reference: str, base_reference: Optional[str] = None, name: Optional[str] = None) -> bool:
    """Elimina la foto de una referencia del catálogo permanente (local SQLite y Supabase Cloud)."""
    conn = get_connection()
    cursor = conn.cursor()

    refs_to_delete = {str(reference).strip()}
    if base_reference and str(base_reference).strip():
        refs_to_delete.add(str(base_reference).strip())
    else:
        b_ref = extract_base_reference(reference)
        if b_ref:
            refs_to_delete.add(b_ref)

    if name and str(name).strip():
        refs_to_delete.add(str(name).strip())

    refs_list = [r for r in refs_to_delete if r]
    if not refs_list:
        conn.close()
        return False

    placeholders = ",".join(["?"] * len(refs_list))
    cursor.execute(f"SELECT photo_url FROM catalog_photos WHERE reference IN ({placeholders})", tuple(refs_list))
    rows = cursor.fetchall()
    photo_urls = list({r["photo_url"] for r in rows if r["photo_url"]})

    cursor.execute(f"DELETE FROM catalog_photos WHERE reference IN ({placeholders})", tuple(refs_list))
    conn.commit()
    conn.close()

    # Eliminar archivos físicos locales si existen
    for purl in photo_urls:
        if purl and str(purl).startswith("/uploads/"):
            fname = os.path.basename(str(purl))
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", fname)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception as e:
                    print(f"Error borrando archivo local {local_path}: {e}")

    # Sincronizar eliminación con Supabase Cloud si está habilitado
    if is_supabase_enabled() and cloud_delete_catalog_photo:
        try:
            cloud_delete_catalog_photo(refs_list, photo_urls)
        except Exception as e:
            print(f"[Supabase Sync] Error al eliminar foto de catálogo en Supabase: {e}")

    return True

def delete_audit(audit_id: int) -> bool:
    """Elimina una auditoría y sus items (las fotos del catálogo se conservan)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_items WHERE audit_id = ?", (audit_id,))
    cursor.execute("DELETE FROM audits WHERE id = ?", (audit_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    # Eliminar archivo físico de Excel original si existe
    try:
        excels_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "excels")
        if os.path.exists(excels_dir):
            for fname in os.listdir(excels_dir):
                if fname.startswith(f"audit_{audit_id}_"):
                    try:
                        os.remove(os.path.join(excels_dir, fname))
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error limpiando archivo físico de auditoría {audit_id}: {e}")

    # Sincronizar eliminación con Supabase Cloud si está habilitado
    if success and is_supabase_enabled() and cloud_delete_audit:
        try:
            cloud_delete_audit(audit_id)
        except Exception as e:
            print(f"[Supabase Sync] Error al eliminar auditoría #{audit_id} en Supabase: {e}")

    return success

def get_recurring_summary() -> List[Dict[str, Any]]:
    """Obtiene un resumen de las referencias que más se han repetido con diferencias."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        i.reference,
        i.name,
        i.category,
        p.photo_url,
        COUNT(DISTINCT i.audit_id) as appearances,
        SUM(CASE WHEN i.difference < 0 THEN 1 ELSE 0 END) as faltante_times,
        SUM(CASE WHEN i.difference > 0 THEN 1 ELSE 0 END) as sobrante_times,
        AVG(i.difference) as avg_diff
    FROM audit_items i
    LEFT JOIN catalog_photos p ON i.reference = p.reference
    GROUP BY i.reference
    HAVING appearances > 1
    ORDER BY appearances DESC
    LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_master_catalog(search: Optional[str] = None, gender: Optional[str] = None, garment_type: Optional[str] = None, has_photo: Optional[bool] = None) -> List[Dict[str, Any]]:
    """
    Retorna el catálogo maestro de referencias consolidado (sin diferencias de inventario).
    Agrupa por modelo/referencia base y consolida todas sus tallas, colores, códigos EAN y fotos.
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT 
        COALESCE(i.base_reference, i.reference) as master_ref,
        i.reference,
        i.name,
        COALESCE(i.category, 'General') as category,
        COALESCE(i.gender, '') as gender,
        COALESCE(i.garment_code, '') as garment_code,
        COALESCE(i.garment_type, i.category, 'General') as garment_type,
        COALESCE(p_exact.photo_url, p_base.photo_url, p_name.photo_url) as photo_url,
        GROUP_CONCAT(DISTINCT i.size) as sizes_raw,
        GROUP_CONCAT(DISTINCT i.color) as colors_raw,
        GROUP_CONCAT(DISTINCT i.barcode) as barcodes_raw,
        COUNT(DISTINCT i.audit_id) as audit_appearances,
        MAX(COALESCE(a.audit_date, substr(a.uploaded_at, 1, 10))) as last_seen_date
    FROM audit_items i
    LEFT JOIN audits a ON i.audit_id = a.id
    LEFT JOIN catalog_photos p_exact ON i.reference = p_exact.reference
    LEFT JOIN catalog_photos p_base ON (i.base_reference IS NOT NULL AND i.base_reference != '' AND i.base_reference = p_base.reference)
    LEFT JOIN catalog_photos p_name ON (i.name IS NOT NULL AND i.name != '' AND i.name = p_name.reference)
    WHERE 1=1
    """
    params = []

    if search and search.strip():
        s = f"%{search.strip()}%"
        query += """ AND (
            i.reference LIKE ? OR 
            i.base_reference LIKE ? OR 
            i.name LIKE ? OR 
            i.barcode LIKE ? OR 
            i.color LIKE ? OR 
            i.category LIKE ? OR
            i.garment_type LIKE ?
        )"""
        params.extend([s, s, s, s, s, s, s])

    if gender and gender.strip() and gender.lower() != 'all':
        query += " AND i.gender = ?"
        params.append(gender.strip())

    if garment_type and garment_type.strip() and garment_type.lower() != 'all':
        query += " AND (i.garment_type = ? OR i.category = ?)"
        params.extend([garment_type.strip(), garment_type.strip()])

    query += " GROUP BY COALESCE(i.base_reference, i.reference), i.name"

    if has_photo is True:
        query += " HAVING photo_url IS NOT NULL AND photo_url != ''"
    elif has_photo is False:
        query += " HAVING photo_url IS NULL OR photo_url = ''"

    query += " ORDER BY i.name ASC, i.reference ASC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    size_order = {
        'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6,
        '28': 7, '30': 8, '32': 9, '34': 10, '36': 11,
        'UN': 12, 'UNICA': 13
    }

    result = []
    for row in rows:
        item = dict(row)
        # Parsear tallas y ordenarlas lógicamente
        raw_sizes = [s.strip() for s in (item.get("sizes_raw") or "").split(",") if s.strip()]
        # Quitar duplicados preservando orden lógico
        unique_sizes = list(dict.fromkeys(raw_sizes))
        sorted_sizes = sorted(unique_sizes, key=lambda x: size_order.get(x.upper(), 99))
        item["sizes"] = sorted_sizes

        # Parsear colores
        raw_colors = [c.strip() for c in (item.get("colors_raw") or "").split(",") if c.strip()]
        item["colors"] = list(dict.fromkeys(raw_colors))

        # Parsear códigos de barras
        raw_barcodes = [b.strip() for b in (item.get("barcodes_raw") or "").split(",") if b.strip()]
        unique_barcodes = list(dict.fromkeys(raw_barcodes))
        item["barcodes"] = unique_barcodes
        item["primary_barcode"] = unique_barcodes[0] if unique_barcodes else ""

        result.append(item)

    return result

def get_catalog_stats() -> Dict[str, Any]:
    """Retorna estadísticas rápidas del catálogo maestro y la lista de tipos de prenda disponibles."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total referencias únicas
    cursor.execute("SELECT COUNT(DISTINCT COALESCE(base_reference, reference)) FROM audit_items")
    total_refs = cursor.fetchone()[0]

    # Tipos de prendas existentes
    cursor.execute("""
    SELECT DISTINCT COALESCE(garment_type, category) 
    FROM audit_items 
    WHERE COALESCE(garment_type, category) IS NOT NULL AND COALESCE(garment_type, category) != ''
    ORDER BY 1
    """)
    garment_types = [r[0] for r in cursor.fetchall() if r[0]]

    # Total con fotos
    cursor.execute("SELECT COUNT(DISTINCT reference) FROM catalog_photos WHERE photo_url IS NOT NULL AND photo_url != ''")
    total_with_photos = cursor.fetchone()[0]

    # Conteo por género
    cursor.execute("SELECT COUNT(DISTINCT COALESCE(base_reference, reference)) FROM audit_items WHERE gender = 'Dama'")
    dama_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT COALESCE(base_reference, reference)) FROM audit_items WHERE gender = 'Caballero'")
    caballero_count = cursor.fetchone()[0]

    conn.close()
    return {
        "total_models": total_refs,
        "total_references": total_refs,
        "total_with_photos": total_with_photos,
        "dama_count": dama_count,
        "caballero_count": caballero_count,
        "garment_types": garment_types
    }

