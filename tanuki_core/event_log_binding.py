class DashboardEventLogBinding:
    """Read-only adapter for the existing all-channel social-log presenter."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def presentation(self, filter_mode="all", participant_name=""):
        return self.dashboard.controller.build_social_log_presentation(
            self.dashboard,
            filter_mode=filter_mode,
            participant_name=participant_name,
        )
