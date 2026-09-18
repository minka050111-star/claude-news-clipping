from __future__ import annotations

import argparse
from pathlib import Path

from .clip import write_digest


def main() -> None:
    parser = argparse.ArgumentParser(description="현대자동차 대외협력 면접 대비 뉴스 클리핑")
    parser.add_argument("--days", type=int, default=1, help="최근 N일 이내 기사만 수집 (기본 1일)")
    parser.add_argument("--max-per-keyword", type=int, default=5, help="키워드별 최대 수집 기사 수 (기본 5)")
    parser.add_argument("--output", type=Path, default=Path("clippings"), help="출력 디렉터리 (기본 clippings/)")
    parser.add_argument(
        "--summarize-top-n",
        type=int,
        default=3,
        help="카테고리별 AI 요약(핵심 내용/면접 답변 포인트 초안)을 생성할 최신 기사 수. "
        "0이면 AI 요약 없이 빈 칸으로 둠 (기본 3, ANTHROPIC_API_KEY 필요)",
    )
    parser.add_argument("--no-ai", action="store_true", help="AI 요약 생략 (--summarize-top-n 0 과 동일)")
    args = parser.parse_args()

    summarize_top_n = 0 if args.no_ai else args.summarize_top_n
    out_path = write_digest(
        args.output,
        days=args.days,
        max_per_keyword=args.max_per_keyword,
        summarize_top_n=summarize_top_n,
    )
    print(f"클리핑 생성 완료: {out_path}")


if __name__ == "__main__":
    main()
