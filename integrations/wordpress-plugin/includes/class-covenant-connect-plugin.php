<?php

namespace CovenantConnect;

use WP_Error;

if (! defined('ABSPATH')) {
    exit;
}

/**
 * WordPress integration glue for Covenant Connect.
 */
class Plugin
{
    /**
     * @var Plugin|null
     */
    private static $instance = null;

    /**
     * Retrieve the shared plugin instance.
     */
    public static function instance()
    {
        if (null === self::$instance) {
            self::$instance = new self();
        }

        return self::$instance;
    }

    private function __construct()
    {
        add_action('init', array($this, 'registerShortcodes'));
        add_action('admin_menu', array($this, 'registerSettingsPage'));
        add_action('admin_init', array($this, 'registerSettings'));
        add_action('wp_enqueue_scripts', array($this, 'registerAssets'));
    }

    /**
     * Register the front-end stylesheet.
     */
    public function registerAssets()
    {
        wp_register_style(
            'covenant-connect',
            COVENANT_CONNECT_PLUGIN_URL . 'assets/style.css',
            array(),
            COVENANT_CONNECT_PLUGIN_VERSION
        );
    }

    /**
     * Register shortcodes that surface Covenant Connect content.
     */
    public function registerShortcodes()
    {
        add_shortcode('covenant_connect_sermons', array($this, 'renderSermonsShortcode'));
        add_shortcode('covenant_connect_events', array($this, 'renderEventsShortcode'));
    }

    /**
     * Register plugin settings and option fields.
     */
    public function registerSettings()
    {
        register_setting(
            'covenant_connect_settings',
            'covenant_connect_api_base_url',
            array(
                'type'              => 'string',
                'sanitize_callback' => array($this, 'sanitizeApiBaseUrl'),
                'default'           => '',
            )
        );

        register_setting(
            'covenant_connect_settings',
            'covenant_connect_api_key',
            array(
                'type'              => 'string',
                'sanitize_callback' => array($this, 'sanitizeApiKey'),
                'default'           => '',
            )
        );

        add_settings_section(
            'covenant_connect_api',
            __('API Connection', 'covenant-connect'),
            array($this, 'renderSettingsIntro'),
            'covenant_connect_settings'
        );

        add_settings_field(
            'covenant_connect_api_base_url',
            __('API base URL', 'covenant-connect'),
            array($this, 'renderApiBaseUrlField'),
            'covenant_connect_settings',
            'covenant_connect_api'
        );

        add_settings_field(
            'covenant_connect_api_key',
            __('API token (optional)', 'covenant-connect'),
            array($this, 'renderApiKeyField'),
            'covenant_connect_settings',
            'covenant_connect_api'
        );
    }

    /**
     * Render the settings page in wp-admin.
     */
    public function registerSettingsPage()
    {
        add_options_page(
            __('Covenant Connect', 'covenant-connect'),
            __('Covenant Connect', 'covenant-connect'),
            'manage_options',
            'covenant-connect',
            array($this, 'renderSettingsPage')
        );
    }

    /**
     * Display introductory text above the settings form.
     */
    public function renderSettingsIntro()
    {
        echo '<p>' . esc_html__('Provide your Covenant Connect API endpoint so this site can pull the latest sermons and events.', 'covenant-connect') . '</p>';
    }

    /**
     * Render the API base URL field.
     */
    public function renderApiBaseUrlField()
    {
        $value = esc_attr(get_option('covenant_connect_api_base_url', ''));
        echo '<input type="url" class="regular-text" name="covenant_connect_api_base_url" value="' . $value . '" placeholder="https://api.covenantconnect.example" />';
    }

    /**
     * Render the API key field.
     */
    public function renderApiKeyField()
    {
        $value = esc_attr(get_option('covenant_connect_api_key', ''));
        echo '<input type="text" class="regular-text" name="covenant_connect_api_key" value="' . $value . '" placeholder="Optional token for private deployments" />';
    }

    /**
     * Draw the settings page markup.
     */
    public function renderSettingsPage()
    {
        if (! current_user_can('manage_options')) {
            return;
        }

        echo '<div class="wrap">';
        echo '<h1>' . esc_html__('Covenant Connect', 'covenant-connect') . '</h1>';
        echo '<form method="post" action="options.php">';
        settings_fields('covenant_connect_settings');
        do_settings_sections('covenant_connect_settings');
        submit_button(__('Save changes', 'covenant-connect'));
        echo '</form>';
        echo '</div>';
    }

    /**
     * Render the sermons shortcode output.
     *
     * @param array<string, mixed> $atts
     */
    public function renderSermonsShortcode($atts)
    {
        $attributes = shortcode_atts(
            array(
                'limit'         => 5,
                'show_preacher' => 'true',
                'show_date'     => 'true',
                'layout'        => 'list',
                'cache_minutes' => 5,
            ),
            $atts,
            'covenant_connect_sermons'
        );

        return $this->renderContent(
            'sermons',
            (int) $attributes['limit'],
            (int) $attributes['cache_minutes'],
            $attributes
        );
    }

