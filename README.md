# do-spec 0.2.0

`to-spec → to-tickets → do-spec`: spec에 속한 **open issue만 큐에 넣고**, 작업 후 해당 issue의 **closed 상태를 조회하여 완료**로 판단합니다.

- 이미 closed인 issue는 큐에서 제외합니다. open issue가 참조하는 closed 선행 issue는 처리된 의존성으로 봅니다.
- 실행 직전 closed로 바뀐 issue도 agent를 실행하지 않습니다.
- 작업 후에도 open이거나 tracker 조회가 실패하면 다음 issue를 시작하지 않습니다.
- 기본 `completion: issue-closed`에서는 do-spec이 외부 테스트나 checkpoint commit을 완료 조건으로 요구하지 않습니다. 구현 workflow가 테스트·review·commit·issue close를 담당합니다.
- do-spec이 스스로 issue를 닫아 성공 처리하지 않습니다. 타임아웃·취소·예상 밖 branch 변경은 계속 안전하게 중단합니다.

[변경된 완료 계약](docs/ISSUE-CLOSED.md) · [호환성](COMPATIBILITY.md) · [기존 인수 기록](docs/ACCEPTANCE.md)

[실제 Cline E2E 결과와 재현 방법](docs/REAL-CLINE-E2E.md): Windows x64 Cline 3.0.61 + 동봉 Dagu + 로컬 fake tracker에서 실패 차단·재개를 검증했습니다. 원격 issue나 upstream implement 스킬 자체를 검증한 것은 아닙니다.

## 설치

**`skills/do-spec` 폴더 전체를 사용하는 에이전트의 skill 위치에 복사하고 스킬을 호출하세요.** 예: “do-spec 스킬로 이 spec의 남은 issue를 진행해줘.”

스킬을 읽은 에이전트가 **스킬 내부의 `scripts/run.py`를 `uv run`으로 실행**합니다. 의존성 준비, 계획 생성, 순차 실행, 상태 조회와 모니터링 웹 시작까지 에이전트가 담당하며 실제 웹 주소를 안내합니다. 사용자가 CLI 명령을 입력하거나 별도 터미널을 여는 절차는 기본 사용 흐름에 없습니다. uv와 Git이 필요하고, 첫 방문의 웹 계정 설정은 사용자가 진행합니다.

실행 코드가 폴더에 포함되어 별도 wheel/pip 설치는 필요 없습니다. Python은 uv가 준비합니다. Dagu 2.11.2는 `tools/dagu/2.11.2/windows-amd64.zip`과 `linux-amd64.zip`으로 포함되며, **스킬 최초 사용 시 현재 OS의 실행 파일만 자동으로 풉니다.** 이후에는 해시를 확인해 재사용합니다. 압축 파일은 각각 100MiB 미만이라 일반 Git에 저장할 수 있고, 풀린 실행 파일은 Git에서 제외합니다. 별도 install hook이나 수동 압축 해제는 필요 없습니다. 개발자는 `python scripts/bundle_skill.py --with-dagu`로 압축 파일을 재생성할 수 있습니다. 기본 모니터링 주소는 `http://127.0.0.1:8080`입니다. Windows Cline 3.0.61 + 로컬 tracker 전용 adapter를 지원하며 원격 tracker와 다른 Cline/OS 조합은 미검증입니다.

[스킬 실행 지침](skills/do-spec/SKILL.md) · [에이전트용 내부 명령 참고](skills/do-spec/references/usage.md). 아래는 standalone 도구를 직접 점검하려는 개발자용 선택 사항입니다.

Python 3.12+, Git, 별도 Dagu 2.11.2가 필요합니다. Windows/Linux는 같은 Python 코드이며, Linux 네이티브 실행은 아직 미검증입니다.

```text
python -m venv .venv
<venv-python> -m pip install dist/do_spec-0.2.0-py3-none-any.whl
```

Windows는 `.venv\Scripts\python.exe`, Linux는 `.venv/bin/python`을 사용합니다. `do-spec` 대신 `<venv-python> -m do_spec`도 가능합니다. [skill](skills/do-spec/SKILL.md)은 `dist/do-spec-skill.zip`으로 별도 제공합니다. Cline의 확인된 skill 위치에 설치하며 전역 설정은 자동 변경하지 않습니다.

## 로컬 실패·재개 데모

```text
do-spec demo --dir .demo/closed-fail5 --dagu <absolute-dagu-executable> --fail-at 5
```

fake agent가 1~4번 issue를 closed로 바꾸고 5번은 open으로 남깁니다. `ISSUE_STILL_OPEN`, 종료 코드 11로 멈추며 6~10번 agent는 시작하지 않습니다. 상태 파일은 `.demo/closed-fail5/issues.json`, 시작 journal은 `agent.jsonl`입니다. 실제 tracker나 모델을 호출하지 않습니다.

데모의 5번 issue를 closed로 바꾼 뒤 조회만 재개합니다. 실제 운영에서는 구현 workflow가 실제 issue를 닫아야 합니다.

```powershell
$run = (Get-ChildItem .demo/closed-fail5/state/runs -Directory | Select-Object -First 1).FullName
$dbPath = (Resolve-Path .demo/closed-fail5/issues.json).Path
$db = Get-Content $dbPath -Raw | ConvertFrom-Json
$db.issues.'5'.state = 'closed'
$db | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $dbPath
do-spec resume --run "$run" --mode verify-only
do-spec status --run "$run"
```

`verify-only`는 테스트 재실행이 아니라 **closed 재조회**입니다. `rerun-agent` (`repair`)는 현재 open issue만 재실행하고, `finalize-only` (`report-only`)는 closure 확인 후의 보고를 재개합니다. 새로운 큐를 만들 때 전부 closed라면 agent 실행 없이 성공합니다. 기존 예약 run은 같은 worktree에서 resume하여 작업을 보존합니다.

## 설정·UI·검증

`init --repo <repo> --output <sidecar.json> --dagu <exe>`로 초안을 만들고, spec·Parent·ticket mapping·tracker를 설정합니다. 로컬 fixture에는 `tracker.state_file`이 필수입니다. 기본 정책에서는 `checks`와 `allowed_paths`를 생략할 수 있습니다. 원문 Markdown을 수정하거나 필수 YAML header를 추가하지 않습니다.

```text
do-spec plan --project <project.json>
do-spec start --plan <printed-plan-file>
do-spec ui --project <project.json> --port 18080
```

기존 Dagu UI의 builtin 인증을 유지합니다. `pause`는 다음 issue 경계, `stop`은 현재 process tree 종료 요청입니다. raw Retry는 보호 검사를 우회하지 않습니다. Cline의 지원 범위는 **Windows 3.0.61 + 로컬 tracker**이며, 원격 gh/tea 연결 회귀는 합성 CLI를 사용합니다. 전체 PRD MVP 완료를 의미하지 않습니다.

```powershell
$env:PYTHONPATH='src'
$env:DO_SPEC_DAGU=(Resolve-Path .tools/dagu.exe).Path
python -m unittest discover -s tests -v
```

명시적 `completion: external-checkpoint`는 과거 회귀용 정책으로 유지합니다. 기존 immutable plan을 새 의미로 자동 변경하지 않습니다. 버전 변경 전 실패 worktree와 로그는 보존하세요. 제거는 `python -m pip uninstall do-spec`; 데이터 자동 삭제·reset·force push는 없습니다.
