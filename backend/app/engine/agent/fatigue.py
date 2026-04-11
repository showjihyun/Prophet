"""Exposure Fatigue Model — 반복 노출에 따른 수용성 감쇠.

SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#sq-01
"""
from dataclasses import dataclass


@dataclass
class FatigueConfig:
    """ExposureFatigue 설정.

    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#sq-01
    """
    saturation_threshold: int = 20   # 이 횟수 이상이면 min_factor 고정
    decay_rate: float = 0.85          # 스텝당 지수 감쇠율
    min_factor: float = 0.1           # 최소 수용성 배율


class ExposureFatigue:
    """반복 노출에 따른 수용성 감쇠(피로) 모델.

    SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#sq-01

    실제 광고/소셜미디어에서 동일 콘텐츠를 반복 노출받으면
    반응 확률이 줄어드는 현상(ad fatigue)을 모델링한다.

    Formula:
        factor = max(min_factor, decay_rate ^ exposure_count)
        exposure_count >= saturation_threshold → factor = min_factor
    """

    def __init__(self, config: FatigueConfig | None = None) -> None:
        self._config = config or FatigueConfig()

    def compute_fatigue_factor(self, exposure_count: int) -> float:
        """노출 횟수에 따른 피로 배율을 계산한다.

        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#sq-01

        Args:
            exposure_count: 에이전트의 누적 노출 횟수 (>= 0)

        Returns:
            fatigue_factor in [min_factor, 1.0]
            0이면 1.0 (피로 없음), saturation 이상이면 min_factor
        """
        cfg = self._config
        if exposure_count <= 0:
            return 1.0
        if exposure_count >= cfg.saturation_threshold:
            return cfg.min_factor
        factor = cfg.decay_rate ** exposure_count
        return max(cfg.min_factor, min(1.0, factor))


__all__ = ["ExposureFatigue", "FatigueConfig"]
