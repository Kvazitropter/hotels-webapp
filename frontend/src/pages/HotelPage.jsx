import { Link, useParams } from 'react-router-dom';
import usePageMeta from '../hooks/usePageMeta';
import { hotels } from '../data/hotels';

function HotelPage() {
  usePageMeta(
    'HotelsWeb — информация о гостинице',
    'Страница гостиницы HotelsWeb с описанием отеля, удобствами, стоимостью проживания и списком доступных номеров.'
  );

  const { id } = useParams();
  const hotel = hotels.find((item) => item.id === Number(id));

  if (!hotel) {
    return (
      <main className="max-w-6xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold">Гостиница не найдена</h1>
        <p className="text-slate-600 mt-3">
          Проверьте ссылку или вернитесь в каталог гостиниц.
        </p>
        <Link
          to="/catalog"
          className="inline-block mt-6 bg-blue-600 text-white rounded-xl px-5 py-3 font-semibold hover:bg-blue-700"
        >
          Вернуться в каталог
        </Link>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-4 py-8 md:py-10">
      <img
        src={hotel.image}
        alt={`Фотография гостиницы ${hotel.name}`}
        className="w-full h-56 sm:h-72 md:h-96 object-cover rounded-3xl"
      />

      <div className="mt-8 grid lg:grid-cols-[1fr_320px] gap-6 lg:gap-8">
        <section aria-labelledby="hotel-title">
          <h1 id="hotel-title" className="text-3xl md:text-4xl font-bold">
            {hotel.name}
          </h1>

          <p className="text-slate-500 mt-2">
            {hotel.city} · ★ {hotel.rating}
          </p>

          <p className="text-slate-700 mt-5 leading-7">
            {hotel.description}
          </p>

          <section className="mt-8" aria-labelledby="amenities-title">
            <h2 id="amenities-title" className="text-2xl font-bold">
              Удобства
            </h2>

            <div className="flex flex-wrap gap-2 mt-4" aria-label={`Удобства гостиницы ${hotel.name}`}>
              {hotel.amenities.map((item) => (
                <span key={item} className="bg-slate-100 rounded-full px-4 py-2">
                  {item}
                </span>
              ))}
            </div>
          </section>

          <section className="mt-8" aria-labelledby="rooms-title">
            <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
              <div>
                <h2 id="rooms-title" className="text-2xl font-bold">
                  Доступные номера
                </h2>
                <p className="text-slate-600 mt-2">
                  Выберите подходящий номер и перейдите к оформлению бронирования.
                </p>
              </div>
            </div>

            <div className="space-y-4 mt-4">
              {hotel.rooms.map((room) => (
                <article
                  key={room.id}
                  className="bg-white border rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
                >
                  <div>
                    <h3 className="text-lg font-semibold">{room.title}</h3>
                    <p className="text-slate-500 mt-1">
                      До {room.capacity} гостей
                    </p>
                  </div>

                  <div className="sm:text-right">
                    <p className="font-bold">{room.price} ₽ / ночь</p>
                    <Link
                      to={`/booking/${hotel.id}/${room.id}`}
                      className="inline-block w-full sm:w-auto text-center mt-3 bg-blue-600 text-white rounded-xl px-4 py-2 font-semibold hover:bg-blue-700"
                      aria-label={`Забронировать номер ${room.title} в гостинице ${hotel.name}`}
                    >
                      Забронировать
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </section>

        <aside className="bg-white rounded-2xl border p-6 h-fit shadow-sm" aria-label="Краткая информация о гостинице">
          <h2 className="text-xl font-bold">Краткая информация</h2>

          <div className="grid gap-4 mt-4">
            <div>
              <p className="text-slate-600">Стоимость от</p>
              <p className="text-2xl font-bold">{hotel.priceFrom} ₽ / ночь</p>
            </div>

            <div>
              <p className="text-slate-600">Рейтинг</p>
              <p className="text-xl font-bold">★ {hotel.rating}</p>
            </div>

            <div>
              <p className="text-slate-600">Количество доступных номеров</p>
              <p className="text-xl font-bold">{hotel.rooms.length}</p>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

export default HotelPage;
