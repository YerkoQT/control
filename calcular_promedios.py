"""
calcular_promedios.py
"""
import os, json, csv, requests, sys
from collections import defaultdict
from datetime import datetime

TOKEN = os.environ.get("GH_TOKEN", "")
REPO  = os.environ.get("GH_REPO",  "")

print("=" * 60)
print("  CALCULAR PROMEDIOS — Mini Quiz Misiles Balísticos")
print("=" * 60)
print(f"  Repositorio : {REPO}")
print(f"  Fecha/Hora  : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print()

if not TOKEN:
    print("ERROR: GH_TOKEN no encontrado.")
    sys.exit(1)
if not REPO:
    print("ERROR: GH_REPO no encontrado.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

# 1. Obtener issues
print("Descargando issues con label 'quiz-nota'...")
issues = []
page   = 1
while True:
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/issues",
        headers=HEADERS,
        params={"labels":"quiz-nota","state":"all","per_page":100,"page":page}
    )
    if r.status_code == 401:
        print(f"ERROR 401: Token sin permisos. Agrega 'permissions: issues: read' al workflow.")
        sys.exit(1)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:300]}")
        sys.exit(1)
    data = r.json()
    if not data: break
    issues += data
    print(f"  Pagina {page}: {len(data)} issues")
    page += 1

print(f"\nTotal issues: {len(issues)}")

if not issues:
    print("Sin registros todavia. Los issues se crean cuando un estudiante")
    print("termina el quiz con el token configurado en la URL.")
    with open("promedios.csv","w") as f:
        f.write("nombre,ci,intentos,promedio,mejor,peor,quizzes,estado,ultima_fecha\n")
    with open("reporte.txt","w") as f:
        f.write("Sin registros todavia.\n")
    sys.exit(0)

# 2. Extraer JSON
print("\nExtrayendo datos...")
registros = []
for issue in issues:
    body = issue.get("body","")
    try:
        s = body.index("```json") + 7
        e = body.index("```", s)
        rec = json.loads(body[s:e].strip())
        rec.setdefault("nm","?")
        rec.setdefault("ci","?")
        rec.setdefault("nota",0)
        rec.setdefault("quizzes","?")
        rec.setdefault("date","?")
        registros.append(rec)
    except:
        pass

print(f"Registros validos: {len(registros)}")

# 3. Agrupar por CI
por_ci = defaultdict(list)
for rec in registros:
    por_ci[rec["ci"]].append(rec)

# 4. Calcular promedios
resultados = []
for ci, intentos in por_ci.items():
    nombre   = intentos[-1].get("nm","?")
    notas    = [float(r["nota"]) for r in intentos]
    promedio = round(sum(notas)/len(notas), 1)
    mejor    = max(notas)
    peor     = min(notas)
    estado   = "APROBADO" if promedio >= 51 else "REPROBADO"
    todos_qz = set()
    for r in intentos:
        for q in str(r.get("quizzes","")).split(","):
            q=q.strip()
            if q.isdigit(): todos_qz.add(int(q))
    resultados.append({
        "nombre": nombre, "ci": ci,
        "intentos": len(intentos),
        "promedio": promedio, "mejor": mejor, "peor": peor,
        "quizzes": ",".join(str(q) for q in sorted(todos_qz)),
        "estado": estado,
        "ultima_fecha": intentos[-1].get("date","?")
    })

resultados.sort(key=lambda x: x["promedio"], reverse=True)

# 5. CSV
campos = ["nombre","ci","intentos","promedio","mejor","peor","quizzes","estado","ultima_fecha"]
with open("promedios.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    w.writerows(resultados)
print(f"CSV exportado: promedios.csv ({len(resultados)} estudiantes)")

# 6. Reporte
SEP = "=" * 70
sep = "-" * 70
L = []
L.append(SEP)
L.append("  REPORTE DE PROMEDIOS — Mini Quiz Misiles Balisticos")
L.append(f"  Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
L.append(SEP)
L.append(f"  Total estudiantes : {len(resultados)}")
L.append(f"  Aprobados  (>=51%): {sum(1 for r in resultados if r['estado']=='APROBADO')}")
L.append(f"  Reprobados (<51%) : {sum(1 for r in resultados if r['estado']!='APROBADO')}")
L.append(f"  Total registros   : {len(registros)}")
L.append("")
L.append(sep)
L.append(f"  {'#':<4} {'Nombre':<25} {'CI':<12} {'Int':<5} {'Prom%':<7} {'Mejor':<7} {'Peor':<7} Estado")
L.append(sep)
for i,r in enumerate(resultados,1):
    s = "OK" if r["estado"]=="APROBADO" else "--"
    L.append(f"  {i:<4} {r['nombre'][:24]:<25} {str(r['ci']):<12} {r['intentos']:<5} {r['promedio']:<7} {r['mejor']:<7} {r['peor']:<7} {s} {r['estado']}")
L.append(sep)
L.append("")
L.append("  DETALLE POR ESTUDIANTE")
L.append(sep)
for r in resultados:
    L.append(f"  Nombre   : {r['nombre']}")
    L.append(f"  CI       : {r['ci']}")
    L.append(f"  Promedio : {r['promedio']}%   Mejor: {r['mejor']}%   Peor: {r['peor']}%")
    L.append(f"  Intentos : {r['intentos']}   Quizzes rendidos: Q{r['quizzes']}")
    L.append(f"  Estado   : {r['estado']}")
    L.append(f"  Ultimo   : {r['ultima_fecha']}")
    L.append("")
L.append(SEP)

reporte = "\n".join(L)
print("\n" + reporte)
with open("reporte.txt","w",encoding="utf-8") as f:
    f.write(reporte)

print("\nArchivos listos:")
print("  -> promedios.csv  (descargar desde Artifacts)")
print("  -> reporte.txt    (visible en esta consola)")
