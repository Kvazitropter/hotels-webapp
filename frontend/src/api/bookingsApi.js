import { apiRequest } from './client';

export function createBooking(bookingData) {
  return apiRequest('/me/bookings/', {
    method: 'POST',
    body: JSON.stringify(bookingData),
  });
}

export function getMyBookings(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, value);
    }
  });

  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/me/bookings/${query}`);
}

export function getMyBookingById(id) {
  return apiRequest(`/me/bookings/${id}/`);
}

export function cancelBooking(id, reason) {
  return apiRequest(`/me/bookings/${id}/cancel/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export function moveBooking(id, dates) {
  return apiRequest(`/me/bookings/${id}/move/`, {
    method: 'POST',
    body: JSON.stringify(dates),
  });
}
