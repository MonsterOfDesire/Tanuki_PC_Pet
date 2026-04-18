from dataclasses import dataclass

from .validation import build_validation_report


@dataclass(frozen=True)
class ValidationCheckResult:
    report: str
    warnings: tuple[str, ...]

    @property
    def has_warnings(self):
        return bool(self.warnings)


@dataclass(frozen=True)
class DebugRefreshResult:
    refreshed_pet_count: int


class DashboardToolsActions:
    def __init__(self, validation_report_builder=None):
        self.validation_report_builder = validation_report_builder or build_validation_report

    def apply_debug_refresh(self, pets_dict):
        refreshed_pet_count = 0
        for info in pets_dict.values():
            pet = info.get("pet")
            if pet:
                pet.update()
                refreshed_pet_count += 1
        return DebugRefreshResult(refreshed_pet_count=refreshed_pet_count)

    def build_validation_result(self, resource_resolver, config_store=None):
        assets_dir = resource_resolver("assets_cropped")
        config_path = config_store.config_path if config_store else resource_resolver("config.json")
        report, warnings = self.validation_report_builder(assets_dir, config_path)
        return ValidationCheckResult(report=report, warnings=tuple(warnings))
