# Copyright 2025 Google LLC
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

"""Workflow for the Shop the Look page."""

import csv
import datetime

import mesop as me
from google.cloud import firestore

from common.storage import (
    download_from_gcs_as_string,
    store_to_gcs,
)
from config.default import Default
from config.firebase_config import FirebaseClient
from models.shop_the_look_models import (
    CatalogRecord,
    ModelRecord,
)
from state.shop_the_look_state import PageState
from state.state import AppState

config = Default()
db = FirebaseClient(database_id=config.GENMEDIA_FIREBASE_DB).get_client()

def model_on_delete(e: me.ClickEvent):
     state = me.state(PageState)
     file_to_delete = e.key.split("/")[-1]
     print(f"deleting {file_to_delete}")
     state.current_status = f"Deleting model {file_to_delete}"
     try:
         doc_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME).document(
             file_to_delete
         )

         doc_ref.delete()
         state.models = load_model_data()
         state.current_status = ""
         yield
     except:
         print(f"Model data  delete failure: {file_to_delete} cannot be stored")

def article_on_delete(e: me.ClickEvent):
    state = me.state(PageState)
    file_to_delete = e.key.split("/")[-1]
    print(f"deleting {file_to_delete}")
    state.current_status = f"Deleting article {file_to_delete}"
    try:
        doc_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME).document(
            file_to_delete
        )
        doc_ref.delete()
        load_article_data()
        state.current_status = ""
        yield
    except:
        print(f"Model data  delete failure: {file_to_delete} cannot be stored")


def get_csv_headers(csv_reader):
    """
    Retrieves a list of header names from a CSV file.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        list: A list containing the header names, or an empty list if the file is empty or an error occurs.
    """
    try:
        header = next(csv_reader)
        return header
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def on_click_upload_models(e: me.UploadEvent):
    """Upload image to GCS"""
    state = me.state(PageState)
    state.reference_model_file = e.file
    contents = e.file.getvalue()
    destination_blob_name = store_to_gcs(
        "uploads", e.file.name, e.file.mime_type, contents
    )

    state.reference_model_file_gs_uri = f"gs://{destination_blob_name}"

    print(
        f"{destination_blob_name} with contents len {len(contents)} of type {e.file.mime_type} uploaded to {config.GENMEDIA_BUCKET}."
    )

    csv_file = download_from_gcs_as_string(
        f"gs://{config.GENMEDIA_BUCKET}/uploads/{e.file.name}"
    )

    cf = [row.decode("utf-8") for row in csv_file.split(b"\n") if row]
    cf = csv.reader(cf, delimiter=",")

    required_fields = [
        "model_group",
        "model_id",
        "model_name",
        "model_description",
        "model_view",
        "primary_view",
        "model_image",
    ]

    headers = get_csv_headers(cf)

    for c in required_fields:  # ie. ["batch", "department"]
        if c not in headers:
            print(f"Missing CSV header for {c}")
            return

    current_datetime = datetime.datetime.now()

    for row in cf:
        try:
            # TODO mapping object instead of row[]
            doc_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME).document(
                f"{row[1]}_{row[4]}"
            )
            doc_ref.set(
                {
                    "model_group": row[0],
                    "model_id": row[1],
                    "model_name": row[2],
                    "model_description": row[3],
                    "model_view": row[4],
                    "primary_view": row[5],
                    "model_image": row[6],
                    "timestamp": current_datetime,  # alt: firestore.SERVER_TIMESTAMP
                }
            )
        except:
            print(f"{row[2]} cannot be converted")


