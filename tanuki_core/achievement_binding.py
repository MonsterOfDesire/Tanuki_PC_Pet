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
