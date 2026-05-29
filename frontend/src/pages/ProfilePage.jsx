import { useMemo, useState } from 'react';
import usePageMeta from '../hooks/usePageMeta';

const bookingStatusLabels = {
  A: 'Активно',
  M: 'Перенесено',
  CA: 'Отменено',
  CL: 'Завершено',
};

const bookingTypeLabels = {
  G: 'Гарантированное',
  N: 'Негарантированное',
};

const mockBookings = [
  {
    id: 42,
    hotel_name: 'Grand Hotel Neva',
    room_number: '205A',
    room_type_name: 'Стандартный номер',
    check_in_date: '2026-06-01',
    check_out_date: '2026-06-07',
    days_count: 6,
    adults_count: 2,
    children_count: 1,
    pets_count: 0,
    status: 'A',
    status_display: 'Активно',
    type: 'G',
    created_at: '2026-05-01T12:00:00Z',
  },
  {
    id: 43,
    hotel_name: 'Hotel Moscow Garden',
    room_number: '312',
    room_type_name: 'Улучшенный номер',
    check_in_date: '2026-04-10',
    check_out_date: '2026-04-12',
    days_count: 2,
    adults_count: 1,
    children_count: 0,
    pets_count: 0,
    status: 'CL',
    status_display: 'Завершено',
    type: 'N',
    created_at: '2026-03-25T09:30:00Z',
  },
  {
    id: 44,
    hotel_name: 'Sochi Sea Resort',
    room_number: '118',
    room_type_name: 'Люкс',
    check_in_date: '2026-07-15',
    check_out_date: '2026-07-20',
    days_count: 5,
    adults_count: 2,
    children_count: 0,
    pets_count: 1,
    status: 'CA',
    status_display: 'Отменено',
    type: 'G',
    created_at: '2026-05-05T18:45:00Z',
  },
];

