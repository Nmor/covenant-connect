# Admin experience inventory

## Blueprint overview

- `routes/admin.py` registers the `admin_bp` blueprint and protects all handlers with `login_required` and a custom `admin_required` guard, exposing dashboard, user management, member care, and prayer moderation views.【F:routes/admin.py†L26-L199】
- `routes/admin_reports.py` adds the `/admin/reports` blueprint that powers aggregated metrics, CSV exports, and reporting helpers consumed by the dashboard.【F:routes/admin_reports.py†L16-L360】

## Executive dashboard

- Routes: `GET /admin` and `GET /admin/dashboard` render the executive dashboard with a rolling time window based on `range` query params (`30d`, `60d`, `90d`, `6m`, `1y`). The controller queries attendance, volunteer fulfilment, giving, assimilation, and recent care follow-ups via `ReportingService` utilities.【F:routes/admin.py†L54-L85】
- Templates:
  - `templates/admin/dashboard/index.html` composes the page shell, export shortcuts, and injects partials for the analytic cards plus the recent care follow-up list.【F:templates/admin/dashboard/index.html†L4-L69】
  - `dashboard/filters.html` supplies the timeframe `<form>` so leaders can pivot the range inline.【F:templates/admin/dashboard/filters.html†L1-L18】
  - `dashboard/attendance_panel.html`, `dashboard/volunteer_panel.html`, `dashboard/giving_panel.html`, and `dashboard/assimilation_panel.html` break out each analytic widget, rendering totals, subtables, and sparkline-style summaries from the JSON payload returned by `ReportingService`.【F:templates/admin/dashboard/attendance_panel.html†L1-L46】【F:templates/admin/dashboard/volunteer_panel.html†L1-L43】【F:templates/admin/dashboard/giving_panel.html†L1-L40】【F:templates/admin/dashboard/assimilation_panel.html†L1-L46】
  - The dashboard also surfaces the five most recent care interactions pulled by `_recent_care_followups`, highlighting member names, interaction types, dates, and notes.【F:routes/admin.py†L66-L85】【F:templates/admin/dashboard/index.html†L36-L65】
- Reporting API: `/admin/reports/metrics` hydrates the dashboard, while `/admin/reports/*.csv` endpoints provide downloadable exports for attendance, volunteers, giving, and assimilation funnels.【F:routes/admin_reports.py†L262-L358】

## User management

- Routes: `GET /admin/users` lists accounts, `GET/POST /admin/users/create` handles creation, `GET/POST /admin/users/<id>/edit` updates profiles and triggers automations when admin status flips, `/admin/users/<id>/delete` deletes accounts with a self-delete guard, and `/admin/users/import` is currently a stub that flashes a notice.【F:routes/admin.py†L88-L171】
- Templates:
  - `templates/admin/users.html` renders the data table, action buttons, flash messaging, and the CSV import modal scaffold.【F:templates/admin/users.html†L4-L117】
  - `templates/admin/user_form.html` provides the create/edit form with validation hints, admin toggle, and contextual help copy.【F:templates/admin/user_form.html†L4-L119】
  - `templates/admin/user_import.html` (legacy partial referenced by the modal) mirrors the bulk import expectations if the feature is revived.【F:templates/admin/user_import.html†L1-L39】

## Member care & follow-up

- Routes: `GET /admin/members` lists members (currently without search filtering in the controller) and `GET /admin/members/<id>` renders the profile with interaction history; `_recent_care_followups` supports dashboard rollups.【F:routes/admin.py†L79-L199】
- Templates:
  - `templates/admin/members/index.html` surfaces filters for search/status, assimilation progress bars, follow-up due badges, and deep links into member profiles.【F:templates/admin/members/index.html†L4-L96】
  - `templates/admin/members/detail.html` shows profile stats, milestone checklist, household info, a rich follow-up logging form (interaction type, dates, milestone updates), and the interaction feed. The form references routes such as `admin.log_member_follow_up` that are not yet implemented server-side.【F:templates/admin/members/detail.html†L4-L180】

## Prayer requests moderation

- Route: `GET /admin/prayers` lists inbound requests with modal detail views and action buttons intended to toggle visibility or delete entries; the related POST routes are not present in the blueprint yet.【F:routes/admin.py†L173-L178】【F:templates/admin/prayers.html†L4-L84】

## Additional admin templates awaiting endpoints

- The `templates/admin/` tree also contains layouts for events, volunteer assignments, automations, donations, gallery, facilities, sermons, and settings management. These articulate desired CRUD flows—event creation/editing, volunteer assignment forms, facility reservation conflict warnings, content uploads, etc.—but corresponding Flask routes have not been wired up in `routes/admin.py`, indicating future work for the Prisma-backed services.【F:templates/admin/events.html†L4-L86】【F:templates/admin/event_form.html†L4-L118】【F:templates/admin/volunteers/index.html†L4-L68】【F:templates/admin/volunteers/form.html†L4-L79】【F:templates/admin/donations.html†L4-L68】【F:templates/admin/gallery.html†L4-L63】【F:templates/admin/facilities.html†L4-L200】【F:templates/admin/settings.html†L4-L196】

## Observations & gaps

- Several templates post to routes such as `admin.log_member_follow_up`, `admin.toggle_prayer_visibility`, `admin.delete_prayer`, and other CRUD handlers that are absent in `routes/admin.py`, reinforcing that the Next.js/Prisma migration must supply API endpoints for those interactions before the UI can be fully functional.【F:templates/admin/members/detail.html†L108-L166】【F:templates/admin/prayers.html†L38-L66】
- The reporting service already structures data in a JSON-friendly shape, making it straightforward to mirror in the forthcoming Next.js admin dashboard and to expose via Prisma-powered REST endpoints.【F:routes/admin_reports.py†L31-L241】
