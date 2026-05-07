from django.db import models
from django.apps import apps


class RoomQuerySet(models.QuerySet):
    def annotate_is_premium(self):
        RoomCategory = apps.get_model('hotels', 'RoomCategory')
        return self.annotate(
            is_premium=models.Case(
                models.When(
                    room_type__category__tier__in=RoomCategory.PREMIUM_TIERS,
                    then=models.Value(True)
                ),
                default=models.Value(False),
                output_field=models.BooleanField(),
            )
        )

    def annotate_is_standard(self):
        RoomCategory = apps.get_model('hotels', 'RoomCategory')
        return self.annotate(
            is_standard=models.Case(
                models.When(
                    room_type__category__tier__in=RoomCategory.STANDARD_TIERS,
                    then=models.Value(True)
                ),
                default=models.Value(False),
                output_field=models.BooleanField(),
            )
        )


class RoomManager(models.Manager):
    def get_queryset(self):
        return RoomQuerySet(self.model, using=self._db)

    def available(self, check_in, check_out):
        Booking = apps.get_model('bookings', 'Booking')
        overlapping = Booking.objects.filter(
            room=models.OuterRef('pk'),
            status=Booking.Status.ACTIVE,
            check_in__lt=check_out,
            check_out__gt=check_in
        )
        return self.get_queryset().filter(~models.Exists(overlapping))