function ProfilePage() {
  usePageMeta(
    'HotelsWeb — личный кабинет пользователя',
    'Личный кабинет HotelsWeb для просмотра профиля пользователя, статистики бронирований и управления активными заявками.'
  );
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [bookings, setBookings] = useState(mockBookings);
  const [message, setMessage] = useState('');

  const filteredBookings = useMemo(() => {
    if (statusFilter === 'ALL') {
      return bookings;
    }

    return bookings.filter((booking) => booking.status === statusFilter);
  }, [bookings, statusFilter]);

  const bookingStats = useMemo(() => {
    return {
      total: bookings.length,
      active: bookings.filter((booking) => booking.status === 'A').length,
      completed: bookings.filter((booking) => booking.status === 'CL').length,
      cancelled: bookings.filter((booking) => booking.status === 'CA').length,
    };
  }, [bookings]);

  const handleCancelBooking = (bookingId) => {
    setBookings((currentBookings) =>
      currentBookings.map((booking) =>
        booking.id === bookingId
          ? {
              ...booking,
              status: 'CA',
              status_display: 'Отменено',
            }
          : booking
      )
    );

    setMessage('Бронирование отменено. В рабочей версии запрос будет отправлен на backend.');
  };

  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold">Личный кабинет</h1>
        <p className="text-slate-600">
          В личном кабинете пользователь может просматривать профиль, отслеживать бронирования и управлять активными заявками.
        </p>
      </div>

      <section className="bg-white rounded-2xl border p-6 mt-6 shadow-sm">
        <h2 className="text-xl font-bold">Профиль пользователя</h2>
        <div className="grid md:grid-cols-2 gap-4 mt-4 text-slate-700">
          <p>
            <span className="font-semibold">Имя:</span> Иван Петров
          </p>
          <p>
            <span className="font-semibold">Email:</span> ivan@example.com
          </p>
          <p>
            <span className="font-semibold">Телефон:</span> +7 912 345-67-89
          </p>
          <p>
            <span className="font-semibold">Роль:</span> Гость
          </p>
        </div>
      </section>

      <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6" aria-label="Статистика бронирований">
        <div className="bg-white rounded-2xl border p-5 shadow-sm">
          <p className="text-slate-500">Всего</p>
          <p className="text-3xl font-bold mt-2">{bookingStats.total}</p>
        </div>
        <div className="bg-white rounded-2xl border p-5 shadow-sm">
          <p className="text-slate-500">Активные</p>
          <p className="text-3xl font-bold mt-2">{bookingStats.active}</p>
        </div>
        <div className="bg-white rounded-2xl border p-5 shadow-sm">
          <p className="text-slate-500">Завершённые</p>
          <p className="text-3xl font-bold mt-2">{bookingStats.completed}</p>
        </div>
        <div className="bg-white rounded-2xl border p-5 shadow-sm">
          <p className="text-slate-500">Отменённые</p>
          <p className="text-3xl font-bold mt-2">{bookingStats.cancelled}</p>
        </div>
      </section>

      <section className="bg-white rounded-2xl border p-6 mt-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">Мои бронирования</h2>
            <p className="text-slate-600 mt-1">
              Здесь отображаются бронирования пользователя и их текущий статус.
            </p>
          </div>

          <label className="block md:w-64">
            <span className="text-sm text-slate-600">Фильтр по статусу</span>
            <select
              className="w-full border rounded-xl px-4 py-3 mt-1"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              aria-label="Фильтр бронирований по статусу"
            >
              <option value="ALL">Все бронирования</option>
              <option value="A">Активные</option>
              <option value="M">Перенесённые</option>
              <option value="CA">Отменённые</option>
              <option value="CL">Завершённые</option>
            </select>
          </label>
        </div>

        {message && (
          <div className="bg-blue-50 border border-blue-200 text-blue-700 rounded-xl px-4 py-3 mt-5">
            {message}
          </div>
        )}

        <div className="grid gap-4 mt-5">
          {filteredBookings.length === 0 && (
            <div className="border rounded-2xl p-6 text-slate-600">
              Бронирования с выбранным статусом не найдены.
            </div>
          )}

          {filteredBookings.map((booking) => (
            <article key={booking.id} className="border rounded-2xl p-5">
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-lg font-bold">{booking.hotel_name}</h3>
                    <span className="bg-slate-100 rounded-full px-3 py-1 text-sm">
                      {bookingStatusLabels[booking.status] || booking.status_display}
                    </span>
                  </div>

                  <p className="text-slate-600 mt-2">
                    {booking.room_type_name}, номер {booking.room_number}
                  </p>

                  <div className="grid sm:grid-cols-2 gap-2 mt-4 text-slate-700">
                    <p>
                      <span className="font-semibold">Заезд:</span> {booking.check_in_date}
                    </p>
                    <p>
                      <span className="font-semibold">Выезд:</span> {booking.check_out_date}
                    </p>
                    <p>
                      <span className="font-semibold">Ночей:</span> {booking.days_count}
                    </p>
                    <p>
                      <span className="font-semibold">Тип:</span> {bookingTypeLabels[booking.type]}
                    </p>
                    <p>
                      <span className="font-semibold">Взрослые:</span> {booking.adults_count}
                    </p>
                    <p>
                      <span className="font-semibold">Дети:</span> {booking.children_count}
                    </p>
                    <p>
                      <span className="font-semibold">Животные:</span> {booking.pets_count}
                    </p>
                  </div>
                </div>

                <div className="flex flex-col gap-2 min-w-48">
                  {booking.status === 'A' && (
                    <button
                      className="border border-red-200 text-red-700 rounded-xl px-4 py-3 font-semibold hover:bg-red-50"
                      onClick={() => handleCancelBooking(booking.id)}
                    >
                      Отменить бронирование
                    </button>
                  )}
                  <button className="border rounded-xl px-4 py-3 font-semibold hover:bg-slate-50">
                    Подробнее
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export default ProfilePage;
