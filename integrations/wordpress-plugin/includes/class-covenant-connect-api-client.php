<?php

namespace CovenantConnect;

use WP_Error;

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Small HTTP client for calling the Covenant Connect REST API.
 */
class ApiClient
{
    /**
     * @var string
     */
    private $baseUrl;

    /**
     * @var string
     */
    private $apiKey;

    /**
     * @param string $baseUrl
     * @param string $apiKey
     */
    public function __construct($baseUrl, $apiKey = '')
    {
        $this->baseUrl = rtrim((string) $baseUrl, "/ ");
        $this->apiKey  = (string) $apiKey;
    }

    /**
     * Determine whether the client is configured with a base URL.
     */
    public function isConfigured()
    {
        return $this->baseUrl !== '';
    }

    /**
     * Fetch recent sermons from the API.
     *
     * @param int $limit
     * @return array|WP_Error
     */
    public function getSermons($limit = 5)
    {
        $params = array(
            'page'     => 1,
            'pageSize' => $this->normalizeLimit($limit),
        );

        $response = $this->request('content/sermons', $params);

        if (is_wp_error($response)) {
            return $response;
        }

        if (! isset($response['data']) || ! is_array($response['data'])) {
            return new WP_Error('covenant_connect_invalid_response', __('The sermons response was not in the expected format.', 'covenant-connect'));
        }

        return $response['data'];
    }

    /**
     * Fetch upcoming events from the API.
     *
     * @param int $limit
     * @return array|WP_Error
     */
    public function getEvents($limit = 5)
    {
        $params = array(
            'page'     => 1,
            'pageSize' => $this->normalizeLimit($limit),
        );

        $response = $this->request('events', $params);

        if (is_wp_error($response)) {
            return $response;
        }

        if (! isset($response['data']) || ! is_array($response['data'])) {
            return new WP_Error('covenant_connect_invalid_response', __('The events response was not in the expected format.', 'covenant-connect'));
        }

        return $response['data'];
    }

    /**
     * Execute a GET request against the API.
     *
     * @param string $path
     * @param array<string, scalar> $query
     * @return array|WP_Error
     */
    private function request($path, array $query = array())
    {
        if (! $this->isConfigured()) {
            return new WP_Error('covenant_connect_not_configured', __('Set the Covenant Connect API base URL before embedding content.', 'covenant-connect'));
        }

        $url = trailingslashit($this->baseUrl) . ltrim($path, '/');

        if (! empty($query)) {
            $url = add_query_arg($query, $url);
        }

        $response = wp_remote_get(
            $url,
            array(
                'timeout' => 10,
                'headers' => $this->buildHeaders(),
            )
        );

        if (is_wp_error($response)) {
            return new WP_Error('covenant_connect_network_error', $response->get_error_message(), $response->get_error_data());
        }

        $status = wp_remote_retrieve_response_code($response);
        $body   = wp_remote_retrieve_body($response);

        if ($status < 200 || $status >= 300) {
            return new WP_Error('covenant_connect_http_error', sprintf(__('The Covenant Connect API responded with HTTP %d.', 'covenant-connect'), $status), array('body' => $body));
        }

        $decoded = json_decode($body, true);

        if (JSON_ERROR_NONE !== json_last_error()) {
            return new WP_Error('covenant_connect_json_error', __('Unable to decode the API response.', 'covenant-connect'), array('body' => $body));
        }

        return is_array($decoded) ? $decoded : array();
    }

    /**
     * Build HTTP headers for API requests.
     *
     * @return array<string, string>
     */
    private function buildHeaders()
    {
        $headers = array(
            'Accept' => 'application/json',
        );

        if ($this->apiKey !== '') {
            $headers['Authorization'] = 'Bearer ' . $this->apiKey;
        }

        return $headers;
    }

    /**
     * Normalize a limit value so we do not accidentally request too much data.
     *
     * @param int $limit
     * @return int
     */
    private function normalizeLimit($limit)
    {
        $value = (int) $limit;

        if ($value <= 0) {
            $value = 5;
        }

        return (int) min($value, 25);
    }
}
