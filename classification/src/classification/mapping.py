"""Which waste category each material belongs to.

The categories must match data_rules.CATEGORIES; a unit test checks this contract.
"""

MATERIAL_TO_CATEGORY: dict[str, str] = {
    "paper": "recyclable",
    "cardboard": "recyclable",
    "plastic": "recyclable",
    "metal": "recyclable",
    "glass": "recyclable",
    "organic": "compostable",
    "trash": "landfill",
}

# The 7 materials the model knows, in the default order (labels.json decides the real order).
MATERIALS: tuple[str, ...] = tuple(MATERIAL_TO_CATEGORY)


def to_category(material: str) -> str:
    """Return the waste category for a material, e.g. "plastic" -> "recyclable".

    Raises:
        ValueError: if the material is not one of the 7 known materials.
    """
    try:
        return MATERIAL_TO_CATEGORY[material]
    except KeyError:
        known = ", ".join(MATERIALS)
        raise ValueError(f"Unknown material {material!r}. Known materials: {known}.") from None
