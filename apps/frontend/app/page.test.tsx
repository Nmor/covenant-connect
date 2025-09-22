import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import HomePage from './page';
import {
  getDashboardReport,
  getHomeContent,
  getUpcomingEvents,
  type DashboardResponse,
  type EventsResponse,
  type HomeContentResponse,
} from '../lib/api';

vi.mock('../lib/api', () => ({
  getHomeContent: vi.fn(),
  getDashboardReport: vi.fn(),
  getUpcomingEvents: vi.fn(),
}));

describe('HomePage', () => {
  const mockHome = vi.mocked(getHomeContent);
  const mockReport = vi.mocked(getDashboardReport);
  const mockEvents = vi.mocked(getUpcomingEvents);

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders fallback content when API requests fail', async () => {
    mockHome.mockRejectedValueOnce(new Error('network error'));
    mockReport.mockRejectedValueOnce(new Error('network error'));
    mockEvents.mockRejectedValueOnce(new Error('network error'));

    const element = await HomePage();
    render(element);

    expect(
      screen.getByRole('heading', {
        name: /plan services and care pathways with ease/i,
      })
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /launch admin console/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /review giving activity/i })).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('displays API data when requests succeed', async () => {
    const home: HomeContentResponse = {
      heroTitle: 'Welcome to Covenant Connect',
      heroSubtitle: 'Plan ministry moments with clarity.',
      highlights: ['Track assimilation milestones'],
      nextSteps: [{ label: 'Open portal', url: '/portal' }],
    };
    const report: DashboardResponse = {
      kpis: [
        { label: 'Total Giving', value: 1234.56 },
        { label: 'Completed Donations', value: 8 },
        { label: 'Upcoming Events', value: 2 },
        { label: 'Open Prayer Requests', value: 1 },
      ],
    };
    const events: EventsResponse = {
      data: [
        {
          id: 'evt-1',
          title: 'Special Service',
          startsAt: '2024-03-01T18:00:00.000Z',
          endsAt: '2024-03-01T20:00:00.000Z',
          timezone: 'UTC',
          location: 'Sanctuary',
          recurrenceRule: undefined,
          tags: ['featured'],
        },
      ],
      total: 1,
      page: 1,
      pageSize: 3,
    };

    mockHome.mockResolvedValueOnce(home);
    mockReport.mockResolvedValueOnce(report);
    mockEvents.mockResolvedValueOnce(events);

    const element = await HomePage();
    render(element);

    expect(screen.getByRole('heading', { name: /welcome to covenant connect/i })).toBeInTheDocument();
    expect(screen.getByText(/plan ministry moments/i)).toBeInTheDocument();
    expect(screen.getByText(/track assimilation milestones/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open portal/i })).toBeInTheDocument();
    expect(screen.getByText(/1,234.56/)).toBeInTheDocument();
    expect(screen.getByText('Special Service')).toBeInTheDocument();
  });
});
