def to_seconds(duration: str) -> int:
    duration = duration.strip()
    if duration.endswith("s"):
        return int(duration[:-1])
    if duration.endswith("m"):
        return int(duration[:-1]) * 60
    if duration.endswith("h"):
        return int(duration[:-1]) * 3600
    raise ValueError(f"invalid duration: {duration!r}")