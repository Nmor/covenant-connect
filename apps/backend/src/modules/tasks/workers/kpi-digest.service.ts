import { Inject, Injectable, Logger } from '@nestjs/common';
import { Prisma } from '@prisma/client';

import { PrismaService } from '../../../prisma/prisma.service';
import { EmailService } from '../../email/email.service';

type DepartmentMetrics = {
  attendance: { checked: number; expected: number };
  volunteers: { assigned: number; needed: number };
};

type DigestMetrics = {
  start: Date;
  end: Date;
  departments: Map<string, DepartmentMetrics>;
  givingTotal: number;
  totalAttendance: { checked: number; expected: number };
  totalVolunteer: { assigned: number; needed: number };
  newMembers: number;
};

@Injectable()
export class KpiDigestService {
  private readonly logger = new Logger(KpiDigestService.name);

  constructor(
    @Inject(PrismaService) private readonly prisma: PrismaService,
    @Inject(EmailService) private readonly email: EmailService
  ) {}

  async sendDepartmentDigest(rangeDays: number): Promise<number> {
    const metrics = await this.collectMetrics(rangeDays);
    const departments = await this.prisma.ministryDepartment.findMany({
      where: { leadId: { not: null } },
      include: { lead: true }
    });

    let sent = 0;

    for (const department of departments) {
      const lead = department.lead;
      if (!lead?.email) {
        continue;
      }

      const departmentMetrics = metrics.departments.get(department.name) ?? {
        attendance: { checked: 0, expected: 0 },
        volunteers: { assigned: 0, needed: 0 }
      };

      const body = this.renderDepartmentDigest(department.name, departmentMetrics, metrics.start, metrics.end, metrics.givingTotal);

      await this.email.sendMail({
        to: lead.email,
        subject: `${department.name} KPI Digest (${this.formatDate(metrics.start)} - ${this.formatDate(metrics.end)})`,
        text: body
      });

      sent += 1;
    }

    if (sent === 0) {
      this.logger.warn('No department KPI digests were sent because no leads have email addresses configured.');
    } else {
      this.logger.log(`Sent ${sent} department KPI digest(s).`);
    }

    return sent;
  }

  async sendExecutiveDigest(rangeDays: number): Promise<number> {
    const metrics = await this.collectMetrics(rangeDays);
    const admins = await this.prisma.user.findMany({
      where: { isAdmin: true, email: { not: null } },
      select: { email: true }
    });

    const recipients = admins.map((admin) => admin.email).filter((email): email is string => Boolean(email));

    if (recipients.length === 0) {
      this.logger.warn('Executive KPI digest skipped because no admin recipients are available.');
      return 0;
    }

    const body = this.renderExecutiveDigest(metrics);

    await this.email.sendMail({
      to: recipients,
      subject: `Executive KPI Summary (${this.formatDate(metrics.start)} - ${this.formatDate(metrics.end)})`,
      text: body
    });

    this.logger.log(`Sent executive KPI digest to ${recipients.length} recipient(s).`);
    return recipients.length;
  }

