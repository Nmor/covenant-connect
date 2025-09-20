import { Injectable } from '@nestjs/common';

import type { HomeContent, PaginatedResult, Sermon } from '@covenant-connect/shared';

@Injectable()
export class ContentService {
  private readonly sermons: Sermon[] = [];
  private homeContent: HomeContent = {
    heroTitle: 'Welcome to Covenant Connect',
    heroSubtitle: 'A modern ministry platform for churches.',
    highlights: ['Plan services', 'Track follow-ups', 'Unify communications'],
    nextSteps: [
      { label: 'Plan a visit', url: '/plan-visit' },
      { label: 'Give online', url: '/give' },
      { label: 'Join a group', url: '/groups' }
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
