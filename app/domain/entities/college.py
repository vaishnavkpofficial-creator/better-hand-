@dataclass
class College:
    id: Optional[str] = None
    name: str = ""
    normalized_name: str = ""       # lowercased, trimmed — for uniqueness + fast search
    district: str = ""
    state: str = ""
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: str = "dataset"         # "dataset" | "admin_added" | "promoted_manual"
    is_verified: bool = True        # false only for promoted-but-unreviewed entries
    created_at: datetime