    /**
     * Render the events shortcode output.
     *
     * @param array<string, mixed> $atts
     */
    public function renderEventsShortcode($atts)
    {
        $attributes = shortcode_atts(
            array(
                'limit'         => 5,
                'show_location' => 'true',
                'show_time'     => 'true',
                'layout'        => 'list',
                'cache_minutes' => 5,
            ),
            $atts,
            'covenant_connect_events'
        );

        return $this->renderContent(
            'events',
            (int) $attributes['limit'],
            (int) $attributes['cache_minutes'],
            $attributes
        );
    }

    /**
     * Shared rendering helper for sermons and events.
     *
     * @param 'sermons'|'events' $type
     * @param int $limit
     * @param int $cacheMinutes
     * @param array<string, mixed> $attributes
     * @return string
     */
    private function renderContent($type, $limit, $cacheMinutes, array $attributes)
    {
        $cacheMinutes = max(1, min((int) $cacheMinutes, 60));
        $limit        = max(1, min((int) $limit, 25));
        $cacheKey     = 'covenant_connect_' . $type . '_' . md5(wp_json_encode(array($limit, $attributes)));

        $cached = get_transient($cacheKey);
        if (false !== $cached) {
            return (string) $cached;
        }

        $client = $this->makeClient();

        if (! $client->isConfigured()) {
            return $this->renderNotice(__('Configure the Covenant Connect API base URL in Settings → Covenant Connect before using this shortcode.', 'covenant-connect'));
        }

        if ('sermons' === $type) {
            $response = $client->getSermons($limit);
        } else {
            $response = $client->getEvents($limit);
        }

        if ($response instanceof WP_Error) {
            return $this->renderNotice($response->get_error_message());
        }

        if (! is_array($response) || empty($response)) {
            return $this->renderNotice(__('No content is available yet. Once new records are published they will appear here automatically.', 'covenant-connect'));
        }

        wp_enqueue_style('covenant-connect');

        if ('sermons' === $type) {
            $html = $this->buildSermonsMarkup($response, $attributes);
        } else {
            $html = $this->buildEventsMarkup($response, $attributes);
        }

        set_transient($cacheKey, $html, $cacheMinutes * MINUTE_IN_SECONDS);

        return $html;
    }

    /**
     * Create a new API client with the configured credentials.
     */
    private function makeClient()
    {
        $baseUrl = (string) get_option('covenant_connect_api_base_url', '');
        $apiKey  = (string) get_option('covenant_connect_api_key', '');

        return new ApiClient($baseUrl, $apiKey);
    }

    /**
     * Convert a truthy shortcode attribute to a boolean.
     */
    private function toBool($value)
    {
        if (is_bool($value)) {
            return $value;
        }

        $normalized = strtolower((string) $value);

        return in_array($normalized, array('1', 'true', 'yes', 'on'), true);
    }

    /**
     * Produce HTML for the sermons listing.
     *
     * @param array<int, array<string, mixed>> $sermons
     * @param array<string, mixed> $attributes
     * @return string
     */
    private function buildSermonsMarkup(array $sermons, array $attributes)
    {
        $showPreacher = $this->toBool($attributes['show_preacher']);
        $showDate     = $this->toBool($attributes['show_date']);
        $layout       = $this->sanitizeLayout($attributes['layout']);

        $items = array();

        foreach ($sermons as $sermon) {
            if (! is_array($sermon)) {
                continue;
            }

            $title       = isset($sermon['title']) ? esc_html((string) $sermon['title']) : __('Untitled sermon', 'covenant-connect');
            $description = isset($sermon['description']) ? wp_kses_post($sermon['description']) : '';
            $preacher    = isset($sermon['preacher']) ? esc_html((string) $sermon['preacher']) : '';
            $mediaUrl    = isset($sermon['mediaUrl']) ? esc_url((string) $sermon['mediaUrl']) : '';
            $mediaType   = isset($sermon['mediaType']) ? esc_html((string) $sermon['mediaType']) : '';
            $dateLabel   = isset($sermon['date']) ? $this->formatDate($sermon['date']) : '';

            $metaParts = array();
            if ($showDate && $dateLabel !== '') {
                $metaParts[] = esc_html($dateLabel);
            }
            if ($showPreacher && $preacher !== '') {
                $metaParts[] = esc_html($preacher);
            }

            $meta = '';
            if (! empty($metaParts)) {
                $meta = '<p class="covenant-connect__meta">' . esc_html(implode(' • ', $metaParts)) . '</p>';
            }

            $mediaButton = '';
            if ($mediaUrl !== '') {
                $buttonLabel = $mediaType !== '' ? sprintf(__('Open %s', 'covenant-connect'), $mediaType) : __('Watch / Listen', 'covenant-connect');
                $mediaButton = '<p><a class="covenant-connect__button" href="' . $mediaUrl . '" target="_blank" rel="noopener noreferrer">' . esc_html($buttonLabel) . '</a></p>';
            }

            $items[] = '<li class="covenant-connect__item">'
                . '<h3 class="covenant-connect__title">' . $title . '</h3>'
                . $meta
                . ($description !== '' ? '<p class="covenant-connect__description">' . $description . '</p>' : '')
                . $mediaButton
                . '</li>';
        }

        if (empty($items)) {
            return $this->renderNotice(__('No sermons are available yet.', 'covenant-connect'));
        }

        $classes = 'covenant-connect covenant-connect--' . esc_attr($layout);
        $list    = '<ul class="covenant-connect__list">' . implode('', $items) . '</ul>';

        return '<div class="' . $classes . '">' . $list . '</div>';
    }

