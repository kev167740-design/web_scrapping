"""
Convierte los resultados de cada red (cada actor devuelve su propia estructura)
a un esquema común, y calcula un id estable para evitar duplicados.

Esquema común (union.json):
    brand, platform, record_type (comment / reply / review), id, parent_id,
    source_url (post, vídeo, lugar o empresa), source_name, url, text, title,
    rating, author, created_at (ISO UTC), likes, replies, language, owner_reply
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

CAMPOS = ["brand", "platform", "record_type", "id", "parent_id", "source_url", "source_name",
          "url", "text", "title", "rating", "author", "created_at", "likes", "replies",
          "language", "owner_reply"]


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def primero(item: dict, *claves):
    """Primer valor no vacío entre varias claves (admite rutas como 'author.username')."""
    for clave in claves:
        valor = item
        for parte in clave.split("."):
            valor = valor.get(parte) if isinstance(valor, dict) else None
            if valor is None:
                break
        if valor not in (None, "", [], {}):
            return valor
    return None


def texto(v) -> str:
    return "" if v is None else str(v).strip()


def numero(v) -> int | None:
    """'1.3K' -> 1300, '2,5 mil' -> 2500, '1,234' -> 1234."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower().replace(" ", "")
    mult = 1
    for suf, m in (("mil", 1_000), ("k", 1_000), ("m", 1_000_000)):
        if s.endswith(suf):
            s, mult = s[: -len(suf)], m
            break
    if mult > 1:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "").replace(".", "")
    try:
        return int(float(s) * mult)
    except ValueError:
        return None


def fecha_iso(v) -> str | None:
    """Convierte fechas ISO, epoch o formato de Twitter a 'AAAA-MM-DDTHH:MM:SSZ' (UTC)."""
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
            n = float(v)
            dt = datetime.fromtimestamp(n / 1000 if n > 1e11 else n, tz=timezone.utc)
        else:
            s = str(v).strip()
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")   # formato de Twitter
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OSError, OverflowError):
        return str(v)


def huella(item: dict) -> str:
    return hashlib.sha1(json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                        .encode("utf-8")).hexdigest()[:20]


def registro(**campos) -> dict:
    r = {c: campos.get(c) for c in CAMPOS}
    r["text"] = texto(r["text"])
    if not r["id"]:
        base = {k: r[k] for k in ("platform", "source_url", "author", "created_at", "text", "rating")}
        r["id"] = "h_" + huella(base)
    r["id"] = str(r["id"])
    if r["parent_id"] is not None:
        r["parent_id"] = str(r["parent_id"])
    return r


# ---------------------------------------------------------------------
# Un conversor por red: reciben un item crudo y devuelven 0, 1 o varios registros
# ---------------------------------------------------------------------

def _tiktok(it: dict):
    tipo = it.get("record_type", "comment")
    if tipo not in ("comment", "reply"):
        return
    reply_id = it.get("reply_id")
    if tipo == "reply" and reply_id not in (None, "", "0", 0):
        id_, padre = reply_id, primero(it, "parent_comment_id", "comment_id")
    else:
        id_, padre = it.get("comment_id"), it.get("parent_comment_id") or None
    yield registro(platform="tiktok", record_type=tipo, id=id_, parent_id=padre,
                   source_url=primero(it, "video_url"), url=None, text=it.get("text"),
                   author=primero(it, "author_unique_id", "author_nickname"),
                   created_at=fecha_iso(primero(it, "create_time", "create_time_epoch")),
                   likes=numero(it.get("like_count")), replies=numero(it.get("reply_count")),
                   language=it.get("language") or None)


def _facebook(it: dict):
    padre = primero(it, "replyToCommentId", "parentComment.id")
    profundidad = numero(it.get("threadingDepth")) or 0
    yield registro(platform="facebook", record_type="reply" if (padre or profundidad > 0) else "comment",
                   id=primero(it, "commentId", "id"), parent_id=padre,
                   source_url=primero(it, "inputUrl", "facebookUrl", "postUrl", "url"),
                   url=primero(it, "commentUrl"), text=primero(it, "text"),
                   author=primero(it, "profileName", "author.name"),
                   created_at=fecha_iso(primero(it, "date", "createdAt", "timestamp")),
                   likes=numero(primero(it, "likesCount", "likes")),
                   replies=numero(primero(it, "commentsCount", "repliesCount")))


