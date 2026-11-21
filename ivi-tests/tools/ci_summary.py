"""GitHub Actions 실행 요약($GITHUB_STEP_SUMMARY)에 붙일 줄. 테스트 수를 문서에 손으로 적지 않고 그 실행에서 센다.

    python tools/ci_summary.py junit unit reports/junit-unit.xml
    python tools/ci_summary.py junit "app unit" ../ivi-app/app/build/test-results/testDebugUnitTest/*.xml
    python tools/ci_summary.py trace     # 요구사항 ↔ 테스트 함수 추적, 빠진 곳 수 (docs/traceability.md 는 쓰지 않는다)
    python tools/ci_summary.py links     # 문서·사이트의 끊긴 내부 링크 수

ivi-ci.yml 의 build, unit job 이 마지막 단계에서 부른다. 이 스크립트는 판정하지 않는다(종료 코드 0). 실패는 각 단계가 낸다.
"""
import glob
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # ivi-tests/
sys.path.insert(0, str(ROOT))


def junit_counts(paths):
    """JUnit XML(pytest 의 testsuites, Gradle 의 testsuite)에서 tests, failures, errors, skipped 합."""
    total = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    files = [f for pattern in paths for f in (glob.glob(pattern) or [pattern])]
    for path in files:
        if not Path(path).is_file():
            continue
        root = ET.parse(path).getroot()
        for suite in root.iter("testsuite"):
            for key in total:
                total[key] += int(suite.get(key, 0) or 0)
    return total, len([f for f in files if Path(f).is_file()])


def junit_line(label, paths):
    counts, files = junit_counts(paths)
    if not files:
        return f"- {label}: 결과 파일 없음 (테스트 단계가 돌기 전에 멈춤)"
    passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    return (f"- {label} {passed} passed (failed {counts['failures']}, error {counts['errors']}, "
            f"skipped {counts['skipped']})")


def trace_line():
    from tools import trace_report
    requirements, tests = trace_report.read_requirements(), trace_report.read_test_reqs()
    untested, untraced, unknown = trace_report.check(requirements, tests)
    stale = trace_report.check_conditions(trace_report.read_conditions(), tests)
    missing = len(untested) + len(untraced) + len(unknown)
    return (f"- trace 요구사항 {len(requirements)} ↔ 테스트 함수 {len(tests)}, 누락 {missing}"
            f" (조건 표 어긋남 {len(stale)})")


def links_line():
    from tools import check_links
    return f"- links 끊긴 내부 링크 {len(check_links.check())}"


def main(argv):
    if not argv:
        sys.exit(__doc__)
    kind, rest = argv[0], argv[1:]
    if kind == "junit":
        print(junit_line(rest[0], rest[1:]))
    elif kind == "trace":
        print(trace_line())
    elif kind == "links":
        print(links_line())
    else:
        sys.exit(f"모르는 종류: {kind}")


if __name__ == "__main__":
    main(sys.argv[1:])
