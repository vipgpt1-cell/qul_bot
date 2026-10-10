from qul_bot.bot.callbacks import ListPage, TaskAction, decode_filter, encode_filter
from qul_bot.domain.enums import Priority, TaskStatus
from qul_bot.services.tasks import TaskFilter


def test_filter_round_trip_fits_telegram_limit() -> None:
    flt = TaskFilter(
        workspace_id=123456,
        area_id=98765,
        statuses=frozenset({TaskStatus.REVIEW, TaskStatus.BLOCKED, TaskStatus.CANCELLED}),
        priority=Priority.URGENT,
        assignee_id=424242,
        include_closed=True,
    )
    packed = encode_filter(flt, 17).pack()
    assert len(packed.encode()) <= 64
    decoded, page = decode_filter(ListPage.unpack(packed))
    assert decoded == flt
    assert page == 17


def test_empty_filter_round_trip() -> None:
    flt = TaskFilter(workspace_id=1)
    decoded, page = decode_filter(ListPage.unpack(encode_filter(flt, 0).pack()))
    assert decoded == flt
    assert page == 0


def test_task_action_packs_small() -> None:
    packed = TaskAction(action="approve", task_id=2_000_000_000).pack()
    assert len(packed.encode()) <= 64
