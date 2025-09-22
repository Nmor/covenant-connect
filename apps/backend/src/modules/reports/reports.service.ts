import { Injectable } from '@nestjs/common';
import type { DashboardKpi } from '@covenant-connect/shared';

import { DonationsService } from '../donations/donations.service';
import { EventsService } from '../events/events.service';
import { PrayerService } from '../prayer/prayer.service';

@Injectable()
export class ReportsService {
  constructor(
    private readonly donations: DonationsService,
    private readonly prayer: PrayerService,
    private readonly events: EventsService
  ) {}

  async getDashboard(): Promise<{ kpis: DashboardKpi[] }> {
    const donationsList = await this.donations.list({ page: 1, pageSize: 100 });
    const upcomingEvents = await this.events.list({ page: 1, pageSize: 50 });
    const prayerRequests = await this.prayer.list();

    const totalGiving = donationsList.data.reduce((sum, donation) => sum + donation.amount, 0);
    const completedDonations = donationsList.data.filter((donation) => donation.status === 'completed');

    const kpis: DashboardKpi[] = [
      { label: 'Total Giving', value: totalGiving },
      { label: 'Completed Donations', value: completedDonations.length },
      { label: 'Upcoming Events', value: upcomingEvents.data.length },
      { label: 'Open Prayer Requests', value: prayerRequests.data.filter((req) => req.status !== 'answered').length }
    ];

    return { kpis };
  }
}
