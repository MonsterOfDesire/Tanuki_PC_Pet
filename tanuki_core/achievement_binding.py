class DashboardAchievementBinding:
    """Provides achievement snapshots without exposing Dashboard internals."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def snapshot(self):
        provider = getattr(
            self.dashboard,
            "get_achievement_cabinet_snapshot",
            None,
        )
        return provider() if callable(provider) else None

    def runtime_world_mode(self):
        return str(getattr(self.dashboard, "world_mode", "sandbox") or "sandbox")

    def capture_enabled(self):
        return bool(
            getattr(self.dashboard, "achievement_capture_enabled", False)
        )

    def set_capture_enabled(self, enabled):
        setter = getattr(
            self.dashboard,
            "set_achievement_capture_enabled",
            None,
        )
        return bool(setter(enabled)) if callable(setter) else False

    def latest_memory_path(self, world_mode, achievement_id):
        provider = getattr(
            self.dashboard,
            "get_achievement_memory_path",
            None,
        )
        return (
            provider(world_mode, achievement_id)
            if callable(provider)
            else None
        )
