WEIGHTS = {
    "spatial": 0.40,
    "frequency": 0.25,
    "temporal": 0.35,
}


def _suspicion_level(score: float) -> str:
    if score < 0.3:
        return "none"
    if score < 0.5:
        return "low"
    if score < 0.7:
        return "moderate"
    return "high"


REGION_LABELS = {
    "eyes": "eyes",
    "nose": "nose",
    "mouth": "mouth",
    "forehead": "forehead",
    "cheeks": "cheeks",
    "jawline": "jawline",
}


def _spatial_explanation(regions: dict[str, float]) -> str:
    if not regions:
        return "No regional data available."
    hot = {k: v for k, v in regions.items() if v >= 0.4}
    cool = {k: v for k, v in regions.items() if v < 0.2}
    if not hot:
        return "No anomalous regions detected on the face."
    sorted_hot = sorted(hot.items(), key=lambda x: x[1], reverse=True)
    region_strs = [f"{REGION_LABELS[k]} ({v:.2f})" for k, v in sorted_hot]
    parts = [f"Anomalous regions: {', '.join(region_strs)}."]
    if cool:
        cool_strs = [REGION_LABELS[k] for k, _ in sorted(cool.items(), key=lambda x: x[1])]
        parts.append(f"Consistent regions: {', '.join(cool_strs)}.")
    return " ".join(parts)


def _temporal_explanation(data: dict) -> str:
    parts = []
    bpm = data.get("blinks_per_min", 0)
    if bpm > 0:
        direction = "below" if bpm < 17 else "above"
        diff_pct = abs(bpm - 17) / 17 * 100
        parts.append(f"Blink rate: {bpm:.0f}/min (expected ~17) — {diff_pct:.0f}% {direction} normal")
    else:
        parts.append("Blink rate: undetectable")

    flick = data.get("flickering_score", 0.5)
    if flick > 0.7:
        parts.append("High temporal flickering — strong frame-to-frame spectral inconsistency")
    elif flick > 0.4:
        parts.append("Moderate temporal flickering detected")
    else:
        parts.append("Temporal consistency: stable across frames")

    stability = data.get("landmark_stability", 0.5)
    if stability > 0.7:
        parts.append("Low landmark stability — significant facial landmark jitter")
    elif stability > 0.4:
        parts.append("Moderate landmark jitter detected")
    else:
        parts.append("Landmark stability: consistent positioning")

    return ". ".join(parts) + "."


def _frequency_explanation(score: float) -> str:
    if score < 0.3:
        return "High-frequency energy ratio is within normal range."
    if score < 0.5:
        return "Slightly elevated high-frequency energy — minor spectral artifacts."
    if score < 0.7:
        return "Elevated high-frequency energy ratio — spectral anomalies detected."
    return "Strong high-frequency energy — significant spectral artifacts consistent with manipulation."


def _summary(level: str, spatial: float, frequency: float, temporal: float) -> str:
    if level == "none":
        return "No significant anomalies detected across spatial, frequency, or temporal signals."
    if level == "low":
        return "Minor deviations detected. Results are consistent with authentic footage."
    signals = []
    if spatial >= 0.5:
        signals.append("spatial")
    if frequency >= 0.5:
        signals.append("frequency")
    if temporal >= 0.5:
        signals.append("temporal")
    if len(signals) == 0:
        sig_str = "multiple"
    elif len(signals) == 1:
        sig_str = signals[0]
    elif len(signals) == 2:
        sig_str = f"{signals[0]} and {signals[1]}"
    else:
        sig_str = f"{signals[0]}, {signals[1]}, and {signals[2]}"
    if level == "moderate":
        return f"Anomalous patterns detected primarily in {sig_str} signals. Manual review recommended."
    return f"Strong anomalous patterns detected across {sig_str} signals. Likely manipulated content."


def fuse(
    spatial_score: float,
    frequency_score: float,
    temporal_data: dict,
    region_scores: dict[str, float] | None = None,
) -> dict:
    temporal_score = temporal_data["score"]
    fused = (
        spatial_score * WEIGHTS["spatial"]
        + frequency_score * WEIGHTS["frequency"]
        + temporal_score * WEIGHTS["temporal"]
    )
    level = _suspicion_level(fused)
    regions = region_scores or {}
    return {
        "fused_score": round(fused, 4),
        "spatial_score": round(spatial_score, 4),
        "frequency_score": round(frequency_score, 4),
        "temporal_score": round(temporal_score, 4),
        "suspicion_level": level,
        "summary": _summary(level, spatial_score, frequency_score, temporal_score),
        "signals": {
            "spatial": {
                "score": round(spatial_score, 4),
                "regions": {k: round(v, 4) for k, v in regions.items()},
                "explanation": _spatial_explanation(regions),
            },
            "temporal": {
                "score": round(temporal_score, 4),
                "blink_score": round(temporal_data["blink_score"], 4),
                "blink_count": temporal_data["blink_count"],
                "blinks_per_min": temporal_data["blinks_per_min"],
                "flickering_score": round(temporal_data["flickering_score"], 4),
                "landmark_stability": round(temporal_data["landmark_stability"], 4),
                "explanation": _temporal_explanation(temporal_data),
            },
            "frequency": {
                "score": round(frequency_score, 4),
                "explanation": _frequency_explanation(frequency_score),
            },
        },
    }
