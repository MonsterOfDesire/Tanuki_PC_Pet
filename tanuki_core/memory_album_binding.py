class DashboardMemoryAlbumBinding:
    """Narrow binding between the album page and Dashboard persistence."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def snapshot(self):
        provider = getattr(self.dashboard, "get_memory_album_snapshot", None)
        return provider() if callable(provider) else None

    def set_mode(self, mode):
        setter = getattr(self.dashboard, "set_memory_album_mode", None)
        return bool(setter(mode)) if callable(setter) else False

    def set_capacity(self, capacity):
        setter = getattr(self.dashboard, "set_memory_album_capacity", None)
        return bool(setter(capacity)) if callable(setter) else False

    def open_folder(self):
        opener = getattr(self.dashboard, "open_memory_album_folder", None)
        return bool(opener()) if callable(opener) else False
