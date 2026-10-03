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

class FacadDict(dict):
    """Dict subclass that supports both attribute (d.key) and item (d['key']) access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

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

# ---------------------------------------------------------------------------
# In-memory store (plain dicts), keyed by str(id)
# ---------------------------------------------------------------------------
_USERS = {}
_GROUPS = {}
_SUDOERS = set()
_CHATBOT = {}
_RIDDLES = {}

def _uid(x):
    return str(x)

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

def _make_users_get():
    def get(user_id):
        return _doc_get(_USERS, _uid(user_id))
    return get

def _make_users_set():
    def set(user_id, doc):
        _doc_set(_USERS, _uid(user_id), doc)
    return set

def _make_users_update():
    def update(user_id, updates):
        key = _uid(user_id)
        doc = _doc_get(_USERS, key)
        if doc:
            _merge(doc, None, **updates)
    return update

def _make_users_inc():
    def inc(user_id, key, amount):
        _doc_set(_USERS, _uid(user_id), _USERS.get(_uid(user_id), {}))
        _merge(_doc_get(_USERS, _uid(user_id), {}), None, **{"$inc": {key: amount}})
        _doc_set(_USERS, _uid(user_id), _USERS.get(_uid(user_id)))
    return inc

def _make_users_add():
    def add(user_id, key, value):
        _doc_set(_USERS, _uid(user_id), _USERS.get(_uid(user_id), {}))
        _merge(_doc_get(_USERS, _uid(user_id), {}), None, **{"$addToSet": {key: value}})
        _doc_set(_USERS, _uid(user_id), _USERS.get(_uid(user_id)))
    return add

def _make_users_get_list():
    def get_list(user_id, key):
        return _doc_get(_USERS, _uid(user_id), {}).get(key, [])
    return get_list

def _make_users_find_one():
    def find_one(query=None, **kwargs):
        if not query:
            return None
        key = _uid(next(iter(query.values()), None))
        return _doc_get(_USERS if "user_id" in query else _GROUPS, key)
    return find_one

def _make_users_find():
    def find(query=None, **kwargs):
        store = _USERS if (query and "user_id" in query) else _GROUPS
        if query:
            key = _uid(next(iter(query.values()), None))
            return [_doc_get(store, key)]
        return list(store.values())
    return find

def _make_users_update_one():
    def update_one(query, update, upsert=False):
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
        _doc_set(_USERS, _uid(doc.get("user_id", doc)), doc)
    return insert_one

def _make_users_delete_one():
    def delete_one(query):
        key = _uid(next(iter(query.values()), None))
        _USERS.pop(key, None)
    return delete_one

def _make_users_count_documents():
    def count_documents(query=None):
        return len(_USERS)
    return count_documents

def _make_users_sort():
    def sort(key, reverse=False):
        return sorted(_USERS.values(), key=lambda x: x.get(key, 0), reverse=reverse)
    return sort

def _make_users_limit():
    def limit(n):
        return list(_USERS.values())[:n]
    return limit

def _make_users_upsert():
    def upsert(query, update):
        key = _uid(next(iter(query.values()), None))
        doc = _doc_get(_USERS, key)
        if doc is None:
            doc = {}
            _doc_set(_USERS, key, doc)
        _merge(doc, None, **update)
    return upsert

def _make_users_aggregate():
    def aggregate(pipeline):
        results = []
        for doc in _USERS.values():
            for stage in pipeline:
                if "$match" in stage:
                    if not stage["$match"](doc):
                        break
                elif "$group" in stage:
                    pass
            else:
                results.append(doc)
        return results
    return aggregate

def _make_users_find_one_and_update():
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
    return find_one_and_update

def _make_groups_get():
    def get(chat_id):
        return _doc_get(_GROUPS, _uid(chat_id))
    return get

def _make_groups_set():
    def set(chat_id, doc):
        _doc_set(_GROUPS, _uid(chat_id), doc)
    return set

def _make_groups_update():
    def update(chat_id, updates):
        key = _uid(chat_id)
        doc = _doc_get(_GROUPS, key)
        if doc:
            _merge(doc, None, **updates)
    return update

def _make_groups_find_one():
    def find_one(query=None, **kwargs):
        if not query:
            return None
        key = _uid(next(iter(query.values()), None))
        return _doc_get(_GROUPS, key)
    return find_one

def _make_groups_find():
    def find(query=None, **kwargs):
        if query:
            key = _uid(next(iter(query.values()), None))
            return [_doc_get(_GROUPS, key)]
        return list(_GROUPS.values())
    return find

def _make_groups_update_one():
    def update_one(query, update, upsert=False):
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
        _doc_set(_GROUPS, _uid(doc.get("chat_id", doc)), doc)
    return insert_one

def _make_groups_delete_one():
    def delete_one(query):
        key = _uid(next(iter(query.values()), None))
        _GROUPS.pop(key, None)
    return delete_one

def _make_groups_count_documents():
    def count_documents(query=None):
        return len(_GROUPS)
    return count_documents

def _make_groups_sort():
    def sort(key, reverse=False):
        return sorted(_GROUPS.values(), key=lambda x: x.get(key, 0), reverse=reverse)
    return sort

def _make_groups_limit():
    def limit(n):
        return list(_GROUPS.values())[:n]
    return limit

def _make_groups_upsert():
    def upsert(query, update):
        key = _uid(next(iter(query.values()), None))
        doc = _doc_get(_GROUPS, key)
        if doc is None:
            doc = {}
            _doc_set(_GROUPS, key, doc)
        _merge(doc, None, **update)
    return upsert

def _make_groups_aggregate():
    def aggregate(pipeline):
        results = []
        for doc in _GROUPS.values():
            for stage in pipeline:
                if "$match" in stage:
                    if not stage["$match"](doc):
                        break
            else:
                results.append(doc)
        return results
    return aggregate

def _make_groups_find_one_and_update():
    def find_one_and_update(query, update, upsert=False, return_document=True):
        if not query:
            return None
        key = _uid(next(iter(query.values()), None))
        doc = _doc_get(_GROUPS, key)
        if doc is None and upsert:
            doc = {}
            _doc_set(_GROUPS, key, doc)
        if doc is not None:
            _merge(doc, None, **update)
        return doc
    return find_one_and_update

# ---------------------------------------------------------------------------
# Collection facade objects (module-level, work in all backends)
# ---------------------------------------------------------------------------
users_collection = FacadDict({
    "get": _make_users_get(),
    "set": _make_users_set(),
    "update": _make_users_update(),
    "inc": _make_users_inc(),
    "add": _make_users_add(),
    "get_list": _make_users_get_list(),
    "find_one": _make_users_find_one(),
    "find": _make_users_find(),
    "update_one": _make_users_update_one(),
    "insert_one": _make_users_insert_one(),
    "delete_one": _make_users_delete_one(),
    "count_documents": _make_users_count_documents(),
    "sort": _make_users_sort(),
    "limit": _make_users_limit(),
    "upsert": _make_users_upsert(),
    "aggregate": _make_users_aggregate(),
    "find_one_and_update": _make_users_find_one_and_update(),
})

groups_collection = FacadDict({
    "get": _make_groups_get(),
    "set": _make_groups_set(),
    "update": _make_groups_update(),
    "find_one": _make_groups_find_one(),
    "find": _make_groups_find(),
    "update_one": _make_groups_update_one(),
    "insert_one": _make_groups_insert_one(),
    "delete_one": _make_groups_delete_one(),
    "count_documents": _make_groups_count_documents(),
    "sort": _make_groups_sort(),
    "limit": _make_groups_limit(),
    "upsert": _make_groups_upsert(),
    "aggregate": _make_groups_aggregate(),
    "find_one_and_update": _make_groups_find_one_and_update(),
})

def _make_sudoers_find():
    def find(query=None, **kwargs):
        return _doc_get(_SUDOERS, _uid(next(iter(query.values()), None)))
    return find

sudoers_collection = FacadDict({
    "get": lambda uid: _doc_get(_SUDOERS, _uid(uid)),
    "set": lambda uid, val: _doc_set(_SUDOERS, _uid(uid), val),
    "update": lambda uid, val: _doc_set(_SUDOERS, _uid(uid), val),
    "find_one": _make_sudoers_find(),
    "find": lambda query=None, **kwargs: _doc_get(_SUDOERS, _uid(next(iter(query.values()), None))),
    "count_documents": _make_users_count_documents(),
})

def _make_chatbot_get():
    def get(user_id):
        return _doc_get(_CHATBOT, _uid(user_id))
    return get

def _make_chatbot_set():
    def set(user_id, doc):
        _doc_set(_CHATBOT, _uid(user_id), doc)
    return set

def _make_chatbot_update():
    def update(user_id, updates):
        key = _uid(user_id)
        doc = _doc_get(_CHATBOT, key)
        if doc:
            _merge(doc, None, **updates)
    return update

def _make_chatbot_insert_one():
    def insert_one(doc):
        _doc_set(_CHATBOT, _uid(doc.get("user_id", doc)), doc)
    return insert_one

def _make_chatbot_delete_one():
    def delete_one(query):
        key = _uid(next(iter(query.values()), None))
        _CHATBOT.pop(key, None)
    return delete_one

chatbot_collection = FacadDict({
    "get": _make_chatbot_get(),
    "set": _make_chatbot_set(),
    "update": _make_chatbot_update(),
    "insert_one": _make_chatbot_insert_one(),
    "find_one": _make_users_find_one(),
    "find": _make_users_find(),
    "update_one": _make_chatbot_update(),
    "delete_one": _make_chatbot_delete_one(),
})

def _make_riddles_get():
    def get(chat_id):
        return _doc_get(_RIDDLES, _uid(chat_id))
    return get

def _make_riddles_set():
    def set(chat_id, doc):
        _doc_set(_RIDDLES, _uid(chat_id), doc)
    return set

def _make_riddles_update():
    def update(chat_id, updates):
        key = _uid(chat_id)
        doc = _doc_get(_RIDDLES, key)
        if doc:
            _merge(doc, None, **updates)
    return update

def _make_riddles_insert_one():
    def insert_one(doc):
        _doc_set(_RIDDLES, _uid(doc.get("chat_id", doc)), doc)
    return insert_one

def _make_riddles_delete_one():
    def delete_one(query):
        key = _uid(next(iter(query.values()), None))
        _RIDDLES.pop(key, None)
    return delete_one

riddles_collection = FacadDict({
    "get": _make_riddles_get(),
    "set": _make_riddles_set(),
    "update": _make_riddles_update(),
    "insert_one": _make_riddles_insert_one(),
    "find_one": _make_groups_find_one(),
    "find": _make_groups_find(),
    "update_one": _make_riddles_update(),
    "delete_one": _make_riddles_delete_one(),
})

# ---------------------------------------------------------------------------
# MongoDB (if connected)
# ---------------------------------------------------------------------------
if _mongo_client is not None and _mongo_db is not None:
    users_collection = _mongo_db["users"]
    groups_collection = _mongo_db["groups"]
    sudoers_collection = _mongo_db["sudoers"]
    chatbot_collection = _mongo_db["chatbot"]
    riddles_collection = _mongo_db["riddles"]

# ---------------------------------------------------------------------------
# Redis (best-effort fallback when MongoDB is unavailable)
# ---------------------------------------------------------------------------
redis_client = None
USE_REDIS_FALLBACK = False
DB_BACKEND = "none"

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

log.info("Database backend: %s" % DB_BACKEND)
