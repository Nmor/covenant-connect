<?php
/**
 * Plugin Name: Covenant Connect Bridge
 * Description: Embed sermons and events from the Covenant Connect API directly in WordPress pages.
 * Version: 0.1.0
 * Author: Covenant Connect
 * License: GPLv2 or later
 * Requires PHP: 7.4
 */

if (! defined('ABSPATH')) {
    exit;
}

if (! defined('COVENANT_CONNECT_PLUGIN_VERSION')) {
    define('COVENANT_CONNECT_PLUGIN_VERSION', '0.1.0');
}

if (! defined('COVENANT_CONNECT_PLUGIN_DIR')) {
    define('COVENANT_CONNECT_PLUGIN_DIR', plugin_dir_path(__FILE__));
}

if (! defined('COVENANT_CONNECT_PLUGIN_URL')) {
    define('COVENANT_CONNECT_PLUGIN_URL', plugin_dir_url(__FILE__));
}

require_once COVENANT_CONNECT_PLUGIN_DIR . 'includes/class-covenant-connect-api-client.php';
require_once COVENANT_CONNECT_PLUGIN_DIR . 'includes/class-covenant-connect-plugin.php';

add_action(
    'plugins_loaded',
    static function (): void {
        \CovenantConnect\Plugin::instance();
    }
);
