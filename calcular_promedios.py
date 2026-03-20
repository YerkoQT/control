"""
calcular_promedios.py
─────────────────────────────────────────────────────────────
Lee todos los Issues con label 'quiz-nota' del repositorio,
extrae el JSON de cada uno, calcula el promedio por estudiante
(agrupado por CI) y exporta:
  - promedios.csv   → para descargar como artefacto
  - reporte.txt     → se muestra en la consola de Actions
─────────────────────────────────────────────────────────────
"""

import os, json, csv, requests
from collections import defaultdict
from datetime import datetime

# ─── Credenciales desde variables de entorno (GitHub Actions) ───
TOKEN = os.environ.get("GH_TOKEN", "")
REPO  = os.environ.get("GH_REPO",  "")

if not TOKEN or not REPO:
    print("ERROR: GH_TOKEN o GH_REPO no definidos.")
    exit(1)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# ─── 1. Obtener todos los issues con label quiz-nota ────────────
print(f"\nConectando a: https://github.com/{REPO}")
print("Descargando issues con label 'quiz-nota'...")

issues = []
page   = 1
while True:
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/issues",
        headers=HEADERS,
        params={
            "labels":   "quiz-nota",
            "state":    "all",       # open + closed
            "per_page": 100,
            "page":     page
        }
    )
    if r.status_code != 200:
        print(f"ERROR al obtener issues: {r.status_code} — {r.text}")
        exit(1)
    data = r.json()
    if not data:
        break
    issues += data
    page   += 1

print(f"Total de registros encontrados: {len(issues)}\n")

# ─── 2. Extraer JSON de cada issue ──────────────────────────────
registros = []
errores   = 0

for issue in issues:
    body = issue.get("body", "")
    try:
        start = body.index("```json") + 7
        end   = body.index("```", start)
        rec   = json.loads(body[start:end].strip())
        # Asegurar campos mínimos
        rec.setdefault("nm",      issue["title"])
        rec.setdefault("ci",      "?")
        rec.setdefault("nota",    0)
        rec.setdefault("ok",      0)
        rec.setdefault("tot",     0)
        rec.setdefault("quizzes", "?")
        rec.setdefault("date",    "?")
        registros.append(rec)
    except Exception as e:
        errores += 1

print(f"Registros válidos:  {len(registros)}")
print(f"Registros con error:{errores}\n")

if not registros:
    print("No hay registros para procesar.")
    exit(0)

# ─── 3. Agrupar por CI ──────────────────────────────────────────
por_ci = defaultdict(list)
for rec in registros:
    por_ci[rec["ci"]].append(rec)

# ─── 4. Calcular estadísticas por estudiante ────────────────────
resultados = []

for ci, intentos in por_ci.items():
    # Usar el nombre del intento más reciente
    nombre   = intentos[-1].get("nm", "?")
    notas    = [float(r["nota"]) for r in intentos]
    promedio = round(sum(notas) / len(notas), 1)
    mejor    = max(notas)
    peor     = min(notas)
    total_i  = len(intentos)
    estado   = "APROBADO" if promedio >= 51 else "REPROBADO"

    # Quizzes rendidos (únicos)
    todos_qz = set()
    for r in intentos:
        for q in str(r.get("quizzes","")).split(","):
            q = q.strip()
            if q:
                todos_qz.add(q)
    quizzes_rendidos = ",".join(sorted(todos_qz, key=lambda x: int(x) if x.isdigit() else 99))

    resultados.append({
        "nombre":          nombre,
        "ci":              ci,
        "intentos":        total_i,
        "promedio":        promedio,
        "mejor":           mejor,
        "peor":            peor,
        "quizzes":         quizzes_rendidos,
        "estado":          estado,
        "ultima_fecha":    intentos[-1].get("date","?")
    })

# Ordenar por promedio descendente
resultados.sort(key=lambda x: x["promedio"], reverse=True)

# ─── 5. Exportar CSV ────────────────────────────────────────────
CSV_FILE = "promedios.csv"
campos   = ["nombre","ci","intentos","promedio","mejor","peor",
            "quizzes","estado","ultima_fecha"]

with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    w.writerows(resultados)

print(f"CSV exportado: {CSV_FILE}\n")

# ─── 6. Generar reporte de texto para la consola ────────────────
SEP  = "=" * 80
sep2 = "-" * 80

lines = []
lines.append(SEP)
lines.append(f"  REPORTE DE PROMEDIOS — Mini Quiz Misiles Balísticos")
lines.append(f"  Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
lines.append(f"  Repositorio: {REPO}")
lines.append(SEP)
lines.append("")

# Resumen
aprobados  = sum(1 for r in resultados if r["estado"] == "APROBADO")
reprobados = len(resultados) - aprobados
lines.append(f"  Total estudiantes : {len(resultados)}")
lines.append(f"  Aprobados  (≥51%) : {aprobados}")
lines.append(f"  Reprobados (<51%) : {reprobados}")
lines.append(f"  Total registros   : {len(registros)}")
lines.append("")
lines.append(sep2)

# Encabezado tabla
lines.append(
    f"  {'#':<4} {'Nombre':<28} {'CI':<12} {'Int.':<5} "
    f"{'Prom.':<8} {'Mejor':<8} {'Peor':<8} {'Estado'}"
)
lines.append(sep2)

for i, r in enumerate(resultados, 1):
    simbolo = "✓" if r["estado"] == "APROBADO" else "✗"
    lines.append(
        f"  {i:<4} {r['nombre'][:27]:<28} {r['ci']:<12} {r['intentos']:<5} "
        f"{r['promedio']:<8} {r['mejor']:<8} {r['peor']:<8} "
        f"{simbolo} {r['estado']}"
    )

lines.append(sep2)
lines.append("")

# Detalle por estudiante
lines.append("  DETALLE POR ESTUDIANTE")
lines.append(sep2)
for r in resultados:
    lines.append(f"  Nombre  : {r['nombre']}")
    lines.append(f"  CI      : {r['ci']}")
    lines.append(f"  Promedio: {r['promedio']}%  |  Mejor: {r['mejor']}%  |  Peor: {r['peor']}%")
    lines.append(f"  Intentos: {r['intentos']}  |  Quizzes rendidos: {r['quizzes']}")
    lines.append(f"  Estado  : {r['estado']}  |  Último intento: {r['ultima_fecha']}")
    lines.append("")

lines.append(SEP)

reporte = "\n".join(lines)
print(reporte)

# Guardar reporte en archivo también
with open("reporte.txt","w",encoding="utf-8") as f:
    f.write(reporte)

print(f"\nArchivos generados:")
print(f"  - {CSV_FILE}   (descargar desde Artifacts)")
print(f"  - reporte.txt  (visible en la consola de Actions)")
