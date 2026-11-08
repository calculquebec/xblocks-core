"""
Django App configuration for the xblocks-core Discussion XBlock.
"""

from django.apps import AppConfig


class DiscussionAppConfig(AppConfig):
    """
    Configuration for the Discussion XBlock Django application.

    Why are we registering this as a Django App?
    --------------------------------------------
    By default, Django's template engine (specifically the `app_directories` loader)
    only discovers `templates/` folders that belong to an app listed in `INSTALLED_APPS`.

    Since XBlocks are inherently isolated components, they are not typically added
    to the LMS/CMS global `INSTALLED_APPS`. As a result, any standard Django templates
    (.html files) inside this block would be invisible to the core Open edX platform
    when it attempts to route or render them natively.

    Instead of forcing repository consumers to manually modify `lms/envs/common.py`
    or use deployment-specific Tutor plugins to append to `TEMPLATES['DIRS']`, we
    leverage the Open edX Django App Plugin Framework (`plugin_app`). This hook
    dynamically injects this module into `INSTALLED_APPS` at runtime.

    This automatically exposes our `templates/` directory to the platform natively
    without manual intervention.

    References:

    - Open edX Plugin App Framework:
      https://docs.openedx.org/projects/edx-django-utils/en/latest/plugins/how_tos/how_to_create_a_plugin_app.html

    - Django App Directories Loader:
      https://docs.djangoproject.com/en/stable/ref/templates/api/#django.template.loaders.app_directories.Loader

    """

    name = "xblock_discussion"
    label = "xblock_discussion"
    verbose_name = "XBlocks Core - Discussion Templates"

    plugin_app = {
        "settings_config": {
            "lms.djangoapp": {
                "default": "",
            },
            "cms.djangoapp": {
                "default": "",
            },
        },
    }
