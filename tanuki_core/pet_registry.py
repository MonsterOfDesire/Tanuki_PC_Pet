from dataclasses import dataclass


@dataclass(frozen=True)
class PetSpec:
    folder_name: str
    scale: float
    display_name: str
    initially_visible: bool = True


DEFAULT_PET_SPECS = (
    PetSpec("Symboli Rudolf", 0.45, "滷豆腐"),
    PetSpec("Tokai Teio", 0.35, "帝寶", initially_visible=False),
    PetSpec("Sirius Symboli", 0.4, "天狼星", initially_visible=False),
    PetSpec("Tsurumaru Tsuyoshi", 0.3, "鶴寶", initially_visible=False),
    PetSpec("Air Groove", 0.4, "氣槽", initially_visible=False),
)


class PetRegistry:
    """Stable lookup boundary over the runtime's single pet collection."""

    def __init__(self, pets_dict, pets_list):
        self.pets_dict = pets_dict
        self.pets_list = pets_list

    def find_by_name(self, pet_name, *, visible_only=False):
        for pet in self.pets_list:
            if getattr(pet, "name", None) != pet_name:
                continue
            if visible_only and not pet.isVisible():
                continue
            return pet
        return None
