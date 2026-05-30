from bisect import bisect, bisect_left
from datetime import date

from django.db.models import QuerySet

from app.bookings.models import Booking
from app.hotels.models import Room


def get_booked_dates(
    room_qs: QuerySet[Room], after: date | None = None,
    before: date | None = None
) -> dict[int, list[tuple[date, date]]]:
    qs = Booking.objects.filter(
        room__in=room_qs,
        status__in=[Booking.Status.ACTIVE, Booking.Status.CLOSED],
    )

    if after is not None:
        qs = qs.filter(check_out_date__gt=after)
    if before is not None:
        qs = qs.filter(check_in_date__lt=before)

    bookings = qs.order_by('check_in_date', 'check_out_date') \
        .values_list('room_id', 'check_in_date', 'check_out_date')

    periods = {}
    for room in room_qs:
        periods[room.pk] = []
    for room_id, after, later in bookings:
        periods[room_id].append((after, later))
    return periods


# def insert_booked_dates(
#     booking_dates: list[tuple[date, date]], after: date, later
# ) -> list[tuple[date, date]]:
#     inx = bisect([dates[0] for dates in booking_dates], after)
#     booking_dates.insert(inx, (after, later))
#     return booking_dates


def get_vacant_dates(
    room_qs: QuerySet[Room], after: date | None = None,
    before: date | None = None
) -> dict[int, list[tuple[date, date]]]:
    booked = get_booked_dates(room_qs, after, before)
    vacant = {}

    for room_id, bookings in booked.items():
        vacant[room_id] = gaps = []
        if not bookings:
            gaps.append((after, before))
            continue
        gaps.append((after, bookings[0][0]))
        for (_, prev_out), (next_in, _) in zip(bookings, bookings[1:]):
            if next_in > prev_out:
                gaps.append((prev_out, next_in))
        gaps.append((bookings[-1][1], before))

    return vacant


def free_vacant(
    vacant_dates: list[tuple[date, date]], after: date, before: date
) -> list[tuple[date, date]]:
    inx1 = bisect([dates[1] for dates in vacant_dates], after)
    inx2 = bisect_left([dates[0] for dates in vacant_dates], before)

    left = vacant_dates[inx1] if inx1 < len(vacant_dates) else None
    right = vacant_dates[inx2] if inx2 < len(vacant_dates) else None

    new_start = min(after, left[0]) if left else after
    new_end = max(before, right[1]) if right else before

    end_idx = (inx2 + 1) if right else inx1
    vacant_dates[inx1:end_idx] = [(new_start, new_end)]

    return vacant_dates
