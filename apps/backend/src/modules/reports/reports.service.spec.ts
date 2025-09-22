import type { Donation, Event, PaginatedResult, PrayerRequest } from '@covenant-connect/shared';

import { ReportsService } from './reports.service';
import type { DonationsService } from '../donations/donations.service';
import type { EventsService } from '../events/events.service';
import type { PrayerService } from '../prayer/prayer.service';

type DonationsServiceMock = Pick<DonationsService, 'list'>;
type EventsServiceMock = Pick<EventsService, 'list'>;
type PrayerServiceMock = Pick<PrayerService, 'list'>;

describe('ReportsService', () => {
  let donations: jest.Mocked<DonationsServiceMock>;
  let events: jest.Mocked<EventsServiceMock>;
  let prayer: jest.Mocked<PrayerServiceMock>;
  let service: ReportsService;

  beforeEach(() => {
    donations = { list: jest.fn() } as unknown as jest.Mocked<DonationsServiceMock>;
    events = { list: jest.fn() } as unknown as jest.Mocked<EventsServiceMock>;
    prayer = { list: jest.fn() } as unknown as jest.Mocked<PrayerServiceMock>;

    service = new ReportsService(
      donations as unknown as DonationsService,
      prayer as unknown as PrayerService,
      events as unknown as EventsService
    );
  });

  it('summarises core KPIs from donations, events, and prayer requests', async () => {
    const donationRecords: Donation[] = [
      {
        id: 'don-1',
        memberId: '12',
        amount: 50,
        currency: 'USD',
        provider: 'paystack',
        status: 'completed',
        metadata: {},
        createdAt: new Date('2024-01-01T00:00:00.000Z'),
        updatedAt: new Date('2024-01-01T00:00:00.000Z'),
      },
      {
        id: 'don-2',
        memberId: null,
        amount: 25,
        currency: 'USD',
        provider: 'stripe',
        status: 'pending',
        metadata: {},
        createdAt: new Date('2024-01-02T00:00:00.000Z'),
        updatedAt: new Date('2024-01-02T00:00:00.000Z'),
      },
    ];

    const upcomingEvents: PaginatedResult<Event> = {
      data: [
        {
          id: 'event-1',
          title: 'Community Night',
          description: 'Gathering for families',
          startsAt: new Date('2024-02-01T18:00:00.000Z'),
          endsAt: new Date('2024-02-01T20:00:00.000Z'),
          timezone: 'UTC',
          recurrenceRule: undefined,
          segments: [],
          tags: [],
          location: 'Main Hall',
          createdAt: new Date('2024-01-01T00:00:00.000Z'),
          updatedAt: new Date('2024-01-01T00:00:00.000Z'),
        },
        {
          id: 'event-2',
          title: 'Volunteer Training',
          description: 'Orientation for new volunteers',
          startsAt: new Date('2024-02-05T18:00:00.000Z'),
          endsAt: new Date('2024-02-05T19:30:00.000Z'),
          timezone: 'UTC',
          recurrenceRule: undefined,
          segments: [],
          tags: [],
          location: 'Room 201',
          createdAt: new Date('2024-01-02T00:00:00.000Z'),
          updatedAt: new Date('2024-01-02T00:00:00.000Z'),
        },
      ],
      total: 2,
      page: 1,
      pageSize: 50,
    };

    const prayerRequests: PaginatedResult<PrayerRequest> = {
      data: [
        {
          id: 'prayer-1',
          requesterName: 'Ada Lovelace',
          requesterEmail: 'ada@example.com',
          requesterPhone: undefined,
          message: 'Pray for upcoming outreach',
          memberId: undefined,
          status: 'new',
          followUpAt: undefined,
          createdAt: new Date('2024-01-03T00:00:00.000Z'),
          updatedAt: new Date('2024-01-03T00:00:00.000Z'),
        },
        {
          id: 'prayer-2',
          requesterName: 'Alan Turing',
          requesterEmail: undefined,
          requesterPhone: undefined,
          message: 'Thanksgiving for answered prayer',
          memberId: undefined,
          status: 'answered',
          followUpAt: undefined,
          createdAt: new Date('2024-01-04T00:00:00.000Z'),
          updatedAt: new Date('2024-01-04T00:00:00.000Z'),
        },
      ],
      total: 2,
      page: 1,
      pageSize: 2,
    };

    donations.list.mockResolvedValue({
      data: donationRecords,
      total: donationRecords.length,
      page: 1,
      pageSize: 100,
    });
    events.list.mockResolvedValue(upcomingEvents);
    prayer.list.mockResolvedValue(prayerRequests);

    const result = await service.getDashboard();

    expect(donations.list).toHaveBeenCalledWith({ page: 1, pageSize: 100 });
    expect(events.list).toHaveBeenCalledWith({ page: 1, pageSize: 50 });
    expect(prayer.list).toHaveBeenCalledTimes(1);

    expect(result.kpis).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: 'Total Giving', value: 75 }),
        expect.objectContaining({ label: 'Completed Donations', value: 1 }),
        expect.objectContaining({ label: 'Upcoming Events', value: 2 }),
        expect.objectContaining({ label: 'Open Prayer Requests', value: 1 }),
      ])
    );
  });
});
