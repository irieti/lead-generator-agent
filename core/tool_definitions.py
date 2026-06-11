"""
Tool schemas passed to the Anthropic API.
Claude reads these descriptions and decides autonomously when to call each tool.
"""

TOOL_DEFINITIONS = [
    {
        "name": "search_linkedin",
        "description": (
            "Search LinkedIn for people matching a role, location, or industry. "
            "Use this to find potential leads. Returns a list of profiles with name, "
            "headline, company, and profile URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query e.g. 'marketing agency founder Lisbon' or 'Head of Growth SaaS Berlin'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results to return. Default 10, max 25.",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_linkedin_profile",
        "description": (
            "Get full details of a LinkedIn profile by URL. Returns name, headline, "
            "current company, location, about section, recent activity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "profile_url": {
                    "type": "string",
                    "description": "Full LinkedIn profile URL e.g. https://linkedin.com/in/username",
                },
            },
            "required": ["profile_url"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for information about a person, company, or topic. "
            "Use to enrich lead context, research companies, or gather report data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query. Be specific for better results.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_gmail",
        "description": (
            "Read emails from Gmail. Can fetch recent unread emails or search by query. "
            "Use to check for inbound leads, replies, or follow-up threads."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query e.g. 'is:unread' or 'subject:automation inquiry' or 'from:founder'",
                    "default": "is:unread",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of emails to return. Default 10.",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "send_gmail",
        "description": (
            "Send an email via Gmail. IMPORTANT: always call telegram_ask for approval "
            "before calling this tool. Never send without explicit approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "Email body in plain text",
                },
                "reply_to_thread_id": {
                    "type": "string",
                    "description": "Gmail thread ID if this is a reply. Optional.",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "send_linkedin_invite",
        "description": (
            "Send a LinkedIn connection request with a personalized message. "
            "IMPORTANT: always call telegram_ask for approval before calling this. "
            "Rate limited to 10 invites per day automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "profile_url": {
                    "type": "string",
                    "description": "Full LinkedIn profile URL of the person to invite",
                },
                "message": {
                    "type": "string",
                    "description": "Personalized connection message. Max 300 characters.",
                },
            },
            "required": ["profile_url", "message"],
        },
    },
    {
        "name": "read_sheet",
        "description": (
            "Read data from Google Sheets. Use to check if a lead already exists, "
            "review past outreach, or load context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "worksheet": {
                    "type": "string",
                    "description": "Worksheet name. Default 'Leads'.",
                    "default": "Leads",
                },
                "search_value": {
                    "type": "string",
                    "description": "Optional value to search for in the sheet (e.g. a name or company)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "write_sheet",
        "description": (
            "Log a lead or update a row in Google Sheets. Always log every person "
            "you research, even if you don't reach out."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "worksheet": {
                    "type": "string",
                    "description": "Worksheet name. Default 'Leads'.",
                    "default": "Leads",
                },
                "row": {
                    "type": "object",
                    "description": (
                        "Data to log as key-value pairs. Common fields: "
                        "name, company, role, linkedin_url, email, source, "
                        "status, score, notes, outreach_sent, date"
                    ),
                },
            },
            "required": ["row"],
        },
    },
    {
        "name": "telegram_ask",
        "description": (
            "Send a message to Irie on Telegram and WAIT for her response before continuing. "
            "Use before any send action (email, LinkedIn invite). "
            "Also use when you need clarification or approval for something important. "
            "Returns 'approved', 'rejected', or the text of her reply."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to send. Include full context: who, what, why, and what you're about to do.",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional button labels to show. Default: ['Approve', 'Reject']",
                    "default": ["Approve", "Reject"],
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "telegram_notify",
        "description": (
            "Send a non-blocking update to Irie on Telegram. Does not wait for a response. "
            "Use for progress updates, completion summaries, or FYI messages."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Notification message to send.",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "post_linkedin",
        "description": (
            "Publish a text post to LinkedIn. "
            "IMPORTANT: always call telegram_ask for approval before calling this. "
            "Use when asked to create or publish a LinkedIn post. "
            "Text only, no images. Max 3000 characters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The full post text to publish on LinkedIn.",
                },
            },
            "required": ["text"],
        },
    },
]