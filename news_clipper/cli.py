from __future__ import annotations

import argparse
from pathlib import Path

from .clip import write_digest


def main() -> None:
    parser = argparse.ArgumentParser(description="현대자동차 대외협력 면접 대비 뉴스 클리핑")
    parser.add_argument("--days", type=int, default=1, help="최근 N일 이내 기사만 수집 (기본 1일)")
    parser.add_argument("--max-per-keyword", type=int, default=5, help="키워드별 최대 수집 기사 수 (기본 5)")
    parser.add_argument("--output", type=Path, default=Path("clippings"), help="출력 디렉터리 (기본 clippings/)")
    args = parser.parse_args()

    out_path = write_digest(args.output, days=args.days, max_per_keyword=args.max_per_keyword)
    print(f"클리핑 생성 완료: {out_path}")


if __name__ == "__main__":
    main()
