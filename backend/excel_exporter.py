import os
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_validation_excel(audit_info: Dict[str, Any], items: List[Dict[str, Any]], output_path: str) -> str:
    """
    Genera un archivo Excel (.xlsx) con los datos del inventario y las columnas
    de validación, motivos y observaciones agregadas para enviar de respuesta.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Informe de Auditoría"

    # Estilos
    font_title = Font(name="Calibri", size=14, bold=True, color="1E293B")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="64748B")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    
    fill_header = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") # Slate 900
    fill_faltante = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Red 100
    fill_sobrante = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Green 100
    fill_validada = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid") # Sky 100
    
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # Título del reporte
    ws.merge_cells("A1:G1")
    ws["A1"] = f"INFORME DE AUDITORÍA - FARO: {audit_info.get('name', 'Lectura de Inventario')}"
    ws["A1"].font = font_title
    
    ws.merge_cells("A2:G2")
    ws["A2"] = f"Archivo original: {audit_info.get('filename')} | Generado: {audit_info.get('uploaded_at')}"
    ws["A2"].font = font_subtitle

    # Fila de encabezados
    headers = [
        "Referencia",
        "Nombre Prenda",
        "Talla",
        "Color",
        "Código de Barras",
        "Categoría",
        "Teórico",
        "Tienda",
        "Bodega",
        "Total Físico",
        "Diferencia",
        "Tipo Diferencia",
        "Estado Validación",
        "Dictamen / Justificación",
        "Observaciones / Notas",
        "Fecha Validación",
        "Tiene Foto"
    ]

    header_row = 4
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    # Llenado de filas
    current_row = 5
    for item in items:
        diff = item.get("difference", 0)
        tipo_dif = "Faltante" if diff < 0 else ("Sobrante" if diff > 0 else "Exacto")
        total_fisico = (item.get("store_count") or 0) + (item.get("warehouse_count") or 0)
        has_photo = "SÍ" if item.get("photo_url") else "NO"

        row_values = [
            item.get("reference", ""),
            item.get("name", ""),
            item.get("size", "-"),
            item.get("color", "-"),
            item.get("barcode", "-"),
            item.get("category", "General"),
            item.get("theoretical_count", 0),
            item.get("store_count", 0),
            item.get("warehouse_count", 0),
            total_fisico,
            diff,
            tipo_dif,
            item.get("status", "pendiente").capitalize(),
            item.get("validation_verdict", ""),
            item.get("validation_notes", ""),
            item.get("validated_at", "") or "-",
            has_photo
        ]

        for col_idx, val in enumerate(row_values, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font_regular
            cell.border = border_thin
            cell.alignment = Alignment(vertical="center")

            # Alineación numérica
            if col_idx in [7, 8, 9, 10, 11]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col_idx in [3, 4, 12, 13, 16, 17]:
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Resaltar diferencias
            if col_idx in [11, 12]:
                if diff < 0:
                    cell.fill = fill_faltante
                    cell.font = Font(name="Calibri", size=10, bold=True, color="991B1B")
                elif diff > 0:
                    cell.fill = fill_sobrante
                    cell.font = Font(name="Calibri", size=10, bold=True, color="166534")

            # Resaltar si ya está validada
            if col_idx == 13 and item.get("status") == "validada":
                cell.fill = fill_validada
                cell.font = Font(name="Calibri", size=10, bold=True, color="0369A1")

        current_row += 1

    # Ajuste automático del ancho de columnas
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row < 4:
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    # Congelar panel para que los encabezados permanezcan visibles al hacer scroll
    ws.freeze_panes = "A5"

    wb.save(output_path)
    return output_path

def generate_email_table_html(audit_info: Dict[str, Any], items: List[Dict[str, Any]], only_validated: bool = False) -> str:
    """
    Genera una tabla HTML limpia y formateada para copiar y pegar directamente
    en el cuerpo de un correo electrónico (Outlook, Gmail, etc.), con consolidado de tallas.
    """
    target_items = items
    if only_validated:
        target_items = [i for i in items if i.get("status") == "validada"]

    # Calcular consolidado por tallas
    size_tally = {}
    for i in target_items:
        s = str(i.get("size") or "-").strip().upper()
        diff = i.get("difference", 0)
        if s not in size_tally:
            size_tally[s] = {"faltantes": 0, "sobrantes": 0, "refs": 0}
        size_tally[s]["refs"] += 1
        if diff < 0:
            size_tally[s]["faltantes"] += abs(diff)
        elif diff > 0:
            size_tally[s]["sobrantes"] += diff

    # Ordenar tallas lógicamente
    order_map = {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '28': 7, '30': 8, '32': 9, '34': 10, '36': 11}
    sorted_sizes = sorted(size_tally.keys(), key=lambda x: (order_map.get(x, 99), x))

    html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; color: #1e293b; max-width: 100%;">
        <div style="background-color: #0f172a; color: #ffffff; padding: 14px 18px; border-radius: 6px 6px 0 0;">
            <h3 style="margin: 0; font-size: 16px;">Informe de Revisión de Inventario - FARO</h3>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #cbd5e1;">
                <strong>Lectura:</strong> {audit_info.get('name', 'Auditoría')} | 
                <strong>Prendas en reporte:</strong> {len(target_items)}
            </p>
        </div>

        <!-- CONSOLIDADO POR TALLAS -->
        <div style="background-color: #f8fafc; border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; padding: 12px 16px; border-bottom: 2px solid #e2e8f0;">
            <h4 style="margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase; color: #475569; letter-spacing: 0.5px;">
                📊 Consolidado de Diferencias por Talla
            </h4>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
    """

    for s in sorted_sizes:
        data = size_tally[s]
        html += f"""
                <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-size: 11px; margin-right: 8px; margin-bottom: 6px; display: inline-block;">
                    <strong>Talla {s}:</strong> 
                    <span style="color: #dc2626; font-weight: bold; margin-left: 4px;">-{data['faltantes']} faltan</span> | 
                    <span style="color: #16a34a; font-weight: bold;">+{data['sobrantes']} sobran</span>
                </div>
        """

    html += """
            </div>
        </div>

        <table style="width: 100%; border-collapse: collapse; border: 1px solid #cbd5e1; font-size: 12px; margin-top: 0;">
            <thead>
                <tr style="background-color: #f1f5f9; color: #334155; text-align: left; border-bottom: 2px solid #94a3b8;">
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1;">Referencia</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1;">Descripción</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: center;">Talla</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: center;">Color</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: right;">Teórico</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: right;">Tienda</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: right;">Bodega</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: right;">Físico</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: center;">Diferencia por Talla</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1;">Dictamen / Revisión</th>
                    <th style="padding: 8px 10px; border: 1px solid #cbd5e1;">Observaciones</th>
                </tr>
            </thead>
            <tbody>
    """

    for item in target_items:
        diff = item.get("difference", 0)
        total_fisico = (item.get("store_count") or 0) + (item.get("warehouse_count") or 0)
        size_label = item.get("size", "-")
        
        diff_bg = "#ffffff"
        diff_color = "#334155"
        diff_label = str(diff)
        
        if diff < 0:
            diff_bg = "#fee2e2"
            diff_color = "#991b1b"
            diff_label = f"Faltan {abs(diff)} en {size_label}"
        elif diff > 0:
            diff_bg = "#dcfce7"
            diff_color = "#166534"
            diff_label = f"+{diff} Sobran en {size_label}"

        verdict = item.get("validation_verdict") or "Pendiente por validar"
        verdict_color = "#0369a1" if item.get("status") == "validada" else "#64748b"
        notes = item.get("validation_notes") or "-"

        html += f"""
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; font-weight: bold;">{item.get('reference', '')}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0;">{item.get('name', '')}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: center;">{item.get('size', '-')}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: center;">{item.get('color', '-')}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: right;">{item.get('theoretical_count', 0)}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: right;">{item.get('store_count', 0)}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: right;">{item.get('warehouse_count', 0)}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: right; font-weight: bold;">{total_fisico}</td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; text-align: center; background-color: {diff_bg}; color: {diff_color}; font-weight: bold;">
                        {diff_label}
                    </td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; color: {verdict_color}; font-weight: bold;">
                        {verdict}
                    </td>
                    <td style="padding: 6px 10px; border: 1px solid #e2e8f0; font-style: italic;">
                        {notes}
                    </td>
                </tr>
        """

    html += """
            </tbody>
        </table>
        <p style="margin-top: 10px; font-size: 11px; color: #64748b;">
            Reporte generado automáticamente desde FARO - Flujo de Almacén y Reorden Operativo.
        </p>
    </div>
    """
    return html
