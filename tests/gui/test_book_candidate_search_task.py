"""候補検索ワーカーの重複要求・失敗・古い結果破棄を検証する。"""

from threading import Event
from time import monotonic, sleep

from book_manager.gui.book_candidate_search_dialog import CandidateSearchTask
from book_manager.metadata.exceptions import BookMetadataConnectionError


def finish(task):
    deadline = monotonic() + 2
    while task.busy and monotonic() < deadline:
        sleep(0.001)
    assert not task.busy


def test_worker_returns_candidates():
    calls = []
    def search(**kwargs):
        calls.append(kwargs)
        return ["candidate"]
    task = CandidateSearchTask()
    assert task.start(search, title="本", author="著者")
    finish(task)
    assert task.poll() == (["candidate"], None)
    assert task.poll() is None
    assert calls == [{"title": "本", "author": "著者", "publisher": "", "max_results": 20}]


def test_worker_rejects_overlapping_search():
    started, release = Event(), Event()
    calls = []
    def search(**kwargs):
        calls.append(kwargs)
        started.set()
        assert release.wait(2)
        return []
    task = CandidateSearchTask()
    try:
        assert task.start(search, title="本", author="")
        assert started.wait(2)
        assert not task.start(search, title="別の本", author="")
    finally:
        release.set()
    finish(task)
    assert len(calls) == 1


def test_worker_keeps_exception_without_retry():
    calls = []
    error = BookMetadataConnectionError("通信失敗")
    def search(**kwargs):
        calls.append(kwargs)
        raise error
    task = CandidateSearchTask()
    assert task.start(search, title="本", author="")
    finish(task)
    assert task.poll() == (None, error)
    assert len(calls) == 1


def test_new_search_discards_unconsumed_old_result():
    task = CandidateSearchTask()
    assert task.start(lambda **kwargs: ["old"], title="旧", author="")
    finish(task)
    assert task.start(lambda **kwargs: ["new"], title="新", author="")
    finish(task)
    assert task.poll() == (["new"], None)
    assert task.poll() is None


def test_worker_searches_by_publisher_only():
    calls = []
    task = CandidateSearchTask()
    assert task.start(lambda **kwargs: calls.append(kwargs) or [], title="", author="", publisher="集英社")
    finish(task)
    assert calls == [{"title": "", "author": "", "publisher": "集英社", "max_results": 20}]
    assert task.poll() == ([], None)


def test_detail_operation_returns_result_without_search():
    task = CandidateSearchTask()
    assert task.start_operation(lambda: "detail")
    finish(task)
    assert task.poll() == ("detail", None)
