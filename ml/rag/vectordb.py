class VectorDB:
    def __init__(self) -> None:
        self.backend = "qdrant"

    def upsert(self, payload: dict) -> dict:
        return {"backend": self.backend, "stored": True, "payload": payload}
