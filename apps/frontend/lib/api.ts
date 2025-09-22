export { API_BASE_URL, ApiError, apiRequest } from './http';

import {
  getDashboardReport as fetchDashboardReport,
  getDonations as fetchDonations,
  getEvents as fetchEvents,
  getHomeContent as fetchHomeContent,
  getPrayerRequests as fetchPrayerRequests
} from './generated/client';
import type {
  DashboardResponseDto,
  DonationsResponseDto,
  EventsResponseDto,
  HomeContentDto,
  PrayerRequestsResponseDto,
  GetDonationsParams,
  GetEventsParams
} from './generated/schemas';

export type PaginatedResponse<T> = {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
};

export type DashboardResponse = DashboardResponseDto;
export type HomeContentResponse = HomeContentDto;
export type EventsResponse = EventsResponseDto;
export type DonationsResponse = DonationsResponseDto;
export type PrayerRequestsResponse = PrayerRequestsResponseDto;

export async function getDashboardReport(): Promise<DashboardResponse> {
  const response = await fetchDashboardReport();
  return response.data;
}

export async function getHomeContent(): Promise<HomeContentResponse> {
  const response = await fetchHomeContent();
  return response.data;
}

export async function getUpcomingEvents(limit = 3): Promise<EventsResponse> {
  return getEvents({ page: 1, pageSize: limit });
}

export async function getEvents(
  params: GetEventsParams = { page: 1, pageSize: 25 }
): Promise<EventsResponse> {
  const response = await fetchEvents(params);
  return response.data;
}

export async function getDonations(
  params: GetDonationsParams = { page: 1, pageSize: 25 }
): Promise<DonationsResponse> {
  const response = await fetchDonations(params);
  return response.data;
}

export async function getPrayerRequests(): Promise<PrayerRequestsResponse> {
  const response = await fetchPrayerRequests();
  return response.data;
}
