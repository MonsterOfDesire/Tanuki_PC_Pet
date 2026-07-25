class DashboardFamilySummaryBinding:
    """Adapter that reuses the Dashboard presenter and household action paths."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def presentation(self):
        return self.dashboard.controller.build_household_summary_presentation(self.dashboard)

    def can_donate_fund(self):
        return getattr(self.dashboard, "world_mode", "") == "golden_legend"

    def donate_fund(self, amount=100):
        return self.dashboard.donate_household_fund(amount=int(amount))
