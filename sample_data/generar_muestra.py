import os
import random
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

SAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))

PRENDAS_BASE = [
    # Camisetas
    ("77-CAM-001", "CAMISETA OVERSIZE ESTAMPADA GRAPHIC", "Camisetas"),
    ("77-CAM-002", "CAMISETA BASICA CUELLO REDONDO ALGODON", "Camisetas"),
    ("77-CAM-003", "CAMISETA POLO PIQUE CLASICA", "Camisetas"),
    ("77-CAM-004", "CAMISILLA RIB TANK TOP", "Camisetas"),
    ("77-CAM-005", "CAMISETA HEAVYWEIGHT VINTAGE WASH", "Camisetas"),
    # Pantalones & Jeans
    ("77-PAN-101", "JEAN WIDE LEG TIRO ALTO RIGIDO", "Pantalones"),
    ("77-PAN-102", "JEAN SLIM FIT STRETCH AZUL MEDIO", "Pantalones"),
    ("77-PAN-103", "PANTALON CARGO CON BOLSILLOS MILITAR", "Pantalones"),
    ("77-PAN-104", "PANTALON JOGGER DRILL ELASTICO", "Pantalones"),
    ("77-PAN-105", "JEAN CARPENTER DETALLES COSTURA", "Pantalones"),
    # Faldas & Shorts
    ("77-FAL-201", "FALDA CORTA PLISADA TABLAS", "Faldas"),
    ("77-FAL-202", "FALDA LARGA DENIM CON ABERTURA", "Faldas"),
    ("77-SHO-203", "SHORT DENIM MOM FIT ROTURAS", "Shorts"),
    ("77-SHO-204", "BERMUDA RELAXED FIT RUSTICA", "Shorts"),
    # Chaquetas & Buzos
    ("77-CHQ-301", "CHAQUETA DENIM OVERSIZE TRUCKER", "Chaquetas"),
    ("77-CHQ-302", "CHAQUETA BOMBER ACOLCHADA NYLON", "Chaquetas"),
    ("77-BUZ-303", "BUZO HOODIE CON CAPOTA Y BOLSILLO", "Buzos"),
    ("77-BUZ-304", "BUZO CUELLO REDONDO BORDADO SEVEN", "Buzos"),
    # Vestidos
    ("77-VES-401", "VESTIDO CORTO TIRAS ESTAMPADO FLORAL", "Vestidos"),
    ("77-VES-402", "VESTIDO MIDI ASIMETRICO CANALE", "Vestidos"),
    # Camisas & Blusas
    ("77-CMS-501", "CAMISA MANGA LARGA LINO SLOUCHY", "Camisas y Blusas"),
    ("77-BLS-502", "BLUSA CROP TOP SATINADA CRUZADA", "Camisas y Blusas"),
    # Accesorios
    ("77-ACC-601", "GORRA BASEBALL BORDADA SEVEN SEVEN", "Accesorios"),
    ("77-ACC-602", "CORREA CUERO HEBILLA METALICA", "Accesorios"),
    ("77-ACC-603", "MORRAL CANVAS CON DIVISION LAPTOP", "Accesorios"),
]

TALLAS = ["XS", "S", "M", "L", "XL"]
COLORES = ["NEGRO", "BLANCO", "AZUL INDIGO", "CRUDO", "VERDE MILITAR", "BEIGE", "GRIS JASPE", "ROSA PALO"]

def generar_excel_inventario(nombre_archivo: str, titulo: str, num_filas: int = 210, seed: int = 42):
    random.seed(seed)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lectura Físico vs Teórico"

    headers = [
        "REFERENCIA",
        "DESCRIPCION",
        "TALLA",
        "COLOR",
        "CODIGO_BARRAS",
        "STOCK_TEORICO",
        "LECTURA_TIENDA",
        "LECTURA_BODEGA",
        "DIFERENCIA"
    ]

    # Estilos de encabezado
    font_h = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill_h = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    align_c = Alignment(horizontal="center", vertical="center")

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = font_h
        cell.fill = fill_h
        cell.alignment = align_c

    for row_idx in range(2, num_filas + 2):
        prenda_base = random.choice(PRENDAS_BASE)
        ref_code = prenda_base[0]
        desc = prenda_base[1]
        talla = random.choice(TALLAS)
        color = random.choice(COLORES)
        
        # Generar código de barras tipo EAN-13
        ean = f"770{random.randint(100000000, 999999999)}"
        
        # Generar conteos de stock
        # ~60% faltantes, ~40% sobrantes para simular el caso de uso
        teorico = random.randint(3, 25)
        
        tipo = random.choices(["faltante", "sobrante", "exacto"], weights=[0.55, 0.35, 0.10])[0]
        if tipo == "faltante":
            diff = -random.randint(1, min(4, teorico))
        elif tipo == "sobrante":
            diff = random.randint(1, 3)
        else:
            diff = 0

        total_fisico = max(0, teorico + diff)
        
        # Distribuir entre tienda y bodega
        tienda = random.randint(0, total_fisico)
        bodega = total_fisico - tienda

        ws.cell(row=row_idx, column=1, value=f"{ref_code}-{talla}")
        ws.cell(row=row_idx, column=2, value=desc)
        ws.cell(row=row_idx, column=3, value=talla)
        ws.cell(row=row_idx, column=4, value=color)
        ws.cell(row=row_idx, column=5, value=ean)
        ws.cell(row=row_idx, column=6, value=teorico)
        ws.cell(row=row_idx, column=7, value=tienda)
        ws.cell(row=row_idx, column=8, value=bodega)
        ws.cell(row=row_idx, column=9, value=diff)

    # Anchos de columna
    for col in ws.columns:
        ws.column_dimensions[openpyxl.utils.get_column_letter(col[0].column)].width = 16

    ws.column_dimensions["B"].width = 38
    ws.column_dimensions["E"].width = 18

    file_path = os.path.join(SAMPLE_DIR, nombre_archivo)
    wb.save(file_path)
    print(f"Archivo generado: {file_path} con {num_filas} referencias.")
    return file_path

if __name__ == "__main__":
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    generar_excel_inventario("inventario_lunes_muestra.xlsx", "Lectura Lunes Seven Seven", num_filas=215, seed=101)
    generar_excel_inventario("inventario_miercoles_muestra.xlsx", "Lectura Miércoles Seven Seven", num_filas=205, seed=202)