    /**
     * Produce HTML for the events listing.
     *
     * @param array<int, array<string, mixed>> $events
     * @param array<string, mixed> $attributes
     * @return string
     */
    private function buildEventsMarkup(array $events, array $attributes)
    {
        $showLocation = $this->toBool($attributes['show_location']);
        $showTime     = $this->toBool($attributes['show_time']);
        $layout       = $this->sanitizeLayout($attributes['layout']);

        $items = array();

        foreach ($events as $event) {
            if (! is_array($event)) {
                continue;
            }

            $title       = isset($event['title']) ? esc_html((string) $event['title']) : __('Untitled event', 'covenant-connect');
            $description = isset($event['description']) ? wp_kses_post($event['description']) : '';
            $location    = isset($event['location']) ? esc_html((string) $event['location']) : '';
            $startsAt    = isset($event['startsAt']) ? $this->formatDateTime($event['startsAt'], $showTime) : '';
            $endsAt      = isset($event['endsAt']) ? $this->formatDateTime($event['endsAt'], $showTime) : '';

            $metaParts = array();
            if ($startsAt !== '') {
                $metaParts[] = esc_html__('Starts', 'covenant-connect') . ': ' . esc_html($startsAt);
            }
            if ($endsAt !== '') {
                $metaParts[] = esc_html__('Ends', 'covenant-connect') . ': ' . esc_html($endsAt);
            }
            if ($showLocation && $location !== '') {
                $metaParts[] = esc_html__('Location', 'covenant-connect') . ': ' . esc_html($location);
            }

            $meta = '';
            if (! empty($metaParts)) {
                $meta = '<p class="covenant-connect__meta">' . implode('<br />', array_map('esc_html', $metaParts)) . '</p>';
            }

            $items[] = '<li class="covenant-connect__item">'
                . '<h3 class="covenant-connect__title">' . $title . '</h3>'
                . $meta
                . ($description !== '' ? '<p class="covenant-connect__description">' . $description . '</p>' : '')
                . '</li>';
        }

        if (empty($items)) {
            return $this->renderNotice(__('There are no upcoming events right now. Check back soon!', 'covenant-connect'));
        }

        $classes = 'covenant-connect covenant-connect--' . esc_attr($layout);
        $list    = '<ul class="covenant-connect__list">' . implode('', $items) . '</ul>';

        return '<div class="' . $classes . '">' . $list . '</div>';
    }

    /**
     * Convert layout hints to a known CSS modifier.
     */
    private function sanitizeLayout($layout)
    {
        $value = strtolower((string) $layout);

        if (! in_array($value, array('list', 'cards'), true)) {
            return 'list';
        }

        return $value;
    }

    /**
     * Format a date string using the site locale.
     */
    private function formatDate($value)
    {
        $timestamp = strtotime((string) $value);

        if (false === $timestamp) {
            return '';
        }

        $format = get_option('date_format');

        return date_i18n($format, $timestamp);
    }

    /**
     * Format a datetime string using the site locale.
     */
    private function formatDateTime($value, $includeTime)
    {
        $timestamp = strtotime((string) $value);

        if (false === $timestamp) {
            return '';
        }

        $dateFormat = get_option('date_format');
        $timeFormat = get_option('time_format');

        if ($this->toBool($includeTime)) {
            return date_i18n($dateFormat . ' ' . $timeFormat, $timestamp);
        }

        return date_i18n($dateFormat, $timestamp);
    }

    /**
     * Render a user-facing notice.
     */
    private function renderNotice($message)
    {
        return '<div class="covenant-connect covenant-connect__notice">' . esc_html($message) . '</div>';
    }

    /**
     * Sanitize the stored base URL.
     */
    public function sanitizeApiBaseUrl($value)
    {
        $sanitized = esc_url_raw((string) $value);

        return $sanitized ?: '';
    }

    /**
     * Sanitize the stored API key.
     */
    public function sanitizeApiKey($value)
    {
        return sanitize_text_field((string) $value);
    }
}
