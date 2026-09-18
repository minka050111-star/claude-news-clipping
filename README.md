# claude-news-clipping

현대자동차 대외협력 직무 면접 대비용 뉴스 클리핑 도구입니다. 자소서와 채용공고에서 언급된
주제(현대차그룹 전략, 관세·통상, 친환경차 정책, 지정학·안보, 국회 입법, 대외협력)를 키워드로
Google 뉴스에서 최신 기사를 모아 매일 정리해줍니다.

## 동작 방식

- 별도 API 키 없이 [Google 뉴스 RSS 검색](https://news.google.com/rss/search)을 사용합니다.
- `news_clipper/config.py`에 정의된 카테고리별 키워드로 검색하고, 동일 기사(링크/제목 기준)는
  자동으로 중복 제거합니다.
- 결과를 카테고리별로 묶어 `clippings/YYYY-MM-DD.md`에 마크다운으로 저장하고, 각 기사 아래에는
  면접 준비용 메모 칸(`핵심 내용`, `면접 답변 포인트`)을 비워둡니다. 매일 클리핑을 읽으면서
  직접 채워 넣으면 그대로 면접 답변 초안이 됩니다.
- `clippings/README.md`는 지금까지 생성된 클리핑 목록 인덱스입니다.

## 로컬 실행

```bash
python -m news_clipper.cli --days 1 --max-per-keyword 5
```

- `--days`: 최근 며칠 이내 기사만 수집할지 (기본 1일)
- `--max-per-keyword`: 키워드 하나당 최대 몇 건까지 가져올지 (기본 5건)
- `--output`: 저장 위치 (기본 `clippings/`)

## 자동화 (GitHub Actions)

`.github/workflows/daily-clipping.yml`이 매일 08:00(KST)에 자동으로 실행되어 그날의 클리핑을
생성하고 저장소에 커밋합니다. `Actions` 탭에서 수동 실행(`workflow_dispatch`)도 가능합니다.
스케줄 트리거는 기본 브랜치(main 등)에 머지된 이후부터 동작합니다.

## 키워드 커스터마이징

`news_clipper/config.py`의 `CATEGORIES`를 수정해 관심 키워드를 추가/삭제할 수 있습니다.
자소서에서 다룬 경험(법안 모니터링, 국제법 논문 등)과 관련된 최신 이슈를 추가로 넣어두면
"최근 이슈에 대해 어떻게 생각하냐"는 질문에 대비하기 좋습니다.

## 테스트

네트워크 호출을 모킹한 단위 테스트가 있습니다 (실제 기사 수집 없이 파싱/중복제거/마크다운
생성 로직을 검증):

```bash
python -m unittest discover -s tests -v
```
