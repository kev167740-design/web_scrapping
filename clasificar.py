"""Clasifica cada registro de union.json con OpenAI (sentiment + category).

Uso:
    py clasificar.py                       # union.json -> union_etiquetado.json
    py clasificar.py --muestra 40          # prueba con 40 registros aleatorios
    py clasificar.py --entrada X.json --salida Y.json

El sentimiento se mide SIEMPRE respecto al banco del campo "brand" del registro.
Guarda el progreso en <salida>.parcial.json para poder reanudar si se corta.
"""
import argparse
import configparser
import html
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

RAIZ = Path(__file__).resolve().parent
MODELO = "gpt-4.1-mini"
LOTE = 25
HILOS = 8
MAX_CHARS = 2000

SENTIMENTS = {
    "positive": "elogio, agradecimiento, satisfacción o recomendación",
    "negative": "queja, crítica, enfado, burla, sarcasmo, intención de irse del banco o "
                "comparación que deja en mejor lugar a otro banco",
    "neutral": "preguntas, peticiones de información o comentarios sin carga emocional clara",
}
CATEGORIES = {
    "card": "Tarjetas de crédito y débito: límites, intereses, cuota anual, bloqueos, pagos rechazados",
    "accounts_fees": "Cuentas y comisiones: apertura y cierre, nómina, mantenimiento, cobros, "
                     "comisiones de cambio de divisa",
    "loans": "Financiación: hipotecas, préstamos personales, tipos de interés, Euríbor",
    "savings_investment": "Ahorro, inversión y seguros: depósitos, cuentas remuneradas, fondos, bróker, seguros",
    "app_payments": "App y pagos digitales: banca online, app, Bizum, transferencias, "
                    "domiciliaciones, pago con el móvil",
    "customer_service": "Atención al cliente y oficinas: teléfono, chat, gestor, esperas, trato, "
                        "oficinas, cajeros",
    "fraud": "Fraude y seguridad: phishing, SMS o llamadas falsas, cargos no reconocidos, "
             "cuentas bloqueadas por seguridad",
    "brand": "Marca y promociones: reacciones al vídeo o anuncio, campañas, ofertas, "
             "bonificaciones, patrocinios, imagen del banco",
    "other": "Sin relación con el banco: saludos, menciones a amigos, spam, bromas ajenas, "
             "texto sin sentido",
}
NOMBRES = {"bbva": "BBVA", "santander": "Banco Santander", "caixabank": "CaixaBank"}

PROMPT = f"""Eres un analista de reputación de marca de banca española. Recibirás comentarios y \
reseñas sobre tres bancos: BBVA, Banco Santander y CaixaBank, extraídos de TikTok, YouTube, \
Instagram, Facebook, X, Google Reviews y Trustpilot.

Cada elemento trae:
- "i": identificador (devuélvelo tal cual)
- "marca": el banco al que pertenece el registro (el banco cuyo vídeo, publicación, oficina o \
perfil se comentó)
- "red": red social de origen
- "estrellas": nota de 1 a 5 si es una reseña (puede faltar)
- "titulo": título de la reseña (puede faltar)
- "texto": el comentario

Asigna a cada elemento un "sentiment" y una "category".

## sentiment — SIEMPRE desde el punto de vista de "marca"
{chr(10).join(f'- {k}: {v}' for k, v in SENTIMENTS.items())}

Reglas clave:
- El sentimiento mide qué dice el comentario sobre el banco de "marca", NO el tono general.
  * Marca BBVA: "con esos intereses mejor me cambio a Santander" -> negative (aunque elogie a Santander).
  * Marca BBVA: "en Santander me cobraban de todo, en BBVA estoy encantado" -> positive.
  * Marca CaixaBank: "BBVA es mucho mejor" -> negative.
- Si el comentario solo habla de otro banco sin compararlo con "marca": usa el tono hacia la \
banca en general si lo hay; si no, neutral.
- Sarcasmo e ironía ("genial, otra comisión más 👏") -> negative.
- Quejas sobre la banca en general que incluyen a "marca" -> negative.
- Las estrellas son una pista para las reseñas, pero manda el texto si lo contradice.
- Preguntas o dudas sin queja ("¿cómo se activa Bizum?") -> neutral.
- Emojis sueltos: 😂🔥❤️👏 suelen ser positivos o de humor; interprétalos según el contexto.

## category — el tema principal (una sola)
{chr(10).join(f'- {k}: {v}' for k, v in CATEGORIES.items())}

Reglas:
- Si hay varios temas, elige el central de la queja o el elogio.
- Trato del personal, esperas, gestor, oficina o cajero -> customer_service (aunque la gestión \
fuera de una tarjeta o cuenta, si el problema principal es el trato o la atención).
- Comentarios de opinión sobre el banco sin tema concreto ("el mejor banco", "banco de ladrones") \
-> brand.
- Comentarios sin relación con el banco (saludos, etiquetar amigos, spam, texto sin sentido, \
chistes ajenos) -> other.

Los textos pueden estar en español, catalán, inglés u otros idiomas; clasifícalos igual.
Devuelve un resultado por cada "i" recibido, sin omitir ninguno."""

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "clasificacion",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["resultados"],
            "properties": {
                "resultados": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["i", "sentiment", "category"],
                        "properties": {
                            "i": {"type": "integer"},
                            "sentiment": {"type": "string", "enum": list(SENTIMENTS)},
                            "category": {"type": "string", "enum": list(CATEGORIES)},
                        },
                    },
                }
            },
        },
    },
}


