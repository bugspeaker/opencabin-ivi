"""문서·사이트 내부 링크 검사(tools/check_links.py). 저장소 전체에 끊긴 링크가 있으면 CI 의 unit job 이 실패한다."""
from tools import check_links


def test_docs_and_site_have_no_broken_internal_links():
    problems = check_links.check()
    assert problems == [], "끊긴 내부 링크:\n" + "\n".join(problems)


def test_slug_follows_github_heading_rule():
    assert check_links.slug("4-2. 서비스별 검증") == "4-2-서비스별-검증"
    assert check_links.slug("2. 화웨이 태블릿에서는 누르기만 adb로") == "2-화웨이-태블릿에서는-누르기만-adb로"
    assert check_links.slug('결과 <abbr title="뜻">VHAL</abbr>과 [링크](a.md) `코드`') == "결과-vhal과-링크-코드"


def test_finds_missing_file_and_missing_anchor(tmp_path):
    (tmp_path / "b.md").write_text("# 제목\n\n## 4-1. 게이트 단계와 기준\n\n## 같은 제목\n\n## 같은 제목\n", encoding="utf-8")
    page = tmp_path / "a.md"
    page.write_text(
        "[있음](b.md#4-1-게이트-단계와-기준) [두 번째](b.md#같은-제목-1) [바깥](https://example.com/#x)\n"
        "[파일 없음](c.md) [앵커 없음](b.md#없는-절) `[코드 안](d.md)`\n"
        "```\n[블록 안](e.md)\n```\n<img src=\"f.png\">\n", encoding="utf-8")
    problems = check_links.check_file(page, {})
    assert [p.split(": ", 1)[1] for p in problems] == ["c.md (파일 없음)", "b.md#없는-절 (앵커 없음)", "f.png (파일 없음)"]
