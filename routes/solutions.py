from flask import Blueprint, render_template

solutions_bp = Blueprint('solutions', __name__, url_prefix='/solutions')

SAAS_FEATURES = [
    {
        "icon": "bi-people",
        "title": "Centralized Member Care",
        "description": (
            "Keep prayer requests, pastoral notes, and follow-up activity organized so"
            " every leader can respond with confidence."
        ),
    },
    {
        "icon": "bi-calendar2-check",
        "title": "Coordinated Ministry Planning",
        "description": (
            "Map events, teams, and volunteer assignments in one dashboard with real-time"
            " availability and automated reminders."
        ),
    },
    {
        "icon": "bi-graph-up",
        "title": "Actionable Engagement Analytics",
        "description": (
            "Measure attendance trends, digital touchpoints, and giving momentum to make"
            " data-backed ministry decisions."
        ),
    },
]

SAAS_AUTOMATIONS = [
    {
        "title": "Prayer Pipeline",
        "summary": (
            "Automatically route new requests to the right ministry leader, notify intercessors,"
            " and track outcomes until every need is closed."
        ),
    },
    {
        "title": "Event Journeys",
        "summary": (
            "Trigger confirmation emails, volunteer reminders, and post-event surveys without"
            " manual work from staff."
        ),
    },
    {
        "title": "Generosity Nudges",
        "summary": (
            "Segment donors, schedule seasonal campaigns, and sync successful payments back"
            " to your finance tools automatically."
        ),
    },
]

SAAS_INTEGRATIONS = [
    "Two-way sync with the Covenant Connect WordPress plugin",
    "Import tools for Planning Center, Google Calendar, and Mailchimp",
    "REST API and Zapier connector for custom ministry workflows",
]

SAAS_PLANS = [
    {
        "name": "Community",
        "price": "$49",
        "billing": "per month",
        "tagline": "Launch your digital ministry hub",
        "features": [
            "Unlimited prayer requests",
            "Event calendar with RSVP management",
            "Team email notifications",
        ],
    },
    {
        "name": "Growth",
        "price": "$99",
        "billing": "per month",
        "tagline": "Automations for expanding teams",
        "features": [
            "Volunteer scheduling & reminders",
            "Automated donor follow-up sequences",
            "Advanced analytics dashboard",
        ],
    },
    {
        "name": "Impact",
        "price": "Custom",
        "billing": "",
        "tagline": "Tailored for multi-campus churches",
        "features": [
            "Dedicated success strategist",
            "Custom data migrations",
            "Priority phone & chat support",
        ],
    },
]

SAAS_FAQS = [
    {
        "question": "Can we connect existing WordPress sites?",
        "answer": (
            "Yes. Install the Covenant Connect plugin to sync sermons, events, and forms"
            " directly from the SaaS dashboard without duplicating content."
        ),
    },
    {
        "question": "Is onboarding included?",
        "answer": (
            "Every subscription comes with guided setup, import checklists, and two live"
            " training sessions for your staff."
        ),
    },
    {
        "question": "How secure is our data?",
        "answer": (
            "We use encrypted storage, role-based permissions, and regional payment providers"
            " that are fully PCI compliant."
        ),
    },
]

PLUGIN_FEATURES = [
    {
        "icon": "bi-cloud-arrow-down",
        "title": "Real-Time Content Sync",
        "description": (
            "Display sermons, devotionals, and events from Covenant Connect inside WordPress"
            " without managing multiple dashboards."
        ),
    },
    {
        "icon": "bi-palette",
        "title": "Theme-Aware Blocks",
        "description": (
            "Drop responsive Gutenberg blocks that inherit your WordPress theme styles for"
            " sermons, events, and donation prompts."
        ),
    },
    {
        "icon": "bi-shield-check",
        "title": "Secure Token Authentication",
        "description": (
            "Issue time-limited access tokens from the SaaS portal so editors can connect"
            " safely without sharing database credentials."
        ),
    },
]

PLUGIN_STEPS = [
    {
        "title": "Install",
        "details": "Upload the plugin ZIP in WordPress or install directly from the marketplace.",
    },
    {
        "title": "Connect",
        "details": "Paste your SaaS API key and choose which site collections to sync.",
    },
    {
        "title": "Publish",
        "details": "Place sermon, event, or donation blocks on any page and let automated sync handle the rest.",
    },
]

PLUGIN_CAPABILITIES = [
    "Embed sermon video and audio players with automatic fallbacks",
    "Show curated event lists, calendars, and add-to-calendar buttons",
    "Create donation callouts that route supporters to secure Paystack or Fincra checkouts",
    "Capture prayer requests that post back to the SaaS pipeline in seconds",
]

PLUGIN_SUPPORT = [
    {
        "title": "Documentation",
        "description": "Step-by-step guides covering shortcodes, Gutenberg blocks, and theme overrides.",
    },
    {
        "title": "Office Hours",
        "description": "Live weekly Q&A sessions with our product specialists to troubleshoot complex builds.",
    },
    {
        "title": "Priority Support",
        "description": "Impact plan customers receive 2-hour response SLAs across chat and email.",
    },
]

PLUGIN_FAQS = [
    {
        "question": "Does the plugin work with multisite?",
        "answer": "Yes, each site can authenticate with its own API token and choose unique content feeds.",
    },
    {
        "question": "Can developers extend the plugin?",
        "answer": "Hooks and filters are available for custom taxonomies, templates, and caching strategies.",
    },
    {
        "question": "How often does sync occur?",
        "answer": "By default content updates every 5 minutes, and you can trigger an instant sync from the WordPress dashboard.",
    },
]


@solutions_bp.route('/saas')
def saas_overview():
    return render_template(
        'saas.html',
        features=SAAS_FEATURES,
        automations=SAAS_AUTOMATIONS,
        integrations=SAAS_INTEGRATIONS,
        plans=SAAS_PLANS,
        faqs=SAAS_FAQS,
    )


@solutions_bp.route('/wordpress-plugin')
def wordpress_plugin():
    return render_template(
        'wordpress_plugin.html',
        features=PLUGIN_FEATURES,
        steps=PLUGIN_STEPS,
        capabilities=PLUGIN_CAPABILITIES,
        support=PLUGIN_SUPPORT,
        faqs=PLUGIN_FAQS,
    )
