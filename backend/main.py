import os
import re
import shutil
import socket
import tempfile
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

try:
    from .database import (
        init_db,
        create_audit,
        list_audits,
        get_audit,
        get_audit_items_with_history,
        get_audit_size_summary,
        update_item_validation,
        save_catalog_photo,
        delete_catalog_photo,
        delete_audit,
        get_recurring_summary,
        get_connection,
        get_master_catalog,
        get_catalog_stats,
        list_employees,
        create_employee,
        update_employee,
        delete_employee,
        get_or_create_weekly_schedule,
        save_schedule_shifts,
        list_schedules,
        list_store_tasks,
        create_store_task,
        toggle_store_task,
        delete_store_task,
        get_hub_summary
    )
    from .excel_parser import parse_excel_file
    from .excel_exporter import generate_validation_excel, generate_email_table_html, modify_original_excel
    from .cloud_adapter import is_supabase_enabled
except ImportError:
    from database import (
        init_db,
        create_audit,
        list_audits,
        get_audit,
        get_audit_items_with_history,
        get_audit_size_summary,
        update_item_validation,
        save_catalog_photo,
        delete_catalog_photo,
        delete_audit,
        get_recurring_summary,
        get_connection,
        get_master_catalog,
        get_catalog_stats,
        list_employees,
        create_employee,
        update_employee,
        delete_employee,
        get_or_create_weekly_schedule,
        save_schedule_shifts,
        list_schedules,
        list_store_tasks,
        create_store_task,
        toggle_store_task,
        delete_store_task,
        get_hub_summary
    )
    from excel_parser import parse_excel_file
    from excel_exporter import generate_validation_excel, generate_email_table_html, modify_original_excel
    try:
        from cloud_adapter import is_supabase_enabled
    except ImportError:
        is_supabase_enabled = lambda: False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

