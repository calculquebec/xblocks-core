0002 Handling Pointer Tags for Extracted XBlocks
####################################################

Date
****
2025-10-10

Status
******
Draft

Context
*******

In the Open edX ecosystem, course content is represented in **OLX (Open Learning XML)**.
OLX supports **two organizational formats** for defining blocks:

1. **Inline Format** - The block's full definition is written inline within its tag attributes.
2. **Pointer Tag Format** - The block's definition is stored separately, and the tag only contains a `url_name` attribute pointing to that definition file.

**Example - Inline Format**

.. code-block:: xml

   <vertical display_name="LTI">
     <lti url_name="lti_789b78a45ec7"
          button_text="Launch third-party stuff"
          display_name="LTI Testing"
          has_score="true"
          weight="20.0"/>
   </vertical>

**Example - Pointer Tag Format**

.. code-block:: xml

   <vertical display_name="LTI">
     <lti url_name="e73666f5807e47cbbd161d0d3aa5132b"/>
   </vertical>

Here, the ``<lti/>`` tag is a **pointer tag** because its configuration is stored separately at:

.. code-block:: xml

   lti/e73666f5807e47cbbd161d0d3aa5132b.xml

   <lti button_text="Launch third-party stuff"
        display_name="LTI Testing"
        has_score="true"
        weight="20.0"/>

Both formats are supported by edx-platform's `XmlMixin`, which handles:

- **Parsing:** detecting pointer tags and loading their definitions from the pointed-to file.
- **Exporting:** serializing blocks in pointer format.

However, this was disrupted when **built-in XBlocks** (such as `WordCloud`, `Annotatable`, `LTI`, `HTML`, `Poll`, `Video`, `Problem`) were **extracted from edx-platform** into a new repository: **xblocks-core**.

The key architectural change was that **extracted XBlocks no longer depend on `XmlMixin`** and instead inherit directly from the base `XBlock` class — following the *pure XBlock* pattern.
This transition removed pointer-tag handling functionality for those blocks.

Problem
*******

When extracted XBlocks are enabled (e.g., via `USE_EXTRACTED_<BLOCK_NAME>_BLOCK` settings) and a course containing pointer tag definitions is imported:

- The import path calls **XBlock.core's** ``parse_xml``, which only understands inline definitions.
- Since it does not recognize pointer tags, the system fails to load full definitions from referenced files.
- As a result, **empty XBlocks with default configurations** are created.

This issue was introduced when pointer-tag parsing logic from `XmlMixin` was no longer applied to extracted XBlocks.

Attempts & Exploration
**********************

Multiple approaches were explored to restore pointer-tag support for the extracted XBlocks:

1. **Add pointer-tag parsing to XBlock.core ``parse_xml``**

   - Attempted in `openedx/XBlock#830`.

   - This would modify XBlock core to recognize pointer nodes and load their definitions.

   - Omitted to avoid changing the XBlock API and core parsing logic.

2. **Implement pointer loading in edx-platform runtime (parent containers)**

   - PR `openedx/edx-platform#37133`.

   - The idea was to have parent container blocks (e.g., `VerticalBlock`, `SequentialBlock`) recognize child pointer tags and load their definitions.

   - This approach worked but required extending the same support to **external container XBlocks**, which would necessitate new interfaces in the XBlock API.

Alternatives To Consider
************************

1. **Core Interface (Containers or Leaf Blocks)**
   - Would unify pointer-tag logic within XBlock core.
   - Rejected for now due to the scope and cross-repo impact.

2. **XML Preprocessing Step in edx-platform**
   - Architecturally cleaner (resolve all pointer tags before XBlock parsing).
   - Rejected as a longer-term project not suited for immediate release needs.

Future Work
***********

Longer-term architectural improvements to consider:

- Introduce a **preprocessing layer** in edx-platform's OLX pipeline to centralize pointer resolution i.e., resolve all pointer tags into inline XML. (Alternative #1).
- Define a **standard XBlock API interface** for pointer-tag handling (Alternative #2).

References
**********

- `openedx/XBlock#830` - Initial attempt to add pointer-tag parsing to XBlock core
- `openedx/edx-platform#37133` - Runtime-based pointer resolution PR
- `xblocks-core` - Repository containing extracted XBlocks and new `PointerTagMixin`
