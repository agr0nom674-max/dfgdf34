"""Мост между приложением и библиотекой netschoolpy (https://pypi.org/project/netschoolpy/).
Все вызовы идут через один постоянный event loop, чтобы сессия и keep-alive библиотеки жили между запросами."""
import asyncio
import json
import threading
from datetime import date, timedelta

import netschoolpy
from netschoolpy import NetSchool

_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()
_ns = None
_creds = None

MESSAGES = {
    "InvalidCredentials": "Неверный логин или пароль",
    "AccountLocked": "Вход временно заблокирован из-за частых попыток. Подождите и попробуйте позже",
    "SchoolNotFound": "Школа не найдена. Проверьте название (как на странице входа)",
    "ServerUnavailable": "Сервер школы сейчас недоступен. Попробуйте позже",
    "SessionExpired": "Сессия истекла, войдите снова",
    "MFAError": "Нужен второй фактор входа, он не поддерживается",
}


def _run(coro, timeout=90):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout)


def _g(obj, *names, default=""):
    for n in names:
        v = getattr(obj, n, None)
        if v not in (None, ""):
            return v
    return default


def _hhmm(v):
    return v.strftime("%H:%M") if hasattr(v, "strftime") else str(v)


def _mark(a):
    m = getattr(a, "mark", None)
    if m is None:
        return None
    m = getattr(m, "mark", m)          # на случай, если оценка вложена в объект
    try:
        return int(m) if m else None
    except (TypeError, ValueError):
        return None


def _to_json(diary):
    days = []
    for d in _g(diary, "schedule", default=[]):
        lessons = []
        for l in _g(d, "lessons", default=[]):
            tasks = [{"text": str(_g(a, "content", "comment")), "mark": _mark(a), "type": str(_g(a, "type"))}
                     for a in _g(l, "assignments", default=[])]
            lessons.append({"number": _g(l, "number", default=0), "start": _hhmm(_g(l, "start")),
                            "end": _hhmm(_g(l, "end")), "subject": str(_g(l, "subject")),
                            "room": str(_g(l, "room")), "assignments": tasks})
        days.append({"date": str(_g(d, "day"))[:10], "lessons": lessons})
    return {"days": days}


def _fill(data, start):
    """Пн–Сб всегда присутствуют; дни без уроков пустые."""
    by = {d["date"]: d for d in data["days"]}
    out = []
    for i in range(6):
        k = (start + timedelta(days=i)).isoformat()
        out.append(by.get(k, {"date": k, "lessons": []}))
    return {"days": out}


async def _close():
    global _ns
    if _ns is not None:
        try:
            await _ns.__aexit__(None, None, None)
        except Exception:
            pass
        _ns = None


async def _login(url, user, password, school):
    global _ns, _creds
    await _close()
    ns = NetSchool(url)
    await ns.__aenter__()
    try:
        await ns.login(user, password, school)
    except BaseException:
        await ns.__aexit__(None, None, None)
        raise
    _ns = ns
    _creds = (url, user, password, school)      # только в памяти; нужен для автоматического повторного входа


async def _diary(start, end):
    try:
        return _fill(_to_json(await _ns.diary(start, end)), start)
    except netschoolpy.SessionExpired:
        if not _creds:
            raise
        await _login(*_creds)
        return _fill(_to_json(await _ns.diary(start, end)), start)


def handle(method, args_json):
    """Единая точка входа из Kotlin. Всегда возвращает JSON-строку {ok, data|error}."""
    try:
        a = json.loads(args_json or "{}")
        if method == "login":
            _run(_login(a["url"], a["user"], a["password"], a["school"]))
            data = True
        elif method == "diary":
            if _ns is None:
                raise netschoolpy.SessionExpired("not logged in")
            data = _run(_diary(date.fromisoformat(a["start"]), date.fromisoformat(a["end"])))
        elif method == "logout":
            _run(_close())
            data = True
        else:
            raise ValueError("unknown method " + method)
        return json.dumps({"ok": True, "data": data}, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        kind = type(e).__name__
        text = MESSAGES.get(kind) or (str(e) or kind)
        return json.dumps({"ok": False, "error": text, "kind": kind}, ensure_ascii=False)
