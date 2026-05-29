import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { hotels } from '../data/hotels';
import usePageMeta from '../hooks/usePageMeta';

function BookingPage() {
  usePageMeta(
    'HotelsWeb — оформление бронирования',
    'Страница оформления бронирования гостиничного номера с контактными данными, датами проживания и параметрами гостей.'
  );
  const navigate = useNavigate();
  const { hotelId, roomId } = useParams();

  const hotel = hotels.find((item) => item.id === Number(hotelId));
  const room = hotel?.rooms.find((item) => item.id === Number(roomId));

  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    checkInDate: '',
    checkOutDate: '',
    adultsCount: 1,
    childrenCount: 0,
    petsCount: 0,
  });

  const [errors, setErrors] = useState({});

  const totalGuests = useMemo(() => {
    return Number(formData.adultsCount) + Number(formData.childrenCount);
  }, [formData.adultsCount, formData.childrenCount]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((currentData) => ({
      ...currentData,
      [name]: value,
    }));

    setErrors((currentErrors) => ({
      ...currentErrors,
      [name]: '',
      form: '',
    }));
  };

  const validateForm = () => {
    const nextErrors = {};

    if (!formData.firstName.trim()) {
      nextErrors.firstName = 'Укажите имя';
    }

    if (!formData.lastName.trim()) {
      nextErrors.lastName = 'Укажите фамилию';
    }

    if (!formData.email.trim()) {
      nextErrors.email = 'Укажите email';
    }

    if (!formData.phone.trim()) {
      nextErrors.phone = 'Укажите телефон';
    }

    if (!formData.checkInDate) {
      nextErrors.checkInDate = 'Выберите дату заезда';
    }

    if (!formData.checkOutDate) {
      nextErrors.checkOutDate = 'Выберите дату выезда';
    }

    if (formData.checkInDate && formData.checkOutDate && formData.checkOutDate <= formData.checkInDate) {
      nextErrors.checkOutDate = 'Дата выезда должна быть позже даты заезда';
    }

    if (Number(formData.adultsCount) < 1) {
      nextErrors.adultsCount = 'Должен быть указан хотя бы один взрослый гость';
    }

    if (room && totalGuests > room.capacity) {
      nextErrors.form = `Выбранный номер рассчитан максимум на ${room.capacity} гостей`;
    }

    return nextErrors;
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    const validationErrors = validateForm();

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    const bookingPayload = {
      room_id: Number(roomId),
      check_in_date: formData.checkInDate,
      check_out_date: formData.checkOutDate,
      adults_count: Number(formData.adultsCount),
      children_count: Number(formData.childrenCount),
      pets_count: Number(formData.petsCount),
    };

    console.log('Booking payload for API:', bookingPayload);

    navigate('/success');
  };

  if (!hotel || !room) {
    return <main className="max-w-6xl mx-auto px-4 py-10">Данные бронирования не найдены</main>;
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold">Оформление бронирования</h1>
      <p className="text-slate-600 mt-2">
        Заполните контактные данные и параметры проживания для подтверждения бронирования.
      </p>

      <div className="bg-white rounded-2xl border p-6 mt-6 shadow-sm">
        <h2 className="text-xl font-bold">{hotel.name}</h2>
        <p className="text-slate-600 mt-1">{room.title}</p>
        <p className="text-slate-600 mt-1">Вместимость: до {room.capacity} гостей</p>
        <p className="font-bold mt-3">{room.price} ₽ / ночь</p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="bg-white rounded-2xl border p-6 mt-6 shadow-sm grid gap-5">
        {errors.form && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3">
            {errors.form}
          </div>
        )}

        <section>
          <h2 className="text-xl font-bold">Контактные данные</h2>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <label className="block">
              <span className="text-sm text-slate-600">Имя</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="firstName"
                placeholder="Иван"
                value={formData.firstName}
                onChange={handleChange}
                aria-invalid={Boolean(errors.firstName)}
              />
              {errors.firstName && <span className="text-sm text-red-600">{errors.firstName}</span>}
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Фамилия</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="lastName"
                placeholder="Иванов"
                value={formData.lastName}
                onChange={handleChange}
                aria-invalid={Boolean(errors.lastName)}
              />
              {errors.lastName && <span className="text-sm text-red-600">{errors.lastName}</span>}
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Email</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="email"
                type="email"
                placeholder="user@example.com"
                value={formData.email}
                onChange={handleChange}
                aria-invalid={Boolean(errors.email)}
              />
              {errors.email && <span className="text-sm text-red-600">{errors.email}</span>}
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Телефон</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="phone"
                type="tel"
                placeholder="+7 912 345-67-89"
                value={formData.phone}
                onChange={handleChange}
                aria-invalid={Boolean(errors.phone)}
              />
              {errors.phone && <span className="text-sm text-red-600">{errors.phone}</span>}
            </label>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold">Параметры проживания</h2>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <label className="block">
              <span className="text-sm text-slate-600">Дата заезда</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="checkInDate"
                type="date"
                value={formData.checkInDate}
                onChange={handleChange}
                aria-invalid={Boolean(errors.checkInDate)}
              />
              {errors.checkInDate && <span className="text-sm text-red-600">{errors.checkInDate}</span>}
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Дата выезда</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="checkOutDate"
                type="date"
                value={formData.checkOutDate}
                onChange={handleChange}
                aria-invalid={Boolean(errors.checkOutDate)}
              />
              {errors.checkOutDate && <span className="text-sm text-red-600">{errors.checkOutDate}</span>}
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Взрослые</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="adultsCount"
                type="number"
                min="1"
                value={formData.adultsCount}
                onChange={handleChange}
                aria-invalid={Boolean(errors.adultsCount)}
              />
              {errors.adultsCount && <span className="text-sm text-red-600">{errors.adultsCount}</span>}
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Дети</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="childrenCount"
                type="number"
                min="0"
                value={formData.childrenCount}
                onChange={handleChange}
              />
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Животные</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                name="petsCount"
                type="number"
                min="0"
                value={formData.petsCount}
                onChange={handleChange}
              />
            </label>

          </div>
        </section>

        <button className="bg-blue-600 text-white rounded-xl px-5 py-3 font-semibold hover:bg-blue-700">
          Подтвердить бронирование
        </button>
      </form>
    </main>
  );
}

export default BookingPage;
