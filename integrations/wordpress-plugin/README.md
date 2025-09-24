# Covenant Connect WordPress Bridge

This directory contains an installable WordPress plugin that embeds sermons and
upcoming events from your Covenant Connect instance. The plugin ships with
shortcodes, Gutenberg blocks, and an admin settings page to configure the API
endpoint and optional bearer token.

## Installation

1. Run the NestJS backend (`apps/backend`) somewhere publicly accessible or
   expose it through a tunnelling service during development.
2. Download the latest `covenant-connect-wordpress-*.zip` artifact from the
   GitHub Releases page (or build it locally with `pnpm package:wordpress`).
3. Upload and install the zip via **Plugins → Add New → Upload Plugin** in the
   WordPress dashboard, or extract it into `wp-content/plugins/covenant-connect`.
4. Activate **Covenant Connect Bridge** in the WordPress plugins dashboard.
5. Navigate to **Settings → Covenant Connect** and provide the API base URL (for
   example `https://api.example.com`) and, if required, a bearer token that the
   NestJS deployment expects via the `Authorization` header.

Once configured, place the following shortcodes in any page, post, or block:

- `[covenant_connect_sermons limit="5" layout="cards" show_preacher="true" show_date="true"]`
- `[covenant_connect_events limit="3" layout="list" show_location="true" show_time="false"]`

Both shortcodes accept an optional `cache_minutes` attribute (defaults to `5`)
so busy sites can cache responses locally without overloading the API.

## Gutenberg blocks

Editors who prefer a visual workflow can insert **Covenant Connect Sermons**
and **Covenant Connect Events** blocks from the block inserter. Each block
supports the same display options as the shortcodes (layout, limit, preacher/
location toggles, and caching duration) and renders a live preview inside the
editor using server-side rendering.

## Development notes

- Styles live in `assets/style.css`; they intentionally use minimal selectors so
  they inherit well from any WordPress theme.
- The plugin caches rendered HTML using WordPress transients. Flush the cache by
  deleting the relevant transient or updating the shortcode attributes.
- Additional blocks and editor integrations can build on the existing API client
  in `includes/class-covenant-connect-api-client.php`.

## Packaging & releases

- Run `pnpm package:wordpress` from the repository root to build the block
  assets and generate a distributable zip in
  `integrations/wordpress-plugin/dist/`.
- Tags that match `wordpress-v*` trigger the `wordpress-release.yml` GitHub
  workflow, which builds the plugin and attaches the zip to the corresponding
  release automatically.
