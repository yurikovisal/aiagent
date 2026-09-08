"""§9/§66: the final synthesis must never let the LLM's own phrasing override what the agents'
tool calls actually found — a small local model will occasionally claim 'no access to that data'
right after successfully retrieving it."""

from meza.orchestrator.core import _denies_available_data


def test_detects_common_denial_phrasings():
    assert _denies_available_data("Извините, но я не могу предоставить информацию о складе.")
    assert _denies_available_data("В данный момент у меня нет доступа к этим данным.")
    assert _denies_available_data("Недостаточно данных для ответа.")


def test_does_not_flag_normal_answers():
    assert not _denies_available_data("На складе 700 кг трубы, что выше минимума в 500 кг.")
    assert not _denies_available_data("Заказ AT-1001 задерживается из-за нехватки материала.")
