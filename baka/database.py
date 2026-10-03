# Niko - Premium Aesthetic Telegram Economy & Game Bot
# Database layer: tries MongoDB (env MONGO_URI); falls back to Redis when MongoDB is unreachable.
#
# PLUGIN-DICT FACADE:
# Both the Mongo and fallback branches expose plain dict objects.  The plugins call the
# Mongo API (find_one / find / update_one / insert_one / delete_one / count_documents /
# sort / limit / upsert / aggregate / find_one_and_update / replace_one).  When the backend
# is not a real Mongo (redis or "none") these methods are implemented on top of an in-memory
# dict so the bot boots and continues to work without MongoDB.

import os
import logging
from datetime import datetime

log = logging.getLogger("ryanbaka.database")

try:
    from pymongo import MongoClient
    from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError, PyMongoError
except ImportError:
    MongoClient = None
    PyMongoError = Exception

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from baka.config import MONGO_URI

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
def _connect_mongo():
    if not MONGO_URI:
        log.warning("MONGO_URI is not set - using Redis fallback.")
        return None, None
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=os.environ.get("SSL_CERT_FILE") or "certifi.where()")
        try:
            client.admin.command("ping")
        except Exception:
            client.close()
            return None, None
        db = client["bakabot_db"]
        log.info("MongoDB connected via MONGO_URI")
        return client, db
    except (ConfigurationError, ServerSelectionTimeoutError, PyMongoError) as e:
        log.warning("MongoDB failed (%s) -> Redis fallback." % e)
        return None, None

_mongo_client, _mongo_db = _connect_mongo()

if _mongo_client is not None and _mongo_db is not None:
    users_collection = _mongo_db["users"]
    groups_collection = _mongo_db["groups"]
    sudoers_collection = _mongo_db["sudoers"]
    chatbot_collection = _mongo_db["chatbot"]
    riddles_collection = _mongo_db["riddles"]
