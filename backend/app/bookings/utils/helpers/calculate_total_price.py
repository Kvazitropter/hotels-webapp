from decimal import Decimal


def calculate_final_price_per_night(
    adults_count: int, children_count: int, room_capacity: int,
    base_price: Decimal, extra_person_price: Decimal,
    discount: Decimal=Decimal(0)
) -> Decimal:
    people_count = adults_count + children_count
    extra_people_count = max(0, people_count - room_capacity)
    extra_pay = Decimal(extra_person_price * extra_people_count)
    price_part = Decimal((100 - discount) / 100)
    final_price_per_night = Decimal(price_part * (base_price + extra_pay))
    return final_price_per_night


def calculate_total_price(days: int=1, *args, **kwargs) -> Decimal:
    return Decimal(calculate_final_price_per_night(*args, **kwargs) * days)
