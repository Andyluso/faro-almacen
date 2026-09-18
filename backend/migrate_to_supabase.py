#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
FARO - Script de Migración Automática de SQLite a Supabase
=============================================================================
Este script toma todos tus inventarios, prendas e historial guardados en tu
SQLite local (backend/inventario.db) y los sincroniza en la nube con Supabase.

Uso:
  python backend/migrate_to_supabase.py
=============================================================================
"""

import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Asegurar compatibilidad de consola en Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "inventario.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

def get_supabase_client():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    
    if not url or not key or "tu-proyecto" in url:
        print("\n❌ Error: Faltan las credenciales de Supabase.")
        print("Asegúrate de definir SUPABASE_URL y SUPABASE_KEY en tu archivo .env o en variables de entorno.")
        print("Ejemplo en .env:")
        print("SUPABASE_URL=https://xyzcompany.supabase.co")
        print("SUPABASE_KEY=eyJhbGciOi...")
        return None, None
        
    try:
        from supabase import create_client
        client = create_client(url, key)
        return client, url
    except Exception as e:
        print(f"\n❌ Error al inicializar cliente de Supabase: {e}")
        return None, None

def run_migration():
    print("=" * 70)
    print("🧭 FARO - Migración a Supabase (PostgreSQL en la Nube)")
    print("=" * 70)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos local no encontrada en: {DB_PATH}")
        return
        
    client, url = get_supabase_client()
    if not client:
        return

    bucket_name = os.environ.get("SUPABASE_STORAGE_BUCKET", "garment-photos").strip()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # 1. Migrar Auditorías (audits)
    # -------------------------------------------------------------------------
    print("\n📦 1. Migrando registros de auditorías...")
    cursor.execute("SELECT * FROM audits ORDER BY id ASC")
    audits = [dict(row) for row in cursor.fetchall()]
    print(f"   Encontradas {len(audits)} auditorías locales.")
    
    for a in audits:
        try:
            # Upsert en Supabase por ID
            data = {
                "id": a["id"],
                "name": a["name"],
                "filename": a["filename"],
                "audit_date": a["audit_date"] or a["uploaded_at"][:10],
                "uploaded_at": a["uploaded_at"],
                "total_items": a["total_items"] or 0,
                "total_faltantes": a["total_faltantes"] or 0,
                "total_sobrantes": a["total_sobrantes"] or 0,
                "total_validados": a["total_validados"] or 0
            }
            client.table("audits").upsert(data).execute()
        except Exception as e:
            print(f"   ⚠️ Error migrando auditoría #{a.get('id')}: {e}")

    print("   ✅ Auditorías migradas con éxito.")

    # -------------------------------------------------------------------------
    # 2. Migrar Prendas de Inventario (audit_items)
    # -------------------------------------------------------------------------
    print("\n👕 2. Migrando prendas de inventario (audit_items)...")
    cursor.execute("SELECT * FROM audit_items ORDER BY id ASC")
    items = [dict(row) for row in cursor.fetchall()]
    print(f"   Encontradas {len(items)} prendas locales.")
    
    batch_size = 150
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        payload = []
        for item in batch:
            payload.append({
                "id": item["id"],
                "audit_id": item["audit_id"],
                "reference": item["reference"],
                "base_reference": item["base_reference"],
                "name": item["name"],
                "size": item["size"] or "-",
                "color": item["color"] or "-",
                "barcode": item["barcode"] or "",
                "gender": item["gender"] or "",
                "garment_code": item["garment_code"] or "",
                "garment_type": item["garment_type"] or "",
                "store_count": item["store_count"] or 0,
                "warehouse_count": item["warehouse_count"] or 0,
                "theoretical_count": item["theoretical_count"] or 0,
                "difference": item["difference"] or 0,
                "category": item["category"] or "General",
                "status": item["status"] or "pendiente",
                "validation_verdict": item["validation_verdict"] or "",
                "validation_notes": item["validation_notes"] or "",
                "validated_at": item["validated_at"]
            })
        try:
            client.table("audit_items").upsert(payload).execute()
            print(f"   -> Migradas prendas {i + 1} a {min(i + batch_size, len(items))}...")
        except Exception as e:
            print(f"   ⚠️ Error migrando lote {i}: {e}")

    print("   ✅ Prendas migradas con éxito.")

    # -------------------------------------------------------------------------
    # 3. Migrar Catálogo Universal de Fotos y Storage
    # -------------------------------------------------------------------------
    print("\n📸 3. Migrando catálogo universal de fotos...")
    cursor.execute("SELECT * FROM catalog_photos")
    photos = [dict(row) for row in cursor.fetchall()]
    print(f"   Encontradas {len(photos)} fotos en catálogo.")

    for p in photos:
        ref = p["reference"]
        local_url = p["photo_url"]
        cloud_url = local_url

        # Si es una foto local (/uploads/xxx.jpg), subirla al Storage de Supabase
        if local_url and local_url.startswith("/uploads/"):
            filename = os.path.basename(local_url)
            local_file_path = os.path.join(UPLOADS_DIR, filename)

            if os.path.exists(local_file_path):
                try:
                    with open(local_file_path, "rb") as f:
                        file_bytes = f.read()
                        client.storage.from_(bucket_name).upload(
                            path=filename,
                            file=file_bytes,
                            file_options={"upsert": "true"}
                        )
                    # Obtener URL pública
                    cloud_url = client.storage.from_(bucket_name).get_public_url(filename)
                    print(f"   -> Subida foto al Storage: {filename}")
                except Exception as upload_err:
                    print(f"   ⚠️ No se pudo subir foto {filename} a Supabase Storage: {upload_err}")

        # Guardar en tabla catalog_photos de Supabase
        try:
            client.table("catalog_photos").upsert({
                "reference": ref,
                "photo_url": cloud_url,
                "updated_at": p["updated_at"] or datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"   ⚠️ Error migrando foto {ref}: {e}")

    print("   ✅ Catálogo de fotos sincronizado con éxito.")

    conn.close()
    print("\n" + "=" * 70)
    print("🎉 ¡MIGRACIÓN A SUPABASE COMPLETADA EXITOSAMENTE!")
    print(f"   Proyecto Supabase: {url}")
    print("=" * 70)

if __name__ == "__main__":
    run_migration()
