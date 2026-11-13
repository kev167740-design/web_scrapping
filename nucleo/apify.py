"""Lanza un actor de Apify y devuelve los resultados de su dataset."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from nucleo.config import clave, seccion
from nucleo.marcas import fail


def _campo(obj, snake: str, camel: str):
    """Lee un campo de un dict (JSON) o de un modelo del cliente de Apify."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(camel, obj.get(snake))
    return getattr(obj, snake, None)


def mostrar_estimacion(max_resultados: int, precio_1000: float, max_cost: float,
                       extra: float = 0.0) -> None:
    est = max_resultados / 1000 * precio_1000 + extra
    print(f"Máximo posible: {max_resultados:,} resultados ≈ ${est:.2f} (aprox.)  ·  "
          f"tope de gasto: ${max_cost:.2f}")


def ejecutar_actor(actor_id: str, run_input: dict, max_cost: float) -> tuple[list[dict], dict]:
    """Ejecuta el actor, espera a que termine y devuelve (items, info)."""
    try:
        from apify_client import ApifyClient
    except ImportError:
        fail("Falta instalar dependencias:  pip install -r requirements.txt")

    token = clave("apify_token", "APIFY_TOKEN")
    minutos = seccion("general").entero("tiempo_maximo_min")
    client = ApifyClient(token)
    print(f"▶ Ejecutando {actor_id} (tope ${max_cost:.2f}, máx. {minutos} min). Esperando...")
    try:
        run = client.actor(actor_id).call(
            run_input=run_input,
            max_total_charge_usd=Decimal(str(round(max_cost, 4))),
            run_timeout=timedelta(minutes=minutos),
            logger=None,
        )
    except Exception as e:  # errores de la API de Apify: se muestra el mensaje real
        codigo = getattr(e, "status_code", None)
        tipo = getattr(e, "type", None) or ""
        mensaje = getattr(e, "message", None) or str(e)
        bajo = f"{tipo} {mensaje}".lower()
        if codigo == 401 or "token" in bajo and ("invalid" in bajo or "unauthorized" in bajo):
            pista = "El token de Apify no es válido. Revisa apify_token en config.cfg."
        elif codigo == 404 and "build" in bajo:
            pista = "El actor no tiene una versión publicada utilizable. Prueba más tarde o usa otro actor."
        elif codigo == 404:
            pista = f"Comprueba que el actor existe y está bien escrito en config.cfg: https://apify.com/{actor_id}"
        elif codigo == 400 or "invalid-input" in bajo or "input" in bajo and "valid" in bajo:
            pista = "Algún parámetro de config.cfg no es válido para este actor (ver el mensaje de arriba)."
        elif codigo in (402, 403) or "credit" in bajo or "limit" in bajo:
            pista = ("Puede ser falta de crédito este mes, un límite de uso, o que el actor necesite "
                     "permisos especiales (ábrelo una vez en la consola de Apify).")
        else:
            pista = ""
        fail(f"Apify respondió con un error{f' (HTTP {codigo})' if codigo else ''}: {mensaje}"
             + (f"\n   Tipo: {tipo}" if tipo else "")
             + (f"\n   → {pista}" if pista else ""))

    if run is None:
        fail("Apify no devolvió información de la ejecución.")

    status = _campo(run, "status", "status")
    status = getattr(status, "value", status)
    run_id = _campo(run, "id", "id")
    dataset_id = _campo(run, "default_dataset_id", "defaultDatasetId")
    url = f"https://console.apify.com/view/runs/{run_id}"
    print(f"  Estado: {status}  ·  log: {url}")
    if status != "SUCCEEDED":
        print("  ⚠️  La ejecución no terminó bien; se guarda lo que haya devuelto. "
              "Revisa el log en el enlace de arriba.")

    items = list(client.dataset(dataset_id).iterate_items()) if dataset_id else []
    demo = sum(1 for i in items if isinstance(i, dict) and i.get("demo") is True)
    if demo:
        print(f"  ⚠️  {demo} resultados son de DEMOSTRACIÓN (datos falsos): este actor limita el "
              f"plan gratuito. Se descartan.")
        items = [i for i in items if not (isinstance(i, dict) and i.get("demo") is True)]
    return items, {"run_id": run_id, "estado": status}