def _instagram(it: dict, padre: dict | None = None):
    fuente = primero(it, "postUrl", "inputUrl", "url") or (padre or {}).get("_fuente")
    yield registro(platform="instagram", record_type="reply" if padre else "comment",
                   id=primero(it, "id", "pk"), parent_id=(padre or {}).get("id"),
                   source_url=fuente, url=primero(it, "commentUrl"), text=primero(it, "text"),
                   author=primero(it, "ownerUsername", "owner.username"),
                   created_at=fecha_iso(primero(it, "timestamp", "createdAt")),
                   likes=numero(primero(it, "likesCount", "likes")),
                   replies=numero(primero(it, "repliesCount")))
    for resp in it.get("replies") or []:
        if isinstance(resp, dict):
            yield from _instagram(resp, padre={"id": primero(it, "id", "pk"), "_fuente": fuente})


def _x(it: dict):
    if texto(it.get("resultType")).lower() in ("post", "original", "originalpost", "run", "runrecord", "summary"):
        return
    if not primero(it, "text", "fullText") and not it.get("id"):
        return   # registros de control del actor
    profundidad = numero(it.get("depth"))
    directa = it.get("isDirectReply")
    tipo = "comment" if (directa is True or (directa is None and (profundidad or 1) <= 1)) else "reply"
    raiz = primero(it, "rootTweetId", "conversationId", "sourceTweetId")
    yield registro(platform="x", record_type=tipo, id=primero(it, "id", "tweetId"),
                   parent_id=primero(it, "parentReplyId", "inReplyToId", "inReplyToStatusId"),
                   source_url=primero(it, "sourceTarget") or (f"https://x.com/i/status/{raiz}" if raiz else None),
                   url=primero(it, "url", "twitterUrl"), text=primero(it, "text", "fullText"),
                   author=primero(it, "authorUsername", "author.username", "author.userName"),
                   created_at=fecha_iso(primero(it, "createdAt")),
                   likes=numero(primero(it, "likeCount", "favoriteCount")),
                   replies=numero(primero(it, "replyCount")), language=primero(it, "lang"))


def _youtube(it: dict):
    yield registro(platform="youtube", record_type="reply" if it.get("is_reply") else "comment",
                   id=it.get("comment_id"), parent_id=it.get("parent_id"),
                   source_url=it.get("video_url"), source_name=it.get("video_title"),
                   url=it.get("comment_url"), text=it.get("text"), author=it.get("author"),
                   created_at=fecha_iso(it.get("published_at")), likes=numero(it.get("like_count")),
                   replies=numero(it.get("reply_count")))


def _google_reviews(it: dict):
    yield registro(platform="google_reviews", record_type="review",
                   id=primero(it, "reviewId", "id"),
                   source_url=primero(it, "url", "placeUrl", "inputUrl"),
                   source_name=primero(it, "title", "placeName", "name_place"),
                   url=primero(it, "reviewUrl"), text=primero(it, "text", "textTranslated", "reviewText"),
                   rating=numero(primero(it, "stars", "rating")),
                   author=primero(it, "name", "reviewerName"),
                   created_at=fecha_iso(primero(it, "publishedAtDate", "publishedAt", "date")),
                   likes=numero(primero(it, "likesCount")),
                   language=primero(it, "originalLanguage", "language"),
                   owner_reply=primero(it, "responseFromOwnerText", "ownerResponse"))


def _trustpilot(it: dict):
    dominio = primero(it, "companyDomain")
    yield registro(platform="trustpilot", record_type="review",
                   id=primero(it, "reviewId", "id"),
                   source_url=primero(it, "companyUrl") or (f"https://www.trustpilot.com/review/{dominio}" if dominio else None),
                   source_name=primero(it, "companyName", "companyDomain"),
                   url=primero(it, "reviewUrl", "url"), text=primero(it, "text", "body"),
                   title=primero(it, "title"), rating=numero(primero(it, "rating", "stars")),
                   author=primero(it, "reviewerName", "consumerName", "author"),
                   created_at=fecha_iso(primero(it, "publishedDate", "date", "createdAt")),
                   language=primero(it, "language"), owner_reply=primero(it, "replyText"))


CONVERSORES = {
    "tiktok": _tiktok, "facebook": _facebook, "instagram": _instagram, "x": _x,
    "youtube": _youtube, "google_reviews": _google_reviews, "trustpilot": _trustpilot,
}


def normalizar(red: str, item: dict, marca: str) -> list[dict]:
    registros = list(CONVERSORES[red](item)) if isinstance(item, dict) else []
    for r in registros:
        r["brand"] = marca
    return registros


def clave_item(red: str, item: dict) -> str:
    """Id estable de un item crudo, para no guardar duplicados al acumular."""
    registros = list(CONVERSORES[red](item)) if isinstance(item, dict) else []
    if registros and not registros[0]["id"].startswith("h_"):
        return f"{registros[0]['record_type']}:{registros[0]['id']}"
    return "h_" + huella(item)
