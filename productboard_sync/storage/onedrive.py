from ._graph_base import GRAPH_BASE, GraphAuthMixin
from .base import StorageBackend


class OneDriveStorageBackend(GraphAuthMixin, StorageBackend):
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        drive_id: str,
        folder_id: str,
        timeout: int = 30,
    ) -> None:
        self._drive_id = drive_id
        self._folder_id = folder_id
        self._init_auth(tenant_id, client_id, client_secret, timeout=timeout)

    def _item_url(self, path: str) -> str:
        return f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._folder_id}:/{path}:/content"

    def write_file(self, path: str, content: str) -> None:
        self._graph_put(self._item_url(path), content)

    def read_file(self, path: str) -> str:
        return self._graph_get_text(self._item_url(path))

    def list_files(self, prefix: str = "") -> list[str]:
        url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._folder_id}/children"
        items = self._graph_list_children(url)
        names = [item["name"] for item in items if "name" in item]
        return [name for name in names if name.startswith(prefix)]

    def delete_file(self, path: str) -> None:
        url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._folder_id}:/{path}:"
        self._graph_delete(url)
