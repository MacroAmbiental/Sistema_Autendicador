import firebase_admin
from firebase_admin import firestore_async, storage

from app.core.config import settings


def get_firebase_app():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    options = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket

    if options:
        return firebase_admin.initialize_app(options=options)
    return firebase_admin.initialize_app()


def get_firestore():
    get_firebase_app()
    return firestore_async.client()


def get_storage_bucket():
    get_firebase_app()
    return storage.bucket()