def on_click_upload_catalog(e: me.UploadEvent):
    """Upload image to GCS"""
    state = me.state(PageState)
    state.reference_catalog_file = e.file
    contents = e.file.getvalue()
    destination_blob_name = store_to_gcs(
        "uploads", e.file.name, e.file.mime_type, contents
    )

    state.reference_catalog_file_gs_uri = f"gs://{destination_blob_name}"

    print(
        f"{destination_blob_name} with contents len {len(contents)} of type {e.file.mime_type} uploaded to {config.GENMEDIA_BUCKET}."
    )

    csv_file = download_from_gcs_as_string(
        f"gs://{config.GENMEDIA_BUCKET}/uploads/{e.file.name}"
    )

    cf = [row.decode("utf-8") for row in csv_file.split(b"\n") if row]
    cf = csv.reader(cf, delimiter=",")

    required_fields = [
        "item_id",
        "look_id",
        "article_type",
        "article_color",
        "model_group",
        "description",
        "image_view",
        "try_on_order",
    ]

    headers = get_csv_headers(cf)

    for c in required_fields:  # ie. ["batch", "department"]
        if c not in headers:
            print(f"Missing CSV header for {c}")
            return

    current_datetime = datetime.datetime.now()

    for row in cf:
        try:
            doc_ref = db.collection(
                config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME
            ).document(f"{row[1]}_{row[2]}")
            doc_ref.set(
                {
                    "item_id": row[0],
                    "look_id": int(row[1]),
                    "article_type": row[2],
                    "article_color": row[3],
                    "model_group": row[4],
                    "description": row[5],
                    "image_view": row[6],
                    "try_on_order": row[7],
                    "timestamp": current_datetime,  # alt: firestore.SERVER_TIMESTAMP
                }
            )
        except:
            print(f"{row[2]} cannot be converted")


def load_model_data(limit: int = 50):
    try:
        app_state = me.state(AppState)
        media_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME)

        query = media_ref.where("upload_user", "in", ["everyone", app_state.user_email])

        models = []
        for doc in query.stream():
            model_data = doc.to_dict()
            models.append(ModelRecord(**model_data))

        return models
    except Exception as e:
        print(f"Error fetching models: {e}")


def load_article_data(limit: int = 50):
    state = me.state(PageState)
    app_state = me.state(AppState)
    media_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME)
    query = media_ref.where("upload_user", "in", ["everyone", app_state.user_email])

    articles = []
    for doc in query.stream():
        article_data = doc.to_dict()
        articles.append(CatalogRecord(**article_data))

    articles = sorted(articles, key=lambda article: article.article_type)

    state.articles = articles


def load_look_data(limit: int = 50):
    state = me.state(PageState)
    media_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME).order_by(
        "look_id", direction=firestore.Query.ASCENDING
    )
    looks = []
    for doc in media_ref.stream():
        catalog_data = doc.to_dict()
        record = CatalogRecord(**catalog_data)
        record.clothing_image = (f"gs://{config.GENMEDIA_BUCKET}/{record.item_id}",)
        looks.append(record)

    looks.sort(key=lambda item: (item.look_id, item.try_on_order))
    looks = list(
        filter(
            lambda look: look.article_type not in ("sunglasses", "watch", "hat"),
            looks,
        )
    )

    return looks


def get_selected_look():
    state = me.state(PageState)
    selected_look_data = list(
        filter(lambda catalogrecord: catalogrecord.selected, state.articles)
    )
    return selected_look_data


def get_model_records(model_id):
    state = me.state(PageState)
    model_records = []
    for m in state.models:
        if m.model_id == model_id:
            model_records.append(m)
    return model_records


def store_model_data(file_path):
    state = me.state(PageState)
    app_state = me.state(AppState)
    current_datetime = datetime.datetime.now()
    file_name_only = file_path.split("/")[-1]
    doc_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME)

    upload_user = "everyone" if state.upload_everyone else app_state.user_email

    new_doc_data = {
        "model_group": "0",
        "model_id": file_name_only,
        "model_image": file_path,
        "timestamp": current_datetime,
        "upload_user": upload_user,
    }

    update_time, doc_ref = doc_ref.add(new_doc_data)


def store_article_data(file_path, article_category):
    state = me.state(PageState)
    app_state = me.state(AppState)
    current_datetime = datetime.datetime.now()
    file_name_only = file_path.split("/")[-1]
    doc_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME)

    upload_user = "everyone" if state.upload_everyone else app_state.user_email

    new_doc_data = {
        "item_id": file_name_only,
        "article_type": article_category,
        "model_group": "0",
        "timestamp": current_datetime,
        "ai_description": None,
        "selected": False,
        "available_to_select": True,
        "clothing_image": file_path,
        "upload_user": upload_user,
    }

    update_time, doc_ref = doc_ref.add(new_doc_data)