def limpiar(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "", flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
    return t[:MAX_CHARS]


def a_elemento(i, r):
    texto = limpiar(r.get("text"))
    e = {"i": i, "marca": NOMBRES.get(r.get("brand"), r.get("brand")), "red": r.get("platform")}
    if r.get("rating") is not None:
        e["estrellas"] = r["rating"]
    titulo = limpiar(r.get("title"))
    # Trustpilot recorta el título con "…" cuando es el inicio del texto: no aporta nada
    if titulo and not texto.startswith(titulo.rstrip("…").rstrip()):
        e["titulo"] = titulo
    e["texto"] = texto
    return e


def clasificar_lote(cliente, elementos):
    ids = {e["i"] for e in elementos}
    for intento in range(5):
        try:
            resp = cliente.chat.completions.create(
                model=MODELO,
                temperature=0,
                response_format=SCHEMA,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": json.dumps(elementos, ensure_ascii=False)},
                ],
            )
            datos = json.loads(resp.choices[0].message.content)["resultados"]
            res = {d["i"]: (d["sentiment"], d["category"]) for d in datos if d["i"] in ids}
            if set(res) == ids:
                return res, resp.usage
            faltan = ids - set(res)
            if len(elementos) > 1 and intento >= 1:
                # reintenta solo los que faltan
                resto, uso = clasificar_lote(cliente, [e for e in elementos if e["i"] in faltan])
                res.update(resto)
                return res, resp.usage
        except Exception as ex:  # noqa: BLE001
            print(f"  aviso: {type(ex).__name__}: {ex} (reintento {intento + 1})", file=sys.stderr)
            time.sleep(2 ** intento)
    raise RuntimeError(f"No se pudo clasificar el lote {sorted(ids)[:3]}…")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=str(RAIZ / "union.json"))
    ap.add_argument("--salida", default=str(RAIZ / "union_etiquetado.json"))
    ap.add_argument("--muestra", type=int, default=0, help="clasifica solo N registros aleatorios")
    args = ap.parse_args()

    cfg = configparser.ConfigParser()
    cfg.read(RAIZ / "config.cfg", encoding="utf-8")
    clave = cfg.get("claves", "openai_api_key", fallback="").strip()
    if not clave:
        sys.exit("Falta openai_api_key en config.cfg [claves]")
    cliente = OpenAI(api_key=clave)

    registros = json.loads(Path(args.entrada).read_text(encoding="utf-8"))
    salida = Path(args.salida)
    parcial = salida.with_suffix(".parcial.json")
    hecho = {}
    if parcial.exists() and not args.muestra:
        hecho = {int(k): tuple(v) for k, v in json.loads(parcial.read_text(encoding="utf-8")).items()}
        print(f"Reanudando: {len(hecho)} ya clasificados")

    indices = range(len(registros))
    if args.muestra:
        indices = random.Random(7).sample(list(indices), args.muestra)
    pendientes = [a_elemento(i, registros[i]) for i in indices
                  if i not in hecho and limpiar(registros[i].get("text"))]
    lotes = [pendientes[k:k + LOTE] for k in range(0, len(pendientes), LOTE)]
    print(f"{len(pendientes)} registros a clasificar en {len(lotes)} lotes con {MODELO}")

    candado = threading.Lock()
    tokens = [0, 0]
    with ThreadPoolExecutor(HILOS) as pool:
        futuros = [pool.submit(clasificar_lote, cliente, l) for l in lotes]
        for n, f in enumerate(as_completed(futuros), 1):
            res, uso = f.result()
            with candado:
                hecho.update(res)
                tokens[0] += uso.prompt_tokens
                tokens[1] += uso.completion_tokens
                if not args.muestra and (n % 20 == 0 or n == len(lotes)):
                    parcial.write_text(json.dumps(hecho), encoding="utf-8")
            if n % 20 == 0 or n == len(lotes):
                print(f"  {n}/{len(lotes)} lotes")

    coste = tokens[0] / 1e6 * 0.40 + tokens[1] / 1e6 * 1.60
    print(f"Tokens: {tokens[0]:,} entrada / {tokens[1]:,} salida (~{coste:.2f} $)")

    if args.muestra:
        for i in indices:
            s, c = hecho.get(i, (None, None))
            r = registros[i]
            print(f"[{r['brand']}/{r['platform']}/{r.get('rating')}] {s:>8} {c:<18} "
                  f"{limpiar(r.get('text'))[:110]!r}" if s else f"[{r['brand']}] (sin texto)")
        return

    for i, r in enumerate(registros):
        s, c = hecho.get(i, (None, None))
        r["sentiment"], r["category"] = s, c
    salida.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    parcial.unlink(missing_ok=True)
    print(f"Guardado {salida} ({len(registros)} registros, "
          f"{sum(1 for r in registros if r['sentiment'] is None)} sin texto -> null)")


if __name__ == "__main__":
    main()