os.makedirs(UPLOADS_DIR, exist_ok=True)
EXCELS_DIR = os.path.join(UPLOADS_DIR, "excels")
os.makedirs(EXCELS_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

# Inicializar base de datos
init_db()

app = FastAPI(title="FARO - Flujo de Almacén y Reorden Operativo")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para evitar caché en navegadores y celulares (actualizaciones instantáneas)
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    # Evitar caché en html, js, css y manifest json para reflejar cambios en tiempo real
    path = request.url.path
    if path == "/" or path.endswith((".js", ".html", ".css", ".json")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    if path == "/sw.js":
        response.headers["Service-Worker-Allowed"] = "/"
    return response

# Montar carpeta de uploads para servir imágenes
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

def get_local_ip():
    """Detecta la dirección IP local de la máquina en la red Wi-Fi/Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No se envía paquete real, solo se abre socket para detectar interfaz activa
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_public_tunnel_url() -> Optional[str]:
    """Busca la URL pública del túnel Cloudflare si está activo."""
    # 1. Variable de entorno
    env_url = os.environ.get("TUNNEL_URL")
    if env_url:
        return env_url.strip()

    # 2. Archivo tunnel_url.txt
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tunnel_file = os.path.join(workspace_dir, "tunnel_url.txt")
    if os.path.exists(tunnel_file):
        try:
            with open(tunnel_file, "r", encoding="utf-8") as f:
                url = f.read().strip()
                if url.startswith("http"):
                    return url
        except Exception:
            pass

    # 3. Archivo tunnel.log o cloudflared.log en el workspace
    for log_name in ["tunnel.log", "cloudflared.log"]:
        log_path = os.path.join(workspace_dir, log_name)
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    matches = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                    if matches:
                        return matches[-1]
            except Exception:
                pass

    # 4. Tareas en antigravity (si existe la carpeta de logs de tareas)
    try:
        user_home = os.path.expanduser("~")
        brain_dir = os.path.join(user_home, ".gemini", "antigravity", "brain")
        if os.path.exists(brain_dir):
            for root, _, files in os.walk(brain_dir):
                for file in files:
                    if file.endswith(".log") and "task-" in file:
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                f.seek(0, os.SEEK_END)
                                size = f.tell()
                                f.seek(max(0, size - 5000))
                                snippet = f.read()
                                matches = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', snippet)
                                if matches:
                                    return matches[-1]
                        except Exception:
                            continue
    except Exception:
        pass

    return None

class ValidationPayload(BaseModel):
    verdict: str
    notes: Optional[str] = ""

@app.get("/api/system/network-info")
def get_network_info():
    """Retorna la información de red para conectar el celular."""
    local_ip = get_local_ip()
    port = 8000
    public_url = get_public_tunnel_url()
    # Si existe el túnel público seguro HTTPS, usarlo como URL móvil preferida
    preferred_mobile = public_url if public_url else f"http://{local_ip}:{port}"
    return {
        "local_ip": local_ip,
        "port": port,
        "public_url": public_url,
        "mobile_url": preferred_mobile,
        "local_url": f"http://localhost:{port}"
    }

@app.get("/api/system/database-status")
def get_database_status():
    """Reporta el motor de base de datos activo (Supabase Nube vs SQLite Local)."""
    try:
        from .cloud_adapter import is_supabase_enabled
        enabled = is_supabase_enabled()
    except Exception:
        try:
            from cloud_adapter import is_supabase_enabled
            enabled = is_supabase_enabled()
        except Exception:
            enabled = False

    return {
        "mode": "supabase" if enabled else "sqlite",
        "provider": "Supabase PostgreSQL (Nube 24/7)" if enabled else "SQLite Local (Disco)",
        "connected": True
    }

@app.get("/api/audits")
def api_list_audits(
    search: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Lista todas las auditorías previas con filtros opcionales de fecha y texto."""
    return list_audits(search=search, date=date, date_from=date_from, date_to=date_to)

@app.get("/api/audits/{audit_id}")
def api_get_audit(audit_id: int):
    """Obtiene el detalle de una auditoría y sus prendas con historial de reincidencias."""
    audit = get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    
    items = get_audit_items_with_history(audit_id)
    size_summary = get_audit_size_summary(audit_id)
    return {
        "audit": audit,
        "items": items,
        "size_summary": size_summary
    }

@app.delete("/api/audits/{audit_id}")
def api_delete_audit(audit_id: int):
    """Elimina una auditoría."""
    success = delete_audit(audit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return {"message": "Auditoría eliminada exitosamente"}

@app.post("/api/audits/upload")
async def api_upload_audit(
    file: UploadFile = File(...),
    audit_name: Optional[str] = Form(None),
    audit_date: Optional[str] = Form(None)
):
    """
    Recibe el archivo Excel de lectura (Lunes o Miércoles), lo analiza,
    guarda las prendas en la base de datos y crea la sesión de auditoría.
    """
    filename = file.filename or "inventario.xlsx"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx o .xls)")

    # Guardar en archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        items, meta = parse_excel_file(tmp_path)
        if not items:
            raise HTTPException(status_code=400, detail="No se encontraron referencias válidas en el Excel.")

        effective_date_str = audit_date.strip() if audit_date and audit_date.strip() else datetime.now().strftime("%Y-%m-%d")

        # Determinar nombre por defecto si no se especificó
        if not audit_name or not audit_name.strip():
            now_str = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            weekday = datetime.now().strftime("%A")
            dias_es = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                       "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
            dia_nombre = dias_es.get(weekday, "Lectura")
            audit_name = f"Lectura {dia_nombre} ({now_str})"

        audit_id = create_audit(audit_name.strip(), filename, items, audit_date=effective_date_str)

        # 1. Guardar copia física permanente del Excel original en el servidor
        safe_fname = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        permanent_excel_path = os.path.join(EXCELS_DIR, f"audit_{audit_id}_{safe_fname}")
        shutil.copyfile(tmp_path, permanent_excel_path)

        # 1.1 Sincronizar archivo original con Supabase Storage para persistencia 24/7 en la nube
        if is_supabase_enabled():
            try:
                try:
                    from .cloud_adapter import get_client, get_storage_bucket
                except Exception:
                    from cloud_adapter import get_client, get_storage_bucket
                client = get_client()
                if client:
                    bucket = get_storage_bucket()
                    storage_path = f"excels/audit_{audit_id}_{safe_fname}"
                    with open(permanent_excel_path, "rb") as ef:
                        client.storage.from_(bucket).upload(storage_path, ef.read(), file_options={"upsert": "true"})
            except Exception as st_err:
                print(f"[Supabase Storage] Error respaldando Excel original en la nube: {st_err}")

        # 2. Comparación automática histórica: calcular cuántas prendas de este nuevo archivo ya se repetían en auditorías pasadas
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(DISTINCT i.id) 
        FROM audit_items i
        WHERE i.audit_id = ? 
          AND EXISTS (
              SELECT 1 FROM audit_items prev 
              WHERE prev.audit_id != ? 
                AND (prev.reference = i.reference OR (prev.base_reference IS NOT NULL AND prev.base_reference != '' AND prev.base_reference = i.base_reference))
          )
        """, (audit_id, audit_id))
        recurrent_count = cursor.fetchone()[0]
        conn.close()

        return {
            "audit_id": audit_id,
            "audit_name": audit_name,
            "filename": filename,
            "items_count": len(items),
            "recurrent_count": recurrent_count,
            "meta": meta
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el Excel: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/api/audits/{audit_id}/download-original")
def api_download_original_excel(audit_id: int):
    """Permite descargar el archivo Excel original subido por el usuario en esta auditoría."""
    audit = get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    
    filename = audit.get("filename", "inventario.xlsx")
    safe_fname = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    target_path = os.path.join(EXCELS_DIR, f"audit_{audit_id}_{safe_fname}")
    
    if not os.path.exists(target_path):
        candidates = [f for f in os.listdir(EXCELS_DIR) if f.startswith(f"audit_{audit_id}_")]
        if candidates:
            target_path = os.path.join(EXCELS_DIR, candidates[0])
        else:
            raise HTTPException(status_code=404, detail="El archivo Excel original no se encuentra guardado en el servidor")
            
    return FileResponse(
        target_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

@app.post("/api/items/{item_id}/validate")
def api_validate_item(item_id: int, payload: ValidationPayload):
    """Guarda el dictamen de validación y observaciones para una prenda."""
    success = update_item_validation(item_id, payload.verdict, payload.notes or "")
    if not success:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return {"message": "Prenda validada correctamente"}

def optimize_and_save_photo(upload_file: UploadFile, reference: str, base_reference: str = "", name: str = "") -> str:
    """Optimiza la imagen con Pillow (redimensiona y comprime) y la guarda permanentemente de forma universal."""
    clean_ref = "".join(c for c in (base_reference or reference) if c.isalnum() or c in ("-", "_")).strip()
    if not clean_ref:
        clean_ref = "prenda"
        
    filename = f"ref_{clean_ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    dest_path = os.path.join(UPLOADS_DIR, filename)

    try:
        image = Image.open(upload_file.file)
        # Convertir a RGB en caso de PNG o formato transparente
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Redimensionar si es muy grande (máximo 1600x1600)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        # Guardar comprimida en JPEG de buena calidad
        image.save(dest_path, "JPEG", quality=85, optimize=True)
    except Exception:
        # Si Pillow falla por algún formato extraño, guardar directo
        upload_file.file.seek(0)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

    photo_url = f"/uploads/{filename}"
    save_catalog_photo(reference, photo_url, base_reference, name)
    return photo_url

@app.post("/api/items/{item_id}/photo")
async def api_upload_item_photo(item_id: int, file: UploadFile = File(...)):
    """
    Sube o toma una foto para una prenda de la auditoría.
    La foto queda asociada universalmente a todas las tallas de la referencia en el catálogo maestro.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT reference, base_reference, name FROM audit_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    reference = row["reference"]
    base_ref = row["base_reference"] or ""
    item_name = row["name"] or ""
    photo_url = optimize_and_save_photo(file, reference, base_ref, item_name)

    return {
        "message": "Foto guardada exitosamente y asignada de forma universal a la referencia",
        "reference": reference,
        "base_reference": base_ref,
        "name": item_name,
        "photo_url": photo_url
    }

@app.post("/api/references/{reference}/photo")
async def api_upload_reference_photo(reference: str, file: UploadFile = File(...)):
    """Sube o actualiza la foto directamente para una referencia dada."""
    photo_url = optimize_and_save_photo(file, reference)
    return {
        "message": "Foto de referencia actualizada universalmente",
        "reference": reference,
        "photo_url": photo_url
    }

@app.delete("/api/items/{item_id}/photo")
def api_delete_item_photo(item_id: int):
    """Elimina la foto asociada a una prenda y su referencia en el catálogo universal."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT reference, base_reference, name FROM audit_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    reference = row["reference"]
    base_ref = row["base_reference"] or ""
    item_name = row["name"] or ""

    delete_catalog_photo(reference, base_ref, item_name)
    return {
        "message": "Foto eliminada correctamente del catálogo universal",
        "reference": reference,
        "base_reference": base_ref
    }

@app.delete("/api/references/{reference}/photo")
def api_delete_reference_photo(reference: str):
    """Elimina la foto directamente para una referencia o modelo del catálogo."""
    delete_catalog_photo(reference)
    return {
        "message": f"Foto de la referencia {reference} eliminada correctamente",
        "reference": reference
    }

@app.get("/api/export/{audit_id}/excel")
def api_export_audit_excel(audit_id: int):
    """
    Descarga el archivo Excel original modificado con los hallazgos de validación,
    dictámenes, observaciones y conteo físico en sus columnas correspondientes
    para responder directamente al correo oficial de la central.
    """
    audit = get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
        
    items = get_audit_items_with_history(audit_id)
    
    filename = audit.get("filename", "inventario.xlsx")
    safe_fname = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    target_path = os.path.join(EXCELS_DIR, f"audit_{audit_id}_{safe_fname}")
    
    # 1. Buscar en disco local
    if not os.path.exists(target_path):
        candidates = [f for f in os.listdir(EXCELS_DIR) if f.startswith(f"audit_{audit_id}_")]
        if candidates:
            target_path = os.path.join(EXCELS_DIR, candidates[0])
            
    # 2. Si no está en disco local (ej. reinicio de contenedor en Render), recuperar de Supabase Storage
    if not os.path.exists(target_path) and is_supabase_enabled():
        try:
            try:
                from .cloud_adapter import get_client, get_storage_bucket
            except Exception:
                from cloud_adapter import get_client, get_storage_bucket
            client = get_client()
            if client:
                bucket = get_storage_bucket()
                storage_path = f"excels/audit_{audit_id}_{safe_fname}"
                content = client.storage.from_(bucket).download(storage_path)
                if content:
                    with open(target_path, "wb") as f:
                        f.write(content)
        except Exception as e:
            print(f"[Supabase Storage] No se pudo recuperar copia del Excel en la nube: {e}")

    # Nombre de salida conservando el nombre original
    base, ext = os.path.splitext(filename)
    if not ext:
        ext = ".xlsx"
    out_filename = f"{base}_REVISADO{ext}"
    out_path = os.path.join(tempfile.gettempdir(), f"audit_{audit_id}_{out_filename}")

    # 3. Intentar modificar el archivo original exacto
    success = False
    if os.path.exists(target_path):
        try:
            success = modify_original_excel(target_path, audit, items, out_path)
        except Exception as e:
            print(f"[Excel Export] Error al modificar plantilla original: {e}")
            success = False

    # 4. Fallback si no había plantilla original disponible
    if not success or not os.path.exists(out_path):
        generate_validation_excel(audit, items, out_path)

    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=out_filename
    )

@app.get("/api/export/{audit_id}/email-html")
def api_export_email_html(audit_id: int, only_validated: bool = False):
    """Retorna la tabla HTML formateada para copiar y pegar directamente en el correo de respuesta."""
    audit = get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
        
    items = get_audit_items_with_history(audit_id)
    html_content = generate_email_table_html(audit, items, only_validated=only_validated)
    return HTMLResponse(content=html_content)

@app.get("/api/stats/recurrences")
def api_recurrences_summary():
    """Retorna la lista de prendas que más veces han fallado en auditorías."""
    return get_recurring_summary()

@app.get("/api/catalog")
def api_get_catalog(
    q: Optional[str] = None,
    gender: Optional[str] = None,
    garment_type: Optional[str] = None,
    has_photo: Optional[bool] = None
):
    """Retorna el catálogo maestro de prendas con filtros de búsqueda."""
    items = get_master_catalog(search=q, gender=gender, garment_type=garment_type, has_photo=has_photo)
    return {
        "total": len(items),
        "items": items
    }

@app.get("/api/catalog/stats")
def api_get_catalog_stats():
    """Retorna estadísticas y filtros del catálogo maestro."""
    return get_catalog_stats()

@app.get("/api/system/database-status")
def api_database_status():
    """Retorna el estado de la conexión a la base de datos (Supabase Cloud o SQLite)."""
    supabase_active = is_supabase_enabled()
    return {
        "mode": "supabase" if supabase_active else "sqlite",
        "supabase_connected": supabase_active,
        "database": "PostgreSQL (Supabase Cloud)" if supabase_active else "SQLite Local",
        "storage": "Supabase Storage (garment-photos)" if supabase_active else "Almacenamiento Local (/uploads)"
    }

# -------------------------------------------------------------
# PYDANTIC MODELS & RUTAS DEL PORTAL / HUB OPERATIVO
# -------------------------------------------------------------

class EmployeeCreate(BaseModel):
    name: str
    role: Optional[str] = "Asesor Comercial"
    phone: Optional[str] = ""
    color_tag: Optional[str] = "blue"

class EmployeeUpdate(BaseModel):
    name: str
    role: str
    phone: Optional[str] = ""
    color_tag: Optional[str] = "blue"
    is_active: Optional[int] = 1

class ShiftItem(BaseModel):
    employee_id: int
    day_of_week: str
    shift_type: str
    start_time: Optional[str] = ""
    end_time: Optional[str] = ""
    hours: Optional[float] = 0.0
    notes: Optional[str] = ""

class ScheduleSaveRequest(BaseModel):
    shifts: List[ShiftItem]
    notes: Optional[str] = ""

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "General"
    day_of_week: Optional[str] = ""
    due_date: Optional[str] = ""
    due_time: Optional[str] = ""
    priority: Optional[str] = "Media"
    assigned_to: Optional[str] = ""


@app.get("/api/hub/summary")
def api_get_hub_summary():
    """Retorna métricas consolidadas para las tarjetas principales del Hub."""
    return get_hub_summary()


# Rutas de Colaboradores / Empleados
@app.get("/api/employees")
def api_list_employees(active_only: bool = True):
    return list_employees(active_only=active_only)

@app.post("/api/employees")
def api_create_employee(emp: EmployeeCreate):
    if not emp.name or not emp.name.strip():
        raise HTTPException(status_code=400, detail="El nombre del colaborador es obligatorio")
    created = create_employee(
        name=emp.name,
        role=emp.role or "Asesor Comercial",
        phone=emp.phone or "",
        color_tag=emp.color_tag or "blue"
    )
    return created

@app.put("/api/employees/{emp_id}")
def api_update_employee(emp_id: int, emp: EmployeeUpdate):
    updated = update_employee(
        emp_id=emp_id,
        name=emp.name,
        role=emp.role,
        phone=emp.phone or "",
        color_tag=emp.color_tag or "blue",
        is_active=emp.is_active if emp.is_active is not None else 1
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    return updated

@app.delete("/api/employees/{emp_id}")
def api_delete_employee(emp_id: int):
    ok = delete_employee(emp_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    return {"message": "Colaborador eliminado correctamente", "id": emp_id}


# Rutas de Horarios Semanales
@app.get("/api/schedules")
def api_list_schedules():
    return list_schedules()

@app.get("/api/schedules/week/{week_start_date}")
def api_get_schedule_week(week_start_date: str):
    """Obtiene o inicializa el horario de la semana que inicia en week_start_date (YYYY-MM-DD)."""
    return get_or_create_weekly_schedule(week_start_date)

@app.post("/api/schedules/{schedule_id}/shifts")
def api_save_schedule_shifts(schedule_id: int, payload: ScheduleSaveRequest):
    shifts_dicts = [s.model_dump() for s in payload.shifts]
    save_schedule_shifts(schedule_id, shifts_dicts, notes=payload.notes)
    return {"message": "Horario guardado exitosamente", "schedule_id": schedule_id, "total_shifts": len(shifts_dicts)}


# Rutas de Tareas y Recordatorios
@app.get("/api/tasks")
def api_list_tasks(
    day_of_week: Optional[str] = None,
    due_date: Optional[str] = None,
    completed: Optional[int] = None
):
    return list_store_tasks(day_of_week=day_of_week, due_date=due_date, is_completed=completed)

@app.post("/api/tasks")
def api_create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="El título de la tarea es obligatorio")
    created = create_store_task(
        title=task.title,
        description=task.description or "",
        category=task.category or "General",
        day_of_week=task.day_of_week or "",
        due_date=task.due_date or "",
        due_time=task.due_time or "",
        priority=task.priority or "Media",
        assigned_to=task.assigned_to or ""
    )
    return created

@app.post("/api/tasks/{task_id}/toggle")
def api_toggle_task(task_id: int):
    updated = toggle_store_task(task_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return updated

@app.delete("/api/tasks/{task_id}")
def api_delete_task(task_id: int):
    ok = delete_store_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return {"message": "Tarea eliminada correctamente", "id": task_id}

# Montar frontend al final para que la raíz '/' sirva el cliente web
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
