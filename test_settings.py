"""
Minimal Django settings for running tests on xblocks-core.
"""

from pathlib import Path

from django.http import HttpResponse
from django.urls import re_path

BASE_DIR = Path(__file__).resolve().parent
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "submissions",
    "edxval",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
    }
}


def dummy_callback(_request, *_args, **_kwargs):
    """
    Minimal placeholder view for test URL patterns.
    Underscored arguments silence lint warnings for unused variables.
    """
    return HttpResponse("OK")


ROOT_URLCONF = type(
    "URLConf",
    (),
    {
        "urlpatterns": [
            re_path(
                r"^courses/(?P<course_id>.+)/xqueue/(?P<userid>[^/]+)/(?P<mod_id>.+)/(?P<dispatch>[^/]+)$",
                dummy_callback,
                name="xqueue_callback",
            ),
        ]
    },
)

LMS_ROOT_URL = "http://localhost:8000"

# Code jail REST service
ENABLE_CODEJAIL_REST_SERVICE = False

# Set the python package.module.function that is reponsible of
# calling the remote service in charge of jailed code execution
CODE_JAIL_REST_SERVICE_REMOTE_EXEC = "xblock_problem.capa.safe_exec.remote_exec.send_safe_exec_request_v0"

# Set the codejail remote service host
CODE_JAIL_REST_SERVICE_HOST = "http://127.0.0.1:8550"

# Set the number of seconds LMS will wait to establish an internal
# connection to the codejail remote service.
CODE_JAIL_REST_SERVICE_CONNECT_TIMEOUT = 0.5  # time in seconds

# Set the number of seconds LMS/CMS will wait for a response from the
# codejail remote service endpoint.
CODE_JAIL_REST_SERVICE_READ_TIMEOUT = 3.5  # time in seconds

# CAPA External Code Evaluation #

# Used with XQueue
XQUEUE_WAITTIME_BETWEEN_REQUESTS = 5  # seconds
XQUEUE_INTERFACE = {
    "url": "http://localhost:18040",
    "basic_auth": ["edx", "edx"],
    "django_auth": {"username": "lms", "password": "password"},
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "src" / "xblock_problem" / "capa" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

TRANSCRIPT_LANG_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
