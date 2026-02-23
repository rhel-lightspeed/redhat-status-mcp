"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def components_response() -> dict:
    """Components with groups, children, and mixed degraded states."""
    return {
        "page": {
            "id": "dn6mqn7xvzz3",
            "name": "Red Hat",
            "url": "https://status.redhat.com",
            "time_zone": "Etc/UTC",
            "updated_at": "2026-02-23T15:43:32.578Z",
        },
        "components": [
            {
                "id": "2tj5dnkngjyq",
                "name": "console.redhat.com",
                "status": "operational",
                "group": True,
                "group_id": None,
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "components": ["lv08d42rtt6m", "sr44t0d1q1xy", "twdq5x4c86pc"],
                "position": 1,
                "description": None,
                "showcase": False,
            },
            {
                "id": "lv08d42rtt6m",
                "name": "Ansible Automation Platform - Automation Analytics",
                "status": "operational",
                "group": False,
                "group_id": "2tj5dnkngjyq",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 1,
                "description": None,
                "showcase": False,
            },
            {
                "id": "sr44t0d1q1xy",
                "name": "Ansible Automation Platform - Automation Hub",
                "status": "degraded_performance",
                "group": False,
                "group_id": "2tj5dnkngjyq",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 2,
                "description": None,
                "showcase": False,
            },
            {
                "id": "twdq5x4c86pc",
                "name": "Cost Management",
                "status": "partial_outage",
                "group": False,
                "group_id": "2tj5dnkngjyq",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 3,
                "description": None,
                "showcase": False,
            },
            {
                "id": "fd46lxthfjrs",
                "name": "Container Registries",
                "status": "operational",
                "group": True,
                "group_id": None,
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "components": ["78htzl27599b", "trp61wc39x6l"],
                "position": 2,
                "description": None,
                "showcase": False,
            },
            {
                "id": "78htzl27599b",
                "name": "registry.redhat.io",
                "status": "operational",
                "group": False,
                "group_id": "fd46lxthfjrs",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 1,
                "description": None,
                "showcase": False,
            },
            {
                "id": "trp61wc39x6l",
                "name": "registry.access.redhat.com",
                "status": "operational",
                "group": False,
                "group_id": "fd46lxthfjrs",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 2,
                "description": None,
                "showcase": False,
            },
            {
                "id": "7257pmmcwwx4",
                "name": "access.redhat.com",
                "status": "operational",
                "group": True,
                "group_id": None,
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "components": ["8j62vqmy53rw"],
                "position": 3,
                "description": None,
                "showcase": False,
            },
            {
                "id": "8j62vqmy53rw",
                "name": "Homepage",
                "status": "operational",
                "group": False,
                "group_id": "7257pmmcwwx4",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 1,
                "description": None,
                "showcase": False,
            },
            {
                "id": "8hd2kq9q34lv",
                "name": "bugzilla.redhat.com",
                "status": "operational",
                "group": True,
                "group_id": None,
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "components": ["zkg4fplxxxlr"],
                "position": 4,
                "description": None,
                "showcase": False,
            },
            {
                "id": "zkg4fplxxxlr",
                "name": "Homepage",
                "status": "operational",
                "group": False,
                "group_id": "8hd2kq9q34lv",
                "page_id": "dn6mqn7xvzz3",
                "only_show_if_degraded": False,
                "position": 1,
                "description": None,
                "showcase": False,
            },
        ],
    }


