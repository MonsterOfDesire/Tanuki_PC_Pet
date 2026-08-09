class DashboardFamilySummaryBinding:
    """Adapter that reuses the Dashboard presenter and household action paths."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def presentation(self):
        return self.dashboard.controller.build_household_summary_presentation(self.dashboard)

    def rhythm_presentation(self):
        return self.dashboard.controller.build_household_rhythm_presentation(
            self.dashboard
        )

    def achievement_summary(self):
        provider = getattr(
            self.dashboard,
            "get_achievement_cabinet_snapshot",
            None,
        )
        snapshot = provider() if callable(provider) else None
        if snapshot is None:
            return None
        return snapshot.mode_snapshot(
            getattr(self.dashboard, "world_mode", "sandbox")
        )

    def open_achievement_cabinet(self):
        opener = getattr(
            self.dashboard,
            "show_achievement_cabinet",
            None,
        )
        return opener() if callable(opener) else False

    def can_donate_fund(self):
        return getattr(self.dashboard, "world_mode", "") == "golden_legend"

    def donate_fund(self, amount=100):
        return self.dashboard.donate_household_fund(amount=int(amount))
