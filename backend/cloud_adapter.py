#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
FARO - Adaptador Cloud para Supabase (PostgreSQL + Supabase Storage)
=============================================================================
Permite consultar y guardar auditorías, prendas y fotos en la nube.
Si no está configurado o si no hay conexión, FARO recurre a SQLite local.
=============================================================================
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_client():
    global _client
    if _client is not None:
        return _client
        
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    
    if not url or not key or "tu-proyecto" in url:
        return None
        
    try:
        from supabase import create_client
        _client = create_client(url, key)
        return _client
    except Exception as e:
        print(f"[Supabase] Error al crear cliente: {e}")
        return None

def is_supabase_enabled() -> bool:
    """Verifica si las credenciales de Supabase están configuradas en el entorno."""
    return get_client() is not None

def get_storage_bucket() -> str:
    return os.environ.get("SUPABASE_STORAGE_BUCKET", "garment-photos").strip()

# -----------------------------------------------------------------------------
# OPERACIONES DE AUDITORÍAS EN LA NUBE
# -----------------------------------------------------------------------------
def cloud_list_audits(search: Optional[str] = None, date: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_client()
    if not client:
        return []
        
    query = client.table("audits").select("*").order("audit_date", desc=True).order("id", desc=True)
    if date and str(date).strip():
        query = query.eq("audit_date", str(date).strip()[:10])
    if search and str(search).strip():
        query = query.ilike("name", f"%{str(search).strip()}%")
        
    res = query.execute()
    audits = res.data or []
    
    # Calcular total_validados para cada auditoría
    for a in audits:
        aid = a["id"]
        val_res = client.table("audit_items").select("id", count="exact").eq("audit_id", aid).eq("status", "validada").execute()
        a["total_validados"] = val_res.count if hasattr(val_res, "count") and val_res.count is not None else 0
        
    return audits

def cloud_get_audit(audit_id: int) -> Optional[Dict[str, Any]]:
    client = get_client()
    if not client:
        return None
        
    res = client.table("audits").select("*").eq("id", audit_id).limit(1).execute()
    if not res.data:
        return None
        
    audit = res.data[0]
    val_res = client.table("audit_items").select("id", count="exact").eq("audit_id", audit_id).eq("status", "validada").execute()
    audit["total_validados"] = val_res.count if hasattr(val_res, "count") and val_res.count is not None else 0
    return audit

def cloud_upload_photo(file_bytes: bytes, filename: str) -> Optional[str]:
    """Sube un archivo de imagen al bucket de Supabase Storage y retorna su URL pública."""
    client = get_client()
    if not client:
        return None
    bucket_name = get_storage_bucket()
    try:
        client.storage.from_(bucket_name).upload(
            path=filename,
            file=file_bytes,
            file_options={"upsert": "true"}
        )
        return client.storage.from_(bucket_name).get_public_url(filename)
    except Exception as e:
        print(f"[Supabase Storage] Error subiendo imagen {filename}: {e}")
        return None

def cloud_create_audit(name: str, filename: str, items: List[Dict[str, Any]], audit_date: Optional[str] = None, audit_id: Optional[int] = None) -> int:
    client = get_client()
    if not client:
        raise RuntimeError("Supabase no está disponible")
        
    total_faltantes = sum(1 for item in items if (item.get("difference") or 0) < 0)
    total_sobrantes = sum(1 for item in items if (item.get("difference") or 0) > 0)
    
    a_date = audit_date[:10] if audit_date and str(audit_date).strip() else datetime.now().strftime("%Y-%m-%d")
    
    audit_data = {
        "name": name,
        "filename": filename,
        "audit_date": a_date,
        "total_items": len(items),
        "total_faltantes": total_faltantes,
        "total_sobrantes": total_sobrantes,
        "total_validados": 0
    }
    if audit_id is not None:
        audit_data["id"] = audit_id
    
    res = client.table("audits").upsert(audit_data).execute()
    if not res.data:
        raise RuntimeError("No se pudo insertar la auditoría en Supabase")
        
    final_audit_id = res.data[0]["id"]
    
    # Insertar items en lotes
    payload = []
    for item in items:
        ref = str(item.get("reference", "")).strip()
        digits = re.sub(r'\D', '', ref)
        if len(digits) >= 11:
            ref = digits[:8]
        elif len(ref) > 8 and ref.isdigit():
            ref = ref[:-3] if len(ref) - 3 >= 8 else ref[:8]
            
        row = {
            "audit_id": final_audit_id,
            "reference": ref,
            "base_reference": item.get("base_reference") or ref,
            "name": str(item.get("name", "")).strip(),
            "size": str(item.get("size", "-")).strip(),
            "color": str(item.get("color", "-")).strip(),
            "barcode": str(item.get("barcode", "")).strip(),
            "gender": item.get("gender") or "",
            "garment_code": item.get("garment_code") or "",
            "garment_type": item.get("garment_type") or item.get("category") or "General",
            "store_count": int(item.get("store_count") or 0),
            "warehouse_count": int(item.get("warehouse_count") or 0),
            "theoretical_count": int(item.get("theoretical_count") or 0),
            "difference": int(item.get("difference") or 0),
            "category": item.get("category") or "General",
            "status": item.get("status") or "pendiente",
            "validation_notes": str(item.get("validation_notes") or item.get("observation") or "").strip()
        }
        if "id" in item and item["id"]:
            row["id"] = item["id"]
        payload.append(row)
        
    batch_size = 150
    for i in range(0, len(payload), batch_size):
        client.table("audit_items").upsert(payload[i:i + batch_size]).execute()
        
    return final_audit_id

def cloud_update_item_validation(item_id: int, status: str, verdict: str, notes: str) -> bool:
    client = get_client()
    if not client:
        return False
        
    update_data = {
        "status": status,
        "validation_verdict": verdict,
        "validation_notes": notes,
        "validated_at": datetime.now().isoformat() if status == "validada" else None
    }
    res = client.table("audit_items").update(update_data).eq("id", item_id).execute()
    if res.data and len(res.data) > 0:
        audit_id = res.data[0].get("audit_id")
        if audit_id:
            try:
                val_res = client.table("audit_items").select("id", count="exact").eq("audit_id", audit_id).eq("status", "validada").execute()
                total_val = val_res.count if hasattr(val_res, "count") and val_res.count is not None else 0
                client.table("audits").update({"total_validados": total_val}).eq("id", audit_id).execute()
            except Exception as e:
                print(f"[Supabase] Error actualizando total_validados en auditoría {audit_id}: {e}")
    return bool(res.data)

def cloud_delete_audit(audit_id: int) -> bool:
    client = get_client()
    if not client:
        return False
    try:
        client.table("audit_items").delete().eq("audit_id", audit_id).execute()
        res = client.table("audits").delete().eq("id", audit_id).execute()
        return bool(res.data)
    except Exception as e:
        print(f"[Supabase] Error eliminando auditoría {audit_id}: {e}")
        return False

def cloud_save_catalog_photo(reference: str, photo_url: str) -> bool:
    client = get_client()
    if not client:
        return False
        
    data = {
        "reference": reference,
        "photo_url": photo_url,
        "updated_at": datetime.now().isoformat()
    }
    res = client.table("catalog_photos").upsert(data).execute()
    return bool(res.data)

def cloud_delete_catalog_photo(references: List[str], photo_urls: Optional[List[str]] = None) -> bool:
    """Elimina la foto del catálogo en Supabase y borra el archivo del bucket de Storage."""
    client = get_client()
    if not client:
        return False
        
    try:
        # 1. Eliminar registros de la tabla catalog_photos
        for ref in references:
            if ref and str(ref).strip():
                client.table("catalog_photos").delete().eq("reference", str(ref).strip()).execute()

        # 2. Si se pasaron URLs, extraer los nombres de archivo y eliminarlos del bucket
        if photo_urls:
            bucket_name = get_storage_bucket()
            filenames_to_remove = []
            for purl in photo_urls:
                if purl:
                    fname = os.path.basename(str(purl).split("?")[0])
                    if fname:
                        filenames_to_remove.append(fname)
            if filenames_to_remove:
                try:
                    client.storage.from_(bucket_name).remove(filenames_to_remove)
                except Exception as st_err:
                    print(f"[Supabase Storage] Error borrando archivos {filenames_to_remove}: {st_err}")
                    
        return True
    except Exception as e:
        print(f"[Supabase] Error eliminando foto de catálogo para {references}: {e}")
        return False


