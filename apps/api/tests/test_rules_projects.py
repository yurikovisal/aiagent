from datetime import datetime, timedelta

from meza.rules.projects import TaskNode, analyze_project_delay


def test_finds_root_cause_through_dependency_chain():
    now = datetime(2026, 9, 8, 12, 0)
    tasks = [
        TaskNode(1, "Согласовать спецификацию", "OPEN", now - timedelta(days=3), None, "Иванов"),
        TaskNode(2, "Заказать материал", "OPEN", now - timedelta(days=1), 1, "Петров"),
        TaskNode(3, "Начать производство", "OPEN", now + timedelta(days=1), 2, "Сидоров"),
    ]
    analysis = analyze_project_delay(tasks, now)
    assert analysis.root_cause is not None
    assert analysis.root_cause.task_id == 1
    assert [s.task_id for s in analysis.chain] == [1, 2, 3]


def test_no_overdue_or_blocked_tasks_returns_no_root_cause():
    now = datetime(2026, 9, 8, 12, 0)
    tasks = [TaskNode(1, "Задача", "OPEN", now + timedelta(days=5), None)]
    analysis = analyze_project_delay(tasks, now)
    assert analysis.root_cause is None
    assert analysis.overdue_task_count == 0


def test_done_task_is_never_the_root_cause():
    now = datetime(2026, 9, 8, 12, 0)
    tasks = [
        TaskNode(1, "Завершённая", "DONE", now - timedelta(days=5), None),
        TaskNode(2, "Просроченная", "OPEN", now - timedelta(days=1), 1),
    ]
    analysis = analyze_project_delay(tasks, now)
    assert analysis.root_cause is not None
    assert analysis.root_cause.task_id == 2


def test_blocked_task_without_due_date_still_detected():
    now = datetime(2026, 9, 8, 12, 0)
    tasks = [TaskNode(1, "Заблокирована поставщиком", "BLOCKED", None, None)]
    analysis = analyze_project_delay(tasks, now)
    assert analysis.root_cause is not None
    assert analysis.blocked_task_count == 1


def test_cycle_guard_does_not_infinite_loop():
    now = datetime(2026, 9, 8, 12, 0)
    tasks = [
        TaskNode(1, "A", "OPEN", now - timedelta(days=1), 2),
        TaskNode(2, "B", "OPEN", now - timedelta(days=1), 1),
    ]
    analysis = analyze_project_delay(tasks, now)
    assert analysis.root_cause is not None
    assert len(analysis.chain) <= 2
