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

    yaw_var = data.get("yaw_var", 0)
    pitch_var = data.get("pitch_var", 0)
    roll_var = data.get("roll_var", 0)
    total_var = yaw_var + pitch_var + roll_var
    if total_var < 5:
        parts.append("Head movement: very low variance — subject appears static")
    elif total_var < 20:
        parts.append("Head movement: within normal range")
    else:
        parts.append("Head movement: high variance — unusually erratic motion")

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
                "pose_score": round(temporal_data["pose_score"], 4),
                "blink_count": temporal_data["blink_count"],
                "blinks_per_min": temporal_data["blinks_per_min"],
                "yaw_var": temporal_data["yaw_var"],
                "pitch_var": temporal_data["pitch_var"],
                "roll_var": temporal_data["roll_var"],
                "explanation": _temporal_explanation(temporal_data),
            },
            "frequency": {
                "score": round(frequency_score, 4),
                "explanation": _frequency_explanation(frequency_score),
            },
        },
    }
