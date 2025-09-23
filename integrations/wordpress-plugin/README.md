# Covenant Connect WordPress Bridge

This directory contains an installable WordPress plugin that embeds sermons and
upcoming events from your Covenant Connect instance.  The plugin ships with
shortcodes that render responsive lists, along with an admin settings page to
configure the API endpoint and optional bearer token.

## Installation

1. Run the NestJS backend (`apps/backend`) somewhere publicly accessible or
   expose it through a tunnelling service during development.
2. Copy the `integrations/wordpress-plugin` directory into a folder named
   `covenant-connect` inside `wp-content/plugins` on your WordPress site.
3. Activate **Covenant Connect Bridge** in the WordPress plugins dashboard.
4. Navigate to **Settings → Covenant Connect** and provide the API base URL (for
   example `https://api.example.com`) and, if required, a bearer token that the
   NestJS deployment expects via the `Authorization` header.

Once configured, place the following shortcodes in any page, post, or block:

- `[covenant_connect_sermons limit="5" layout="cards" show_preacher="true" show_date="true"]`
- `[covenant_connect_events limit="3" layout="list" show_location="true" show_time="false"]`

Both shortcodes accept an optional `cache_minutes` attribute (defaults to `5`)
so busy sites can cache responses locally without overloading the API.

## Development notes

- Styles live in `assets/style.css`; they intentionally use minimal selectors so
  they inherit well from any WordPress theme.
- The plugin caches rendered HTML using WordPress transients. Flush the cache by
  deleting the relevant transient or updating the shortcode attributes.
- Additional blocks and editor integrations can build on the existing API client
  in `includes/class-covenant-connect-api-client.php`.

Pack the plugin into a zip by running:

```bash
zip -r covenant-connect-wordpress.zip covenant-connect
```

from inside the `integrations/wordpress-plugin` directory, then upload the zip
through WordPress.
