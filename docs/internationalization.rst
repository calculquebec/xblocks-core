.. _chapter-i18n:

Internationalization
####################
All user-facing text content should be marked for translation. Even if this application is only run in English, our
open source users may choose to use another language. Marking content for translation ensures our users have
this choice.

Follow the `internationalization coding guidelines`_ in the Open edX Developer's Guide when developing new features.

.. _internationalization coding guidelines: https://docs.openedx.org/en/latest/developers/references/developer_guide/internationalization/i18n.html

Project structure
*****************
Each XBlock in this repository manages its own translations independently:

- **Config**: ``src/xblock_<name>/conf/locale/config.yaml`` -- defines supported languages and
  ignored directories.
- **Source strings**: ``src/xblock_<name>/conf/locale/en/LC_MESSAGES/text.po`` -- extracted
  English strings (Python, HTML, and JavaScript combined into a single file).
- **Transifex mapping**: ``src/xblock_<name>/.tx/config`` -- maps the local ``conf/locale/``
  paths to the Transifex resource for that XBlock.
- **Combined source file**: ``src/xblocks_core_locale/conf/locale/en/LC_MESSAGES/django.po`` -- all
  per-xblock ``text.po`` files merged into one, used by the openedx-translations pipeline (OEP-58).

All ``make`` targets iterate over every XBlock that has a ``conf/`` directory automatically.

Updating Translations
*********************
This project follows `OEP-58`_ for translation management. Translations are managed centrally through
the `openedx-translations`_ repository rather than directly via Transifex.

.. _OEP-58: https://docs.openedx.org/en/latest/developers/concepts/oep58.html
.. _openedx-translations: https://github.com/openedx/openedx-translations

**How the pipeline works:**

1. A daily GitHub Actions workflow in openedx-translations clones this repo and runs
   ``make extract_translations``.
2. The combined ``django.po`` file at ``src/xblocks_core_locale/conf/locale/en/`` is committed to
   openedx-translations.
3. The Transifex GitHub App syncs source strings to the ``openedx-translations`` Transifex project
   under the ``open-edx`` organization.
4. The Open edX translation community translates strings on `Transifex`_.
5. Reviewed translations sync back to the openedx-translations repository.

Since these XBlocks were extracted from edx-platform, many strings already have existing translations
in Transifex. The pipeline preserves these so translators do not need to re-translate them.

.. _Transifex: https://www.transifex.com/

**Direct Transifex CLI (alternative):**

Each XBlock also has a ``.tx/config`` for direct Transifex CLI usage when the openedx-translations
pipeline is not available. This requires access to the ``open-edx`` Transifex organization.

1. Install the Transifex CLI: ``make install_transifex_client``
2. Set your API token: ``export TX_TOKEN=<your-api-token>``

..  list-table::
    :widths: 35 65
    :header-rows: 1

    * - Target
      - Description
    * - ``make extract_translations``
      - Extract translatable strings into ``text.po`` for each XBlock
    * - ``make compile_translations``
      - Compile ``.po`` files into ``.mo`` files for each XBlock
    * - ``make pull_translations``
      - Pull translations from Transifex for each XBlock
    * - ``make push_translations``
      - Extract and push source translations to Transifex for each XBlock
    * - ``make validate_translations``
      - Full validation pipeline (dummy build + source drift detection)
    * - ``make detect_changed_source_translations``
      - Check if source ``.po`` files are up-to-date with the code
    * - ``make dummy_translations``
      - Generate dummy Esperanto/RTL ``.po`` files for testing
    * - ``make build_dummy_translations``
      - Generate and compile dummy translations
    * - ``make install_transifex_client``
      - Install the Transifex CLI

Fake Translations
*****************
As you develop features it may be helpful to know which strings have been marked for translation, and which are not.
Use the ``dummy_translations`` make target for this purpose. This target will extract all strings marked for
translation and generate fake translations in the Esperanto (eo) and fake-RTL (rtl) language directories.
Run ``make compile_translations`` afterwards (or use ``make build_dummy_translations`` to do both at once).

You can trigger the display of the translations by setting your browser's language to Esperanto (eo), and navigating to
a page on the site. Instead of plain English strings, you should see specially-accented English strings that look
like this:

    Thé Fütüré øf Ønlïné Édüçätïøn Ⱡσяєм ι# Før änýøné, änýwhéré, änýtïmé Ⱡσяєм #

