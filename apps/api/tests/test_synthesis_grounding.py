"""§9/§66: the final synthesis must never let the LLM's own phrasing override what the agents'
tool calls actually found — a small local model will occasionally claim 'no access to that data'
right after successfully retrieving it."""

from meza.agents.base import AgentResult
from meza.orchestrator.core import _denies_available_data, _has_pending_approval_action


def test_detects_common_denial_phrasings():
    assert _denies_available_data("Извините, но я не могу предоставить информацию о складе.")
    assert _denies_available_data("В данный момент у меня нет доступа к этим данным.")
    assert _denies_available_data("Недостаточно данных для ответа.")


def test_detects_denial_stem_variants_not_in_fixed_phrase_list():
    # ADR 0005 is a recurring bug class: the small local model keeps inventing new refusal
    # phrasings. These exact sentences were never in _DENIAL_PHRASES but must still be caught.
    assert _denies_available_data("Извините, но я не могу выполнить эту задачу.")
    assert _denies_available_data("Я не в состоянии обработать этот запрос.")
    assert _denies_available_data("Невозможно выполнить публикацию материала.")


def test_does_not_flag_normal_answers():
    assert not _denies_available_data("На складе 700 кг трубы, что выше минимума в 500 кг.")
    assert not _denies_available_data("Заказ AT-1001 задерживается из-за нехватки материала.")


def _result_with_pending_approval() -> AgentResult:
    return AgentResult(
        status="success", summary="Предложена публикация «Акция». Ожидает утверждения.",
        actions_proposed=[{"tool": "publish_content", "params": {"content_id": 1}, "pending_approval_id": 10}],
    )


def test_detects_pending_approval_action_in_results():
    successful = {"marketing": _result_with_pending_approval()}
    assert _has_pending_approval_action(successful)


def test_no_pending_approval_when_nothing_was_proposed():
    successful = {"warehouse": AgentResult(status="success", summary="На складе всё в порядке.")}
    assert not _has_pending_approval_action(successful)
