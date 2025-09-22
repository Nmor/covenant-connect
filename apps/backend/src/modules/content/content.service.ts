import { Injectable } from '@nestjs/common';
import type { HomeContent, PaginatedResult, Sermon } from '@covenant-connect/shared';

@Injectable()
export class ContentService {
  private readonly sermons: Sermon[] = [];
  private homeContent: HomeContent = {
    heroTitle: 'Plan services and care pathways with ease',
    heroSubtitle:
      'The TypeScript rewrite ships with modular services for worship planning, assimilation, and giving.',
    highlights: [
      'Blueprint new gatherings with volunteer roles in minutes',
      'Automate next steps for guests and returning members',
      'Connect giving, pastoral care, and communications in one place'
    ],
    nextSteps: [
      { label: 'Launch admin console', url: '/dashboard' },
      { label: 'Browse events calendar', url: '/events' },
      { label: 'Review giving activity', url: '/donations' },
      { label: 'Manage prayer follow-up', url: '/prayer' },
      { label: 'Review API docs', url: '/docs' },
      { label: 'Explore product updates', url: '/changelog' }
    ]
  };

  async getHome(): Promise<HomeContent> {
    return this.homeContent;
  }

  async updateHome(content: Partial<HomeContent>): Promise<HomeContent> {
    this.homeContent = { ...this.homeContent, ...content };
    return this.homeContent;
  }

  async listSermons(): Promise<PaginatedResult<Sermon>> {
    return {
      data: this.sermons,
      total: this.sermons.length,
      page: 1,
      pageSize: this.sermons.length || 1
    };
  }

  async addSermon(sermon: Sermon): Promise<void> {
    this.sermons.push(sermon);
  }
}