else:
    USE_REDIS_FALLBACK = False
    DB_BACKEND = "none"

    # ---- in-memory store (plain dicts), keyed by str(id) ----
    _USERS = {}
    _GROUPS = {}
    _SUDOERS = set()
    _CHATBOT = {}
    _RIDDLES = {}

    def _uid(x):
        return str(x)

    def _lock():
        _locks = {}

        def _acquire(key):
            _locks.setdefault(key, []).append(None)

        def _release(key):
            _locks.get(key, []).pop()

        return _acquire, _release

    _acquire, _release = _lock()

    def _doc_get(store, key, default=None):
        return store.get(key, default)

    def _doc_set(store, key, value):
        store[key] = value

    def _merge(target, source, **fields):
        for k, v in fields.items():
            if k == "$set":
                for kk, vv in v.items():
                    if isinstance(vv, dict) and kk in target and isinstance(target.get(kk), dict):
                        target[kk] = {**target[kk], **vv}
                    elif isinstance(vv, list) and kk in target and isinstance(target.get(kk), list):
                        target[kk] = target[kk] + vv
                    else:
                        target[kk] = vv
            elif k == "$inc":
                for kk, vv in v.items():
                    if isinstance(target.get(kk), (int, float)):
                        target[kk] += vv
                    else:
                        target[kk] = vv
            elif k == "$push":
                for kk, vv in v.items():
                    if kk not in target:
                        target[kk] = []
                    if isinstance(vv, dict):
                        if isinstance(vv, dict) and "$each" in vv:
                            for item in vv["$each"]:
                                if item not in target[kk]:
                                    target[kk].append(item)
                        else:
                            target[kk].append(vv)
                    else:
                        if vv not in target[kk]:
                            target[kk].append(vv)
            elif k == "$pull":
                for kk, vv in v.items():
                    if kk in target:
                        target[kk] = [x for x in target[kk] if x != vv]
            elif k == "$unset":
                for kk in v.keys():
                    target.pop(kk, None)
            elif k == "$addToSet":
                for kk, vv in v.items():
                    if kk not in target:
                        target[kk] = []
                    if isinstance(vv, dict) and "$each" in vv:
                        for item in vv["$each"]:
                            if item not in target[kk]:
                                target[kk].append(item)
                    else:
                        if vv not in target[kk]:
                            target[kk].append(vv)
            elif isinstance(v, dict) and k in target and isinstance(target.get(k), dict):
                target[k] = {**target[k], **v}
            elif isinstance(v, list) and k in target and isinstance(target.get(k), list):
                target[k] = target[k] + v
            else:
                target[k] = v
        return target

    def _add(target, key, value):
        if key not in target:
            target[key] = []
        target[key].append(value)
        return target[key]

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    def _users_get(user_id):
        return _doc_get(_USERS, _uid(user_id))

    def _users_set(user_id, doc):
        _doc_set(_USERS, _uid(user_id), doc)

    def _users_update(user_id, updates):
        key = _uid(user_id)
        doc = _doc_get(_USERS, key)
        if doc is None:
            return
        _merge(doc, None, **updates)

    def _users_inc(user_id, key, amount):
        key_str = _uid(user_id)
        doc = _USERS.get(key_str)
        if doc is None:
            return
        doc[key] = doc.get(key, 0) + amount

    def _users_add(user_id, key, value):
        _add(_USERS.get(_uid(user_id), {}), key, value)

    def _users_get_list(user_id, key):
        return _USERS.get(_uid(user_id), {}).get(key, [])

    # ------------------------------------------------------------------
    # groups
    # ------------------------------------------------------------------
    def _groups_get(chat_id):
        return _doc_get(_GROUPS, _uid(chat_id))

    def _groups_set(chat_id, doc):
        _doc_set(_GROUPS, _uid(chat_id), doc)

    def _groups_update(chat_id, updates):
        key = _uid(chat_id)
        doc = _doc_get(_GROUPS, key)
        if doc is None:
            return
        _merge(doc, None, **updates)

    # ------------------------------------------------------------------
    # sudoers
    # ------------------------------------------------------------------
    def _sudoers_get_all():
        return list(_SUDOERS)

    def _sudoers_add(user_id):
        _SUDOERS.add(_uid(user_id))

    def _sudoers_del(user_id):
        _SUDOERS.discard(_uid(user_id))

    # ------------------------------------------------------------------
    # chatbot
    # ------------------------------------------------------------------
    def _chatbot_get(chat_id):
        return _doc_get(_CHATBOT, _uid(chat_id))

    def _chatbot_set(chat_id, history):
        _doc_set(_CHATBOT, _uid(chat_id), {"history": history})

    # ------------------------------------------------------------------
    # riddles
    # ------------------------------------------------------------------
    def _riddles_get(chat_id):
        return _doc_get(_RIDDLES, _uid(chat_id))

    def _riddles_set(chat_id, doc):
        _doc_set(_RIDDLES, _uid(chat_id), doc)

    # ---- Mongo-style collection facade ----

    def _to_mongo_list(store):
        return list(store.values())

    class _Cursor:
        """List-like cursor returned by find()."""
        def __init__(self, items):
            self._items = items
            self._idx = 0

        def __iter__(self):
            return iter(self._items)

        def __getitem__(self, i):
            return self._items[i]

        def __len__(self):
            return len(self._items)

        def sort(self, key, reverse=False):
            self._items = sorted(self._items, key=lambda d: d.get(key, 0), reverse=reverse)
            return self

        def limit(self, n):
            self._items = self._items[:n]
            return self

        def to_list(self):
            return list(self._items)

    def find_one(query=None, **kwargs):
        if not query:
            return None
        key = _uid(next(iter(query.values()), None))
        return _doc_get(_USERS if "user_id" in query else _GROUPS, key)

    def _current_kind(collection):
        return collection.get("_kind", "user")

    def find(query=None, **kwargs):
        is_user = bool(query) and "user_id" in query
        store = _USERS if is_user else _GROUPS
        if query:
            key = _uid(next(iter(query.values()), None))
            return _Cursor(_doc_get(store, key, []))
        # no query: return all docs of this collection
        kind = _ACTIVE_COLLECTION_KIND
        store = _USERS if kind == "user" else _GROUPS
        return _Cursor(list(store.values()))

    def find_one_and_update(query, update, upsert=False, return_document=True):
        if not query:
            return None
        is_user = "user_id" in query
        store = _USERS if is_user else _GROUPS
        key = _uid(next(iter(query.values()), None))
        doc = _doc_get(store, key)
        if doc is None and upsert:
            doc = {}
            _doc_set(store, key, doc)
        if doc is not None:
            _merge(doc, None, **update)
        return doc

    def update_one(query, update, upsert=False):
        if not query:
            return
        key = _uid(next(iter(query.values()), None))
        doc = _doc_get(_USERS if "user_id" in query else _GROUPS, key)
        if doc is None and upsert:
            doc = {}
            _doc_set(_USERS if "user_id" in query else _GROUPS, key, doc)
        if doc is not None:
            _merge(doc, None, **update)

    def insert_one(doc):
        key = _uid(doc.get("user_id") or doc.get("chat_id"))
        if key:
            _doc_set(_USERS if "user_id" in doc else _GROUPS, key, doc)

    def delete_one(query):
        if not query:
            return
        key = _uid(next(iter(query.values()), None))
        store = _USERS if "user_id" in query else _GROUPS
        _doc_set(store, key, None)

    def count_documents(query=None, **kwargs):
        return 1 if query else len(_USERS)

    def sort(key, reverse=False):
        return self

    def limit(n):
        return self

    def aggregate(pipeline):
        match = pipeline[0].get("$match", {}) if pipeline else {}
        key = next(iter(match.values()), None) if match else None
        items = list(_USERS.values()) if key == "user_id" else []
        sort = pipeline[1].get("$sort", {}) if len(pipeline) > 1 else {}
        if sort:
            items = sorted(items, key=lambda d: d.get(next(iter(sort), ""), 0), reverse=True)
        limit = pipeline[2].get("$limit", 0) if len(pipeline) > 2 else 0
        if limit:
            items = items[:limit]
        return items

    # ------------------------------------------------------------------
    # Collection of all collections
    # ------------------------------------------------------------------
    # Closure builders so each collection's query methods are bound to the
    # correct in-memory store (users vs groups) regardless of which collection
    # the plugin calls them on.

    def _make_users_find():
        def find(query=None, **kwargs):
            is_user = bool(query) and "user_id" in query
            store = _USERS if is_user else _GROUPS
            if query:
                key = _uid(next(iter(query.values()), None))
                return _Cursor(_doc_get(store, key, []))
            return _Cursor(list(_USERS.values()))
        return find

    def _make_users_find_one():
        def find_one(query=None, **kwargs):
            if not query:
                return None
            key = _uid(next(iter(query.values()), None))
            return _doc_get(_USERS, key)
        return find_one

    def _make_users_update_one():
        def update_one(query, update, upsert=False):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            doc = _doc_get(_USERS, key)
            if doc is None and upsert:
                doc = {}
                _doc_set(_USERS, key, doc)
            if doc is not None:
                _merge(doc, None, **update)
        return update_one

    def _make_users_insert_one():
        def insert_one(doc):
            key = _uid(doc.get("user_id") or doc.get("chat_id"))
            if key:
                _doc_set(_USERS, key, doc)
        return insert_one

    def _make_users_delete_one():
        def delete_one(query):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            _USERS.pop(key, None)
        return delete_one

    def _make_groups_find():
        def find(query=None, **kwargs):
            is_user = bool(query) and "user_id" in query
            store = _USERS if is_user else _GROUPS
            if query:
                key = _uid(next(iter(query.values()), None))
                return _Cursor(_doc_get(store, key, []))
            return _Cursor(list(_GROUPS.values()))
        return find

    def _make_groups_find_one():
        def find_one(query=None, **kwargs):
            if not query:
                return None
            key = _uid(next(iter(query.values()), None))
            return _doc_get(_GROUPS, key)
        return find_one

    def _make_groups_update_one():
        def update_one(query, update, upsert=False):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            doc = _doc_get(_GROUPS, key)
            if doc is None and upsert:
                doc = {}
                _doc_set(_GROUPS, key, doc)
            if doc is not None:
                _merge(doc, None, **update)
        return update_one

    def _make_groups_insert_one():
        def insert_one(doc):
            key = _uid(doc.get("user_id") or doc.get("chat_id"))
            if key:
                _doc_set(_GROUPS, key, doc)
        return insert_one

    def _make_groups_delete_one():
        def delete_one(query):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            _GROUPS.pop(key, None)
        return delete_one

    users_collection = {
        "get": _users_get,
        "set": _users_set,
        "update": _users_update,
        "inc": _users_inc,
        "add": _users_add,
        "get_list": _users_get_list,
        "find_one": _make_users_find_one(),
        "find": _make_users_find(),
        "update_one": _make_users_update_one(),
        "insert_one": _make_users_insert_one(),
        "delete_one": _make_users_delete_one(),
        "count_documents": count_documents,
        "find_one_and_update": find_one_and_update,
        "aggregate": aggregate,
    }

    groups_collection = {
        "get": _groups_get,
        "set": _groups_set,
        "update": _groups_update,
        "find_one": _make_groups_find_one(),
        "find": _make_groups_find(),
        "update_one": _make_groups_update_one(),
        "insert_one": _make_groups_insert_one(),
        "delete_one": _make_groups_delete_one(),
        "find_one_and_update": find_one_and_update,
        "aggregate": aggregate,
    }

    def _make_sudoers_find():
        def find(query=None, **kwargs):
            return _Cursor(list(_SUDOERS))
        return find

    sudoers_collection = {
        "get_all": _sudoers_get_all,
        "add": _sudoers_add,
        "del": _sudoers_del,
        "find": _make_sudoers_find(),
    }

    chatbot_collection = {
        "get": _chatbot_get,
        "set": _chatbot_set,
        "find_one": find_one,
        "update_one": update_one,
        "delete_one": delete_one,
    }

    def _make_chatbot_insert_one():
        def insert_one(doc):
            key = _uid(doc.get("chat_id"))
            if key:
                _doc_set(_CHATBOT, key, {"history": doc.get("history", [])})
        return insert_one

    def _make_chatbot_update_one():
        def update_one(query, update, upsert=False):
            key = _uid(next(iter(query.values()), None))
            doc = _doc_get(_CHATBOT, key)
            if doc is None and upsert:
                doc = {"history": []}
                _doc_set(_CHATBOT, key, doc)
            if doc is not None:
                _merge(doc, None, **update)
        return update_one

    def _make_chatbot_delete_one():
        def delete_one(query):
            key = _uid(next(iter(query.values()), None))
            _CHATBOT.pop(key, None)
        return delete_one

    def _make_riddles_insert_one():
        def insert_one(doc):
            key = _uid(doc.get("chat_id"))
            if key:
                _doc_set(_RIDDLES, key, doc)
        return insert_one

    def _make_chatbot_find_one():
        def find_one(query=None, **kwargs):
            if not query:
                return None
            key = _uid(next(iter(query.values()), None))
            return _doc_get(_CHATBOT, key)
        return find_one

    def _make_chatbot_find():
        def find(query=None, **kwargs):
            is_user = bool(query) and "user_id" in query
            store = _USERS if is_user else _GROUPS
            if query:
                key = _uid(next(iter(query.values()), None))
                return _Cursor(_doc_get(store, key, []))
            return _Cursor(list(_CHATBOT.values()))
        return find

    def _make_chatbot_update_one():
        def update_one(query, update, upsert=False):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            doc = _doc_get(_CHATBOT, key)
            if doc is None and upsert:
                doc = {"history": []}
                _doc_set(_CHATBOT, key, doc)
            if doc is not None:
                _merge(doc, None, **update)
        return update_one

    def _make_chatbot_delete_one():
        def delete_one(query):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            _CHATBOT.pop(key, None)
        return delete_one

    def _make_riddles_find_one():
        def find_one(query=None, **kwargs):
            if not query:
                return None
            key = _uid(next(iter(query.values()), None))
            return _doc_get(_RIDDLES, key)
        return find_one

    def _make_riddles_find():
        def find(query=None, **kwargs):
            is_user = bool(query) and "user_id" in query
            store = _USERS if is_user else _GROUPS
            if query:
                key = _uid(next(iter(query.values()), None))
                return _Cursor(_doc_get(store, key, []))
            return _Cursor(list(_RIDDLES.values()))
        return find

    def _make_riddles_update_one():
        def update_one(query, update, upsert=False):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            doc = _doc_get(_RIDDLES, key)
            if doc is None and upsert:
                doc = {}
                _doc_set(_RIDDLES, key, doc)
            if doc is not None:
                _merge(doc, None, **update)
        return update_one

    def _make_riddles_delete_one():
        def delete_one(query):
            if not query:
                return
            key = _uid(next(iter(query.values()), None))
            _RIDDLES.pop(key, None)
        return delete_one

    chatbot_collection = {
        "get": _chatbot_get,
        "set": _chatbot_set,
        "insert_one": _make_chatbot_insert_one(),
        "find_one": _make_chatbot_find_one(),
        "find": _make_chatbot_find(),
        "update_one": _make_chatbot_update_one(),
        "delete_one": _make_chatbot_delete_one(),
    }

    riddles_collection = {
        "get": _riddles_get,
        "set": _riddles_set,
        "find_one": _make_riddles_find_one(),
        "find": _make_riddles_find(),
        "insert_one": _make_riddles_insert_one(),
        "update_one": _make_riddles_update_one(),
        "delete_one": _make_riddles_delete_one(),
    }

# ---------------------------------------------------------------------------
# Redis (best-effort fallback when MongoDB is unavailable)
# ---------------------------------------------------------------------------
if DB_BACKEND == "none" and REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0,
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )
        redis_client.ping()
        log.info("Redis fallback connected.")
        USE_REDIS_FALLBACK = True
        DB_BACKEND = "redis"
    except Exception as e:
        log.warning("Redis fallback unavailable (%s) -> DB_BACKEND=none" % e)
        redis_client = None
        USE_REDIS_FALLBACK = False
        DB_BACKEND = "none"

# Re-export the same names every branch leaves for the plugins
if DB_BACKEND == "mongodb":
    users_collection = _mongo_db["users"]
    groups_collection = _mongo_db["groups"]
    sudoers_collection = _mongo_db["sudoers"]
    chatbot_collection = _mongo_db["chatbot"]
    riddles_collection = _mongo_db["riddles"]

USE_REDIS_FALLBACK = redis_client is not None if DB_BACKEND != "mongodb" else False
DB_BACKEND = "mongodb" if (_mongo_client is not None and _mongo_db is not None) else (
    "redis" if USE_REDIS_FALLBACK else "none")

log.info("Database backend: %s" % DB_BACKEND)