  private async collectMetrics(rangeDays: number): Promise<DigestMetrics> {
    const safeRange = this.normaliseRange(rangeDays);
    const end = new Date();
    const start = new Date(end.getTime() - safeRange * 24 * 60 * 60 * 1000);

    const [attendanceRecords, volunteerRoles, volunteerAssignments, givingAggregate, newMembers] = await Promise.all([
      this.prisma.attendanceRecord.findMany({
        where: { checkInTime: { gte: start, lte: end } },
        include: { role: { include: { department: true } } }
      }),
      this.prisma.volunteerRole.findMany({ include: { department: true } }),
      this.prisma.volunteerAssignment.findMany({
        where: { createdAt: { gte: start, lte: end } },
        include: { role: { include: { department: true } } }
      }),
      this.prisma.donation.aggregate({
        where: { createdAt: { gte: start, lte: end }, status: 'completed' },
        _sum: { amount: true }
      }),
      this.prisma.member.count({ where: { createdAt: { gte: start, lte: end } } })
    ]);

    const departments = new Map<string, DepartmentMetrics>();
    const totalAttendance = { checked: 0, expected: 0 };
    const totalVolunteer = { assigned: 0, needed: 0 };

    for (const record of attendanceRecords) {
      const departmentName = record.role?.department?.name ?? 'General';
      const metrics = departments.get(departmentName) ?? {
        attendance: { checked: 0, expected: 0 },
        volunteers: { assigned: 0, needed: 0 }
      };

      const checked = record.checkedInCount ?? 0;
      const expected = record.expectedAttendees ?? 0;

      metrics.attendance.checked += checked;
      metrics.attendance.expected += expected;

      departments.set(departmentName, metrics);

      totalAttendance.checked += checked;
      totalAttendance.expected += expected;
    }

    for (const role of volunteerRoles) {
      const departmentName = role.department?.name ?? 'General';
      const metrics = departments.get(departmentName) ?? {
        attendance: { checked: 0, expected: 0 },
        volunteers: { assigned: 0, needed: 0 }
      };

      metrics.volunteers.needed += role.neededVolunteers ?? 0;
      departments.set(departmentName, metrics);
      totalVolunteer.needed += role.neededVolunteers ?? 0;
    }

    for (const assignment of volunteerAssignments) {
      const departmentName = assignment.role?.department?.name ?? 'General';
      const metrics = departments.get(departmentName) ?? {
        attendance: { checked: 0, expected: 0 },
        volunteers: { assigned: 0, needed: 0 }
      };

      metrics.volunteers.assigned += 1;
      departments.set(departmentName, metrics);
      totalVolunteer.assigned += 1;
    }

    const givingTotal = this.toNumber(givingAggregate._sum.amount);

    return {
      start,
      end,
      departments,
      givingTotal,
      totalAttendance,
      totalVolunteer,
      newMembers
    };
  }

  private renderDepartmentDigest(
    departmentName: string,
    metrics: DepartmentMetrics,
    start: Date,
    end: Date,
    givingTotal: number
  ): string {
    const attendanceRate = this.calculateRate(metrics.attendance.checked, metrics.attendance.expected);
    const volunteerRate = this.calculateRate(metrics.volunteers.assigned, metrics.volunteers.needed);

    const lines = [
      `KPI summary for ${departmentName}`,
      `Window: ${this.formatDate(start)} - ${this.formatDate(end)}`,
      '',
      `Attendance: ${metrics.attendance.checked} checked-in of ${metrics.attendance.expected} expected (rate ${attendanceRate}%)`,
      `Volunteer coverage: ${metrics.volunteers.assigned} assigned of ${metrics.volunteers.needed} needed (rate ${volunteerRate}%)`,
      `Giving (all ministries): $${givingTotal.toFixed(2)}`,
      '',
      'Next Steps:',
      '- Review volunteer assignments for gaps.',
      '- Celebrate wins with your campus teams.'
    ];

    return lines.join('\n');
  }

  private renderExecutiveDigest(metrics: DigestMetrics): string {
    const attendanceRate = this.calculateRate(
      metrics.totalAttendance.checked,
      metrics.totalAttendance.expected
    );
    const volunteerRate = this.calculateRate(metrics.totalVolunteer.assigned, metrics.totalVolunteer.needed);
    const departmentCount = metrics.departments.size;

    const lines = [
      `Executive KPI Summary (${this.formatDate(metrics.start)} - ${this.formatDate(metrics.end)})`,
      '',
      `Attendance rate: ${attendanceRate}% across ${departmentCount} department(s).`,
      `Volunteer fill rate: ${volunteerRate}% with ${metrics.totalVolunteer.assigned} assignments recorded.`,
      `Giving total: $${metrics.givingTotal.toFixed(2)} from completed donations.`,
      `New members added: ${metrics.newMembers}.`,
      '',
      'Top Opportunities:',
      '- Review departments below 70% volunteer coverage.',
      '- Highlight departments exceeding attendance expectations.'
    ];

    return lines.join('\n');
  }

  private normaliseRange(rangeDays: number): number {
    if (!Number.isFinite(rangeDays) || rangeDays <= 0) {
      return 30;
    }
    return Math.max(1, Math.floor(rangeDays));
  }

  private calculateRate(value: number, total: number): number {
    if (!total || total <= 0) {
      return 0;
    }

    return Math.round((value / total) * 10000) / 100;
  }

  private formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  private toNumber(value: Prisma.Decimal | number | null | undefined): number {
    if (!value) {
      return 0;
    }
    if (typeof value === 'number') {
      return value;
    }
    return value.toNumber();
  }
}
