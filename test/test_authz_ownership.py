# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prove-it tests for server-side ownership authorization (Vuln #2).

Each mutate/delete path must reject a caller whose *server-derived* identity does
not match the stored document owner, and must still allow the true owner. These
tests FAIL against the pre-fix code (the mutation succeeds regardless of owner)
and PASS once the ``common.authz`` ownership checks are in place.

Firestore is faked in-process so the tests never touch a real backend.
"""

# ruff: noqa: D101, D102, D103, S101

import datetime
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import authz


# --------------------------------------------------------------------------- #
# In-process Firestore fake
# --------------------------------------------------------------------------- #
class FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class FakeDocRef:
    def __init__(self, store, doc_id):
        self._store = store
        self.id = doc_id
        self.deleted = False

    def get(self):
        return FakeSnapshot(self._store.get(self.id))

    def update(self, updates):
        if self.id not in self._store:
            raise KeyError(f"no such document {self.id}")
        self._store[self.id].update(updates)

    def set(self, data, merge=False):
        if merge and self.id in self._store:
            self._store[self.id].update(data)
        else:
            self._store[self.id] = dict(data)

    def delete(self):
        self.deleted = True
        self._store.pop(self.id, None)


class FakeCollection:
    def __init__(self, db, store):
        self._db = db
        self._store = store

    def document(self, doc_id=None):
        if doc_id is None:
            self._db.auto += 1
            doc_id = f"auto-{self._db.auto}"
        ref = FakeDocRef(self._store, doc_id)
        self._db.refs.append(ref)
        return ref

    def add(self, data):
        self._db.auto += 1
        doc_id = f"auto-{self._db.auto}"
        self._store[doc_id] = dict(data)
        return (None, FakeDocRef(self._store, doc_id))


class FakeDB:
    def __init__(self):
        self.collections = {}
        self.refs = []
        self.auto = 0

    def collection(self, name):
        store = self.collections.setdefault(name, {})
        return FakeCollection(self, store)

    def seed(self, collection, doc_id, data):
        self.collections.setdefault(collection, {})[doc_id] = dict(data)


@pytest.fixture
def fake_db():
    return FakeDB()


def _set_server_identity(monkeypatch, email):
    """Force the server-derived caller identity used by ``common.authz``."""
    monkeypatch.setattr(authz, "get_current_user_email", lambda: email)


# --------------------------------------------------------------------------- #
# 1. update_template  (common/prompt_template_service.py)
# --------------------------------------------------------------------------- #
def test_update_template_rejects_non_owner(monkeypatch, fake_db):
    import common.prompt_template_service as svc

    monkeypatch.setattr(svc, "db", fake_db)
    fake_db.seed(
        "prompt_templates",
        "tmpl_alice",
        {"prompt": "original", "attribution": "alice@example.com"},
    )
    _set_server_identity(monkeypatch, "attacker@evil.com")

    with pytest.raises(PermissionError):
        svc.PromptTemplateService().update_template(
            "tmpl_alice", {"prompt": "PWNED"}
        )

    # The document must be untouched.
    assert fake_db.collections["prompt_templates"]["tmpl_alice"]["prompt"] == "original"


def test_update_template_allows_owner(monkeypatch, fake_db):
    import common.prompt_template_service as svc

    monkeypatch.setattr(svc, "db", fake_db)
    fake_db.seed(
        "prompt_templates",
        "tmpl_alice",
        {"prompt": "original", "attribution": "alice@example.com"},
    )
    _set_server_identity(monkeypatch, "alice@example.com")

    svc.PromptTemplateService().update_template("tmpl_alice", {"prompt": "updated"})

    assert fake_db.collections["prompt_templates"]["tmpl_alice"]["prompt"] == "updated"


def test_update_template_forbids_attribution_overwrite(monkeypatch, fake_db):
    import common.prompt_template_service as svc

    monkeypatch.setattr(svc, "db", fake_db)
    fake_db.seed(
        "prompt_templates",
        "tmpl_alice",
        {"prompt": "original", "attribution": "alice@example.com"},
    )
    _set_server_identity(monkeypatch, "alice@example.com")

    # Even the owner may not rewrite server-controlled fields via the payload.
    with pytest.raises(PermissionError):
        svc.PromptTemplateService().update_template(
            "tmpl_alice", {"prompt": "x", "attribution": "attacker@evil.com"}
        )

    assert (
        fake_db.collections["prompt_templates"]["tmpl_alice"]["attribution"]
        == "alice@example.com"
    )


# --------------------------------------------------------------------------- #
# 2. add_template attribution forgery  (common/prompt_template_service.py)
# --------------------------------------------------------------------------- #
def test_add_template_rejects_attribution_forgery(monkeypatch, fake_db):
    import common.prompt_template_service as svc

    monkeypatch.setattr(svc, "db", fake_db)
    _set_server_identity(monkeypatch, "attacker@evil.com")

    template = svc.PromptTemplate(
        key="k",
        label="l",
        prompt="p",
        category="c",
        template_type="text",
        attribution="victim@example.com",  # forged
    )

    with pytest.raises(PermissionError):
        svc.PromptTemplateService().add_template(template)

    assert fake_db.collections.get("prompt_templates", {}) == {}


# --------------------------------------------------------------------------- #
# 3. media save/overwrite  (common/metadata.py::add_media_item_to_firestore)
# --------------------------------------------------------------------------- #
def test_media_overwrite_rejects_non_owner(monkeypatch, fake_db):
    import common.metadata as md

    monkeypatch.setattr(md, "db", fake_db)
    fake_db.seed(
        md.config.GENMEDIA_COLLECTION_NAME,
        "media_alice",
        {"user_email": "alice@example.com", "prompt": "original"},
    )
    _set_server_identity(monkeypatch, "attacker@evil.com")

    # Attacker's page-built item is attributed to *themselves* (server-derived),
    # but they target Alice's document id -> ownership mismatch -> rejected.
    item = md.MediaItem(
        id="media_alice", user_email="attacker@evil.com", prompt="PWNED"
    )
    with pytest.raises(PermissionError):
        md.add_media_item_to_firestore(item)

    assert (
        fake_db.collections[md.config.GENMEDIA_COLLECTION_NAME]["media_alice"]["prompt"]
        == "original"
    )


def test_media_overwrite_allows_owner(monkeypatch, fake_db):
    import common.metadata as md

    monkeypatch.setattr(md, "db", fake_db)
    fake_db.seed(
        md.config.GENMEDIA_COLLECTION_NAME,
        "media_alice",
        {"user_email": "alice@example.com", "prompt": "original"},
    )
    _set_server_identity(monkeypatch, "alice@example.com")

    item = md.MediaItem(
        id="media_alice", user_email="alice@example.com", prompt="updated"
    )
    md.add_media_item_to_firestore(item)

    assert (
        fake_db.collections[md.config.GENMEDIA_COLLECTION_NAME]["media_alice"]["prompt"]
        == "updated"
    )


# --------------------------------------------------------------------------- #
# 4. VTO hard delete  (models/shop_the_look_workflow.py::model_on_delete)
# --------------------------------------------------------------------------- #
def _fake_me_state(app_email):
    """Return a fake ``me.state`` that yields per-class state objects."""

    def _state(cls):
        return types.SimpleNamespace(
            user_email=app_email, current_status="", models=[]
        )

    return _state


def test_vto_model_delete_rejects_non_owner(monkeypatch, fake_db):
    import models.shop_the_look_workflow as wf

    monkeypatch.setattr(wf, "db", fake_db)
    monkeypatch.setattr(wf.me, "state", _fake_me_state("attacker@evil.com"))
    monkeypatch.setattr(wf, "load_model_data", lambda: [], raising=False)
    fake_db.seed(
        wf.config.GENMEDIA_VTO_MODEL_COLLECTION_NAME,
        "model_alice",
        {"upload_user": "alice@example.com"},
    )

    event = types.SimpleNamespace(key="some/path/model_alice")
    gen = wf.model_on_delete(event)
    with pytest.raises(PermissionError):
        next(gen)

    # Document must still exist (not deleted).
    assert "model_alice" in fake_db.collections[wf.config.GENMEDIA_VTO_MODEL_COLLECTION_NAME]


def test_vto_model_delete_allows_owner(monkeypatch, fake_db):
    import models.shop_the_look_workflow as wf

    monkeypatch.setattr(wf, "db", fake_db)
    monkeypatch.setattr(wf.me, "state", _fake_me_state("alice@example.com"))
    monkeypatch.setattr(wf, "load_model_data", lambda: [], raising=False)
    fake_db.seed(
        wf.config.GENMEDIA_VTO_MODEL_COLLECTION_NAME,
        "model_alice",
        {"upload_user": "alice@example.com"},
    )

    event = types.SimpleNamespace(key="some/path/model_alice")
    gen = wf.model_on_delete(event)
    next(gen)  # runs the delete then yields

    assert "model_alice" not in fake_db.collections[wf.config.GENMEDIA_VTO_MODEL_COLLECTION_NAME]


# --------------------------------------------------------------------------- #
# 5. Session middleware sink  (common/storage.py::get_or_create_session)
#    Review R1/L2: must be availability-safe (rotate, never raise) so the global
#    identity middleware cannot be turned into a 500-on-every-request DoS.
# --------------------------------------------------------------------------- #
def _seed_session(fake_db, storage, session_id, user_email):
    # Naive UTC to match storage.py's datetime.utcnow() (avoids naive/aware compares).
    now = datetime.datetime.utcnow()
    fake_db.seed(
        storage.cfg.SESSIONS_COLLECTION_NAME,
        session_id,
        {
            "id": session_id,
            "user_email": user_email,
            "created_at": now,
            "last_accessed_at": now,
        },
    )


def test_session_rotates_on_identity_change_without_raising(monkeypatch, fake_db):
    """Anonymous->authenticated reused cookie must rotate, not raise (no 500)."""
    import common.storage as storage

    monkeypatch.setattr(storage, "db", fake_db)
    sessions = storage.cfg.SESSIONS_COLLECTION_NAME
    _seed_session(fake_db, storage, "cookie123", "anonymous@google.com")

    # Authenticated caller replays the anonymous cookie.
    session = storage.get_or_create_session("cookie123", "alice@example.com")

    # A fresh session was minted for the current caller (no exception raised).
    assert session.user_email == "alice@example.com"
    assert session.id != "cookie123"
    assert fake_db.collections[sessions][session.id]["user_email"] == "alice@example.com"
    # The other identity's session was left completely untouched.
    assert fake_db.collections[sessions]["cookie123"]["user_email"] == "anonymous@google.com"


def test_session_owner_match_refreshes_in_place(monkeypatch, fake_db):
    import common.storage as storage

    monkeypatch.setattr(storage, "db", fake_db)
    sessions = storage.cfg.SESSIONS_COLLECTION_NAME
    _seed_session(fake_db, storage, "cookie123", "alice@example.com")
    original_accessed = fake_db.collections[sessions]["cookie123"]["last_accessed_at"]

    session = storage.get_or_create_session("cookie123", "alice@example.com")

    assert session.id == "cookie123"
    assert session.user_email == "alice@example.com"
    # last_accessed_at was refreshed on the same record.
    assert fake_db.collections[sessions]["cookie123"]["last_accessed_at"] >= original_accessed


def test_session_create_records_caller_as_owner(monkeypatch, fake_db):
    import common.storage as storage

    monkeypatch.setattr(storage, "db", fake_db)
    sessions = storage.cfg.SESSIONS_COLLECTION_NAME

    session = storage.get_or_create_session("brandnew", "alice@example.com")

    assert session.id == "brandnew"
    assert fake_db.collections[sessions]["brandnew"]["user_email"] == "alice@example.com"


# --------------------------------------------------------------------------- #
# 6. VTO CSV bulk-upload sinks  (models/shop_the_look_workflow.py)
#    Review M1: previously wrote deterministic-id VTO docs with no authz and no
#    owner field. Must stamp the server-derived caller and reject cross-owner
#    overwrite.
# --------------------------------------------------------------------------- #
_MODEL_CSV = (
    b"model_group,model_id,model_name,model_description,model_view,primary_view,model_image\n"
    b"g0,m1,Name,Desc,front,true,gs://x\n"
)


def _prep_model_upload(monkeypatch, fake_db, wf, caller_email):
    monkeypatch.setattr(wf, "db", fake_db)
    monkeypatch.setattr(wf.me, "state", _fake_me_state(caller_email))
    monkeypatch.setattr(wf, "store_to_gcs", lambda *a, **k: "bucket/uploads/models.csv")
    monkeypatch.setattr(
        wf, "download_from_gcs_as_string", lambda *a, **k: _MODEL_CSV
    )
    file = types.SimpleNamespace(
        name="models.csv", mime_type="text/csv", getvalue=lambda: _MODEL_CSV
    )
    return types.SimpleNamespace(file=file)


def test_vto_csv_upload_stamps_caller_as_owner(monkeypatch, fake_db):
    import models.shop_the_look_workflow as wf

    event = _prep_model_upload(monkeypatch, fake_db, wf, "alice@example.com")

    wf.on_click_upload_models(event)

    models = wf.config.GENMEDIA_VTO_MODEL_COLLECTION_NAME
    assert fake_db.collections[models]["m1_front"]["upload_user"] == "alice@example.com"


def test_vto_csv_upload_rejects_cross_owner_overwrite(monkeypatch, fake_db):
    import models.shop_the_look_workflow as wf

    event = _prep_model_upload(monkeypatch, fake_db, wf, "attacker@evil.com")
    models = wf.config.GENMEDIA_VTO_MODEL_COLLECTION_NAME
    # Alice already owns the doc the attacker's CSV row would collide with.
    fake_db.seed(models, "m1_front", {"upload_user": "alice@example.com", "model_id": "m1"})

    with pytest.raises(PermissionError):
        wf.on_click_upload_models(event)

    # Alice's document is untouched.
    assert fake_db.collections[models]["m1_front"]["upload_user"] == "alice@example.com"
    assert "model_id" in fake_db.collections[models]["m1_front"]
