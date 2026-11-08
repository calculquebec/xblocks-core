"""
Constants used by DjangoXBlockUserService
"""

# This is the view that will be rendered to display the XBlock in the LMS.
# It will also be used to render the block in "preview" mode in Studio, unless
# the XBlock also implements author_view.
STUDENT_VIEW = "student_view"

# This is the view that will be rendered to display the XBlock in the LMS for unenrolled learners.
# Implementations of this view should assume that a user and user data are not available.
PUBLIC_VIEW = "public_view"

# The personally identifiable user ID.
ATTR_KEY_USER_ID = "edx-platform.user_id"
# The country code determined from the user's request IP address.
ATTR_KEY_REQUEST_COUNTRY_CODE = "edx-platform.request_country_code"
