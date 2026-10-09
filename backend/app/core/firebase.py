"""Firebase Admin carregado sob demanda: testes locais nao exigem credenciais."""
from app.core.config import settings


def get_firebase_app():
    import firebase_admin
    try:
        return firebase_admin.get_app()
    except ValueError:
        options = {}
        if settings.firebase_project_id:
            options["projectId"] = settings.firebase_project_id
        if settings.firebase_storage_bucket:
            options["storageBucket"] = settings.firebase_storage_bucket
        return firebase_admin.initialize_app(options=options or None)


def get_firestore():
    from firebase_admin import firestore
    get_firebase_app()
    return firestore.client()


def get_storage_bucket():
    from firebase_admin import storage
    get_firebase_app()
    return storage.bucket(settings.firebase_storage_bucket or None)
