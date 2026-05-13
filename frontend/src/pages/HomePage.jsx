import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import usePageMeta from '../hooks/usePageMeta';
import { hotels } from '../data/hotels';

function HomePage() {
  usePageMeta(
    'HotelsWeb — поиск и бронирование гостиниц',
    'Главная страница веб-приложения HotelsWeb для поиска гостиниц, выбора дат проживания и перехода к каталогу отелей.'
  );

  const navigate = useNavigate();
  const [city, setCity] = useState('');
  const [checkInDate, setCheckInDate] = useState('');
  const [checkOutDate, setCheckOutDate] = useState('');

  const handleSearch = (event) => {
    event.preventDefault();

    const params = new URLSearchParams();

    if (city.trim()) {
      params.set('city', city.trim());
    }

    if (checkInDate) {
      params.set('check_in', checkInDate);
    }

    if (checkOutDate) {
      params.set('check_out', checkOutDate);
    }

    navigate(`/catalog?${params.toString()}`);
  };

  return (
    <main>
      <section className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-4 py-12 md:py-20">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold max-w-3xl leading-tight">
            Бронирование гостиниц в удобном веб-приложении
          </h1>
          <p className="mt-5 text-base md:text-lg text-slate-200 max-w-2xl">
            Найдите подходящую гостиницу, выберите номер и оформите бронирование за несколько шагов.
          </p>

          <form
            onSubmit={handleSearch}
            className="mt-8 md:mt-10 bg-white text-slate-900 rounded-2xl p-4 grid gap-4 md:grid-cols-5 shadow-lg"
            aria-label="Форма поиска гостиниц"
          >
            <label className="block md:col-span-2">
              <span className="text-sm text-slate-600">Город</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                placeholder="Например, Москва"
                value={city}
                onChange={(event) => setCity(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Дата заезда</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                type="date"
                value={checkInDate}
                onChange={(event) => setCheckInDate(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="text-sm text-slate-600">Дата выезда</span>
              <input
                className="w-full border rounded-xl px-4 py-3 mt-1"
                type="date"
                value={checkOutDate}
                onChange={(event) => setCheckOutDate(event.target.value)}
              />
            </label>

            <button className="bg-blue-600 text-white rounded-xl px-5 py-3 font-semibold hover:bg-blue-700 md:self-end">
              Найти
            </button>
          </form>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 py-10 md:py-12" aria-labelledby="popular-hotels-title">
        <h2 id="popular-hotels-title" className="text-2xl font-bold">
          Популярные гостиницы
        </h2>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          {hotels.map((hotel) => (
            <Link
              key={hotel.id}
              to={`/hotels/${hotel.id}`}
              className="bg-white rounded-2xl overflow-hidden shadow-sm border hover:shadow-md transition block"
              aria-label={`Открыть страницу гостиницы ${hotel.name}`}
            >
              <img src={hotel.image} alt={`Фотография гостиницы ${hotel.name}`} className="h-48 w-full object-cover" />
              <div className="p-5">
                <h3 className="text-xl font-semibold">{hotel.name}</h3>
                <p className="text-slate-500 mt-1">{hotel.city}</p>
                <p className="mt-3 font-semibold">от {hotel.priceFrom} ₽ / ночь</p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

export default HomePage;
