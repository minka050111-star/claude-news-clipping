"""Keyword categories for the news clipping digest.

Each category maps to a theme from the Hyundai Motor 대외협력(External
Affairs) job posting and the applicant's self-introduction, so the digest
doubles as interview prep material.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Category:
    name: str
    keywords: List[str] = field(default_factory=list)


CATEGORIES: List[Category] = [
    Category(
        name="현대차그룹 전략·사업",
        keywords=["현대자동차 전략", "현대차그룹", "기아 전략", "현대차 신사업"],
    ),
    Category(
        name="관세·통상",
        keywords=["자동차 관세", "미국 상호관세 자동차", "한미 통상", "자동차 수출"],
    ),
    Category(
        name="친환경차·산업 정책",
        keywords=["전기차 보조금", "친환경차 정책", "IRA 전기차", "탄소중립 자동차"],
    ),
    Category(
        name="지정학·안보",
        keywords=["지정학 리스크 산업", "미중 갈등 공급망", "핵심광물 공급망", "글로벌 안보 환경"],
    ),
    Category(
        name="국회·입법",
        keywords=["국회 자동차 법안", "산업통상자원위원회", "국토교통위원회 법안"],
    ),
    Category(
        name="대외협력·네트워킹",
        keywords=["기업 대외협력", "대기업 정부 협력", "경제단체 네트워킹"],
    ),
]
