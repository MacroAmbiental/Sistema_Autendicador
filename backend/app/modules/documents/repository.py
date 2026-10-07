from typing import Dict, List, Optional


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._documents: Dict[str, dict] = {}

    def save(self, document: dict) -> dict:
        self._documents[document["internal_id"]] = document
        return document

    def list_all(self) -> List[dict]:
        return list(self._documents.values())

    def get_by_public_id(self, public_id: str) -> Optional[dict]:
        for document in self._documents.values():
            if document["public_id"] == public_id:
                return document
        return None


document_repository = InMemoryDocumentRepository()
