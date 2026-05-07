"""
embeddings/ — W3.5 종목 임베딩 학습 (Contrastive, 64차원).

본 패키지는 *데이터 파이프라인 + augmentation 순수 함수* 를 먼저 정의한다.
인코더·학습 루프는 W3.5B 이후 PyTorch 도입 결정을 받은 뒤 추가.

차기_사이클.md §W3.5 명세:
  - 시계열 윈도우 60거래일, 채널 2 (수익률·거래량 변화).
  - Augmentation 3종: 마스킹 10~30%, 가우시안 노이즈 σ=0.01, 시점 jitter ±2일.
  - 인코더 1D-CNN 3 layer + projection head 64→128→64. (W3.5B)
  - 손실 InfoNCE, temperature 0.1, batch 256. (W3.5B)
"""

from .data import (
    AugmentParams,
    augment_series,
    add_gaussian_noise,
    extract_windows,
    mask_random,
    series_from_prices,
    time_jitter,
)

# W3.5B — PyTorch 의존. 미설치 환경에서는 data 만 노출.
try:
    from .encoder import ContrastiveModel, Encoder1DCNN, ProjectionHead
    from .loss    import alignment_uniformity, nt_xent_loss
    _TORCH_OK = True
except ImportError:
    _TORCH_OK = False

__all__ = [
    "AugmentParams",
    "augment_series",
    "add_gaussian_noise",
    "extract_windows",
    "mask_random",
    "series_from_prices",
    "time_jitter",
]
if _TORCH_OK:
    __all__ += [
        "ContrastiveModel",
        "Encoder1DCNN",
        "ProjectionHead",
        "nt_xent_loss",
        "alignment_uniformity",
    ]