@pytest.fixture
def incidents_response() -> dict:
    """Unresolved incidents fixture with full timeline."""
    return {
        "page": {
            "id": "dn6mqn7xvzz3",
            "name": "Red Hat",
            "url": "https://status.redhat.com",
            "time_zone": "Etc/UTC",
            "updated_at": "2026-02-23T15:43:32.578Z",
        },
        "incidents": [
            {
                "id": "abc123xyz",
                "name": "Elevated error rates on console.redhat.com",
                "status": "investigating",
                "impact": "major",
                "created_at": "2026-02-23T14:00:00.000Z",
                "updated_at": "2026-02-23T15:30:00.000Z",
                "started_at": "2026-02-23T14:00:00.000Z",
                "resolved_at": None,
                "shortlink": "https://stspg.io/abc123xyz",
                "incident_updates": [
                    {
                        "id": "upd002",
                        "status": "investigating",
                        "body": (
                            "We are continuing to investigate elevated error rates. "
                            "Some users may experience issues accessing the console."
                        ),
                        "created_at": "2026-02-23T15:30:00.000Z",
                        "updated_at": "2026-02-23T15:30:00.000Z",
                        "display_at": "2026-02-23T15:30:00.000Z",
                        "affected_components": [
                            {
                                "code": "2tj5dnkngjyq",
                                "name": "console.redhat.com",
                                "new_status": "major_outage",
                                "old_status": "operational",
                            }
                        ],
                    },
                    {
                        "id": "upd001",
                        "status": "investigating",
                        "body": (
                            "We are investigating reports of elevated error rates on "
                            "console.redhat.com."
                        ),
                        "created_at": "2026-02-23T14:00:00.000Z",
                        "updated_at": "2026-02-23T14:00:00.000Z",
                        "display_at": "2026-02-23T14:00:00.000Z",
                        "affected_components": [],
                    },
                ],
                "components": [
                    {
                        "id": "2tj5dnkngjyq",
                        "name": "console.redhat.com",
                        "status": "major_outage",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def incidents_empty() -> dict:
    return {
        "page": {
            "id": "dn6mqn7xvzz3",
            "name": "Red Hat",
            "url": "https://status.redhat.com",
            "time_zone": "Etc/UTC",
            "updated_at": "2026-02-23T15:43:32.578Z",
        },
        "incidents": [],
    }


@pytest.fixture
def maintenances_upcoming() -> dict:
    return {
        "page": {
            "id": "dn6mqn7xvzz3",
            "name": "Red Hat",
            "url": "https://status.redhat.com",
            "time_zone": "Etc/UTC",
            "updated_at": "2026-02-23T15:43:32.578Z",
        },
        "scheduled_maintenances": [
            {
                "id": "mnt001xyz",
                "name": "Scheduled maintenance on registry.redhat.io",
                "status": "scheduled",
                "impact": "maintenance",
                "created_at": "2026-02-20T10:00:00.000Z",
                "updated_at": "2026-02-20T10:00:00.000Z",
                "scheduled_for": "2026-02-25T02:00:00.000Z",
                "scheduled_until": "2026-02-25T04:00:00.000Z",
                "incident_updates": [
                    {
                        "id": "mupd001",
                        "status": "scheduled",
                        "body": (
                            "We will be performing scheduled maintenance on "
                            "registry.redhat.io. Expect brief interruptions."
                        ),
                        "created_at": "2026-02-20T10:00:00.000Z",
                        "updated_at": "2026-02-20T10:00:00.000Z",
                        "display_at": "2026-02-20T10:00:00.000Z",
                    }
                ],
                "components": [
                    {
                        "id": "78htzl27599b",
                        "name": "registry.redhat.io",
                        "status": "operational",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def maintenances_active() -> dict:
    return {
        "page": {
            "id": "dn6mqn7xvzz3",
            "name": "Red Hat",
            "url": "https://status.redhat.com",
            "time_zone": "Etc/UTC",
            "updated_at": "2026-02-23T15:43:32.578Z",
        },
        "scheduled_maintenances": [
            {
                "id": "mnt002xyz",
                "name": "Active maintenance on console.redhat.com",
                "status": "in_progress",
                "impact": "maintenance",
                "created_at": "2026-02-23T01:00:00.000Z",
                "updated_at": "2026-02-23T02:00:00.000Z",
                "scheduled_for": "2026-02-23T02:00:00.000Z",
                "scheduled_until": "2026-02-23T06:00:00.000Z",
                "incident_updates": [],
                "components": [
                    {
                        "id": "2tj5dnkngjyq",
                        "name": "console.redhat.com",
                        "status": "operational",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def maintenances_empty() -> dict:
    return {
        "page": {
            "id": "dn6mqn7xvzz3",
            "name": "Red Hat",
            "url": "https://status.redhat.com",
            "time_zone": "Etc/UTC",
            "updated_at": "2026-02-23T15:43:32.578Z",
        },
        "scheduled_maintenances": [],
    }
