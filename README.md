# claude-news-clipping

현대자동차 대외협력 직무 면접 대비용 뉴스 클리핑 도구입니다. 자소서와 채용공고에서 언급된
주제(현대차그룹 전략, 관세·통상, 친환경차 정책, 지정학·안보, 국회 입법, 대외협력)를 키워드로
Google 뉴스에서 최신 기사를 모아 매일 정리해줍니다.

## 동작 방식

- 별도 API 키 없이 [Google 뉴스 RSS 검색](https://news.google.com/rss/search)을 사용합니다.
- `news_clipper/config.py`에 정의된 카테고리별 키워드로 검색하고, 동일 기사(링크/제목 기준)는
  자동으로 중복 제거합니다.
- 결과를 카테고리별로 묶어 `clippings/YYYY-MM-DD.md`에 마크다운으로 저장합니다. 카테고리마다
  최신 기사 최대 3건은 실제 기사 본문을 읽어 Claude가 `핵심 내용`과 `면접 답변 포인트` 초안을
  자동으로 채워줍니다 (AI 초안이므로 원문을 한 번 확인하고 다듬는 걸 권장합니다). 나머지 기사와
  본문 추출에 실패한 기사는 빈 칸으로 남아 직접 정리하면 됩니다.
- `clippings/README.md`는 지금까지 생성된 클리핑 목록 인덱스입니다.

### AI 요약 활성화 (선택)

1. [console.anthropic.com](https://console.anthropic.com)에서 API 키를 발급받습니다.
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서
   이름 `ANTHROPIC_API_KEY`, 값에 발급받은 키를 등록합니다.
3. 이후 자동 실행부터 AI 초안이 채워집니다. 키를 등록하지 않아도 도구는 정상 동작하며,
   그 경우 모든 메모 칸이 빈 채로 남습니다.
4. 하루에 최대 6개 카테고리 × 3건 = 18개 기사만 요약하도록 제한되어 있어(한 번의 API 호출로
   처리) 비용 부담이 크지 않습니다. `--summarize-top-n`으로 조절하거나 `--no-ai`로 완전히
   끌 수 있습니다.

## 로컬 실행

```bash
python -m news_clipper.cli --days 1 --max-per-keyword 5
```

- `--days`: 최근 며칠 이내 기사만 수집할지 (기본 1일)
- `--max-per-keyword`: 키워드 하나당 최대 몇 건까지 가져올지 (기본 5건)
- `--output`: 저장 위치 (기본 `clippings/`)
- `--summarize-top-n`: 카테고리별 AI 요약 생성 건수 (기본 3, `ANTHROPIC_API_KEY` 필요)
- `--no-ai`: AI 요약 생략 (`--summarize-top-n 0`과 동일)

로컬에서 AI 요약까지 쓰려면 실행 전에 `export ANTHROPIC_API_KEY=발급받은키`를 해주세요.

## 자동화 (GitHub Actions)

`.github/workflows/daily-clipping.yml`이 **매일 08:00(KST), 주말 포함** 자동으로 실행되어
그날의 클리핑을 생성하고 저장소에 커밋합니다 (cron 표현식 `0 23 * * *`의 마지막 자리가 요일인데
`*`로 두어 모든 요일에 실행됩니다). `Actions` 탭에서 수동 실행(`workflow_dispatch`)도 가능합니다.

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
