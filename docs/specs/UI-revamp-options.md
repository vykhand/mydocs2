# UI Revamp Options

| Field   | Value                       |
|---------|-----------------------------|
| Package | `mydocs-ui`                 |
| Version | 2.0 (proposal)              |
| Status  | Draft -- awaiting selection |
| Stack   | Vue 3, Vite, Tailwind CSS, Pinia |

## Design Brief

Rethink the UI around **search-driven document discovery**. The primary user flow is:

1. **Find** -- locate documents by name, content, or date via a clean search interface.
2. **Browse** -- scan results as thumbnails or list items in a gallery.
3. **Inspect** -- open a document viewer that jumps to the located content, with in-doc search, duplicates, and metadata on demand.

### Core Constraints (all options)

- **Three-panel layout**: left (facets/nav), center (gallery), right (viewer/detail).
- **Dual browse modes**: thumbnail grid and compact list, toggled instantly.
- **Search by**: file name, full-text content, date range -- always available.
- **Advanced options**: every screen exposes them, but **only on demand** (disclosure, popover, or drawer).
- **Document viewer**: embedded PDF viewer, in-doc search, potential-duplicates panel, metadata/advanced in collapsible sections.
- Same tech stack (Vue 3 / Vite / Tailwind / Pinia / PDF.js).

---

## Option A -- "Search-First Explorer"

*Inspiration: macOS Finder + Spotlight + Apple Mail three-column layout.*

### Philosophy

Search is the **entire entry point**. There is no separate "Documents" page vs "Search" page -- they are unified. Every interaction begins from the search bar, and the UI progressively reveals detail as you drill in.

### Layout (desktop >= 1024px)

```
+------------------------------------------------------------------+
|  [=] MyDocs          [ _____ Search _____ ]  [+Upload] [S] [?]   |
+------------------------------------------------------------------+
| LEFT SIDEBAR   | CENTER GALLERY               | RIGHT VIEWER     |
| 260px          | flex-1                        | 420px (or 0)     |
|                |                               |                  |
| [Navigation]   | Sort: Name | Date | Relevance | [doc name]      |
|  > All Docs    | View: [grid] [list]           | [PDF viewer]     |
|  > Recent      |                               |                  |
|  > Favorites   | +--+ +--+ +--+ +--+           | [in-doc search]  |
|                | |  | |  | |  | |  |           |                  |
| [Search Facets]| |  | |  | |  | |  |           | [> Duplicates]   |
|  Status [v]    | +--+ +--+ +--+ +--+           | [> Metadata]     |
|  File type [v] | +--+ +--+ +--+ +--+           | [> Advanced]     |
|  Tags [v]      | |  | |  | |  | |  |           |                  |
|  Date range    | +--+ +--+ +--+ +--+           |                  |
|  [> Advanced]  |                               |                  |
|                | 24 of 1,203 documents          |                  |
+----------------+-------------------------------+------------------+
```

### Key Behaviors

**Search bar (always visible in top bar)**
- Large, prominent, centered in the top bar. Keyboard shortcut: `/` or `Cmd+K`.
- Typing filters the gallery in real-time (300ms debounce).
- Searches file names AND content simultaneously; results are ranked by relevance.
- Empty search bar = show all documents (default sort: modified date desc).

**Left sidebar -- Navigation + Facets**
- Top section: quick-nav links (All Documents, Recent, Favorites/Starred).
- Below: **search facets** as collapsible sections:
  - **Status**: checkbox group (new, parsing, parsed, failed).
  - **File type**: checkbox group (PDF, DOCX, images, etc.).
  - **Tags**: searchable multi-select with chips.
  - **Date range**: compact date picker (created / modified toggle).
  - **Advanced facets** (on demand): document IDs, search mode selector (fulltext/vector/hybrid), score threshold.
- Active filters shown as removable chips above the facet area.
- Sidebar collapses to icon-rail on medium screens; becomes a slide-over drawer on mobile.

**Center gallery**
- **Thumbnail grid** (default): cards showing page-1 thumbnail, file name, status badge, date, top tags. Hover reveals quick actions (view, parse, delete).
- **List view**: compact rows with columns (name, type, status, pages, date, tags, relevance score). Sortable headers.
- Toggle between views via icon buttons in the gallery toolbar.
- Toolbar also has: sort dropdown, bulk-select toggle, pagination.
- When a search is active, result cards show a content snippet with highlighted terms beneath the thumbnail.
- Infinite scroll with virtual rendering (or paginated -- user preference in settings).

**Right panel -- Document Viewer**
- **Collapsed by default** (0px width). Clicking a gallery item opens it.
- Slides in from the right with a resize handle.
- Maximizable to full-width (hides gallery) with a button.
- Content:
  1. **PDF/Image viewer** at the top (PDF.js with page nav, zoom, text layer).
  2. **In-document search bar** -- searches within the current document's extracted text; highlights matches in the viewer and lists them as clickable results.
  3. **Potential duplicates** (collapsible): cards showing documents with matching SHA-256 or high content similarity. Collapsed by default.
  4. **Metadata** (collapsible): file size, MIME, page count, author, SHA-256, created/modified dates.
  5. **Tags** (collapsible, default open): editable chip list.
  6. **Advanced** (collapsible): raw JSON, parse config override, re-parse button.
- When opened from a search result, the viewer auto-navigates to the matching page and highlights the matched region.

**Upload**
- Upload is **not a separate page**. The `[+Upload]` button in the top bar opens a **modal/drawer overlay** with the drop zone, file queue, tag input, and progress. Advanced upload options (storage mode, recursive) available via a disclosure.
- After upload completes, new documents appear in the gallery automatically.

**Settings**
- Accessed via the gear icon (`[S]`) in the top bar, opens as a **settings drawer** from the right (not a full page). Contains theme, search defaults, parser defaults, connection info. Advanced settings behind a disclosure.

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| >= 1280px  | All three panels visible simultaneously |
| 1024-1279px | Sidebar collapsed to icon-rail; gallery + viewer |
| 768-1023px  | Gallery only; viewer opens as overlay; sidebar as drawer |
| < 768px     | Gallery full-width; bottom tab bar; viewer as full-screen overlay; facets in filter sheet |

### Routing

Since everything is unified, routing is simplified:

```
/                       → Gallery (all docs, no search)
/?q=term&type=pdf       → Gallery with search/filters (query params)
/doc/:id                → Gallery + viewer open for doc :id
/doc/:id?highlight=...  → Viewer open with search highlight
/upload                 → Gallery with upload modal open
/settings               → Gallery with settings drawer open
```

### Pros
- Minimal navigation -- the user never leaves the main screen.
- Feels fast and direct: type, see results, click, read.
- Search and browsing are the same thing (no mental model switch).
- URL-driven state makes sharing links to specific doc+search easy.

### Cons
- Complex state management for the three-panel layout.
- Mobile experience requires careful degradation of the three-panel design.
- Power users who want a dedicated upload dashboard may miss the full-page upload.

---

## Option B -- "Visual Library"

*Inspiration: Adobe Lightroom + Google Photos + Pinterest.*

### Philosophy

The document collection is presented as a **visual library**. Thumbnails are the primary interface. Search is powerful but doesn't dominate -- it's a tool you reach for, not the default state. The emphasis is on **browsing and visual recognition**.

### Layout (desktop >= 1024px)

```
+------------------------------------------------------------------+
| [=] MyDocs    [___ Search ___] [Filters v]   [+Upload] [S] [?]   |
+------------------------------------------------------------------+
| NAV RAIL | GALLERY                            | INSPECTOR        |
| 64px     | flex-1                              | 380px (or 0)    |
|          |                                     |                 |
| [icons]  | Collections:  All | Recent | Tagged  |                 |
| Upload   |                                     | [filename.pdf]  |
| Library  | +------+ +------+ +------+ +------+ | [large thumb]   |
| Search   | | thumb| | thumb| | thumb| | thumb| |                 |
| Cases    | | name | | name | | name | | name | | Status: Parsed  |
| Settings | | date | | date | | date | | date | | Pages: 12       |
|          | +------+ +------+ +------+ +------+ | Modified: 2d ago|
|          | +------+ +------+ +------+ +------+ |                 |
|          | | thumb| | thumb| | thumb| | thumb| | [Open Viewer]   |
|          | | name | | name | | name | | name | | [Parse] [Del]   |
|          | | date | | date | | date | | date | |                 |
|          | +------+ +------+ +------+ +------+ | [> Tags]        |
|          |                                     | [> Duplicates]  |
|          | Showing 48 of 1,203                  | [> Metadata]    |
|          |                                     | [> Advanced]    |
+----------+-------------------------------------+-----------------+
```

### Key Behaviors

**Top bar**
- Compact search bar (expands on focus to reveal search-in-content toggle, date range quick picks).
- `[Filters v]` button opens a **dropdown filter panel** below the top bar: status, file type, tags, date range. Active filters show as chips in the top bar. Advanced filter options (search mode, score threshold, document IDs) hidden behind `More filters...` link in the dropdown.

**Nav rail (left, always visible)**
- Narrow (64px) icon-only navigation rail. Always visible on desktop.
- Icons: Upload, Library (home), Search (opens dedicated search overlay), Cases, Settings.
- Hovering an icon shows a tooltip label.
- On mobile: converts to bottom tab bar.

**Gallery (center)**
- **Collection tabs** at the top: All, Recent (last 7 days), Tagged (grouped by tag), Favorites.
- **Thumbnail grid** is the primary view. Cards are larger than Option A -- emphasis on visual preview. Masonry layout adapts to varying aspect ratios.
- **List view** available via toggle -- switches to a compact table with sortable columns.
- Cards show: large thumbnail (page 1), file name (truncated), file type icon, date, status dot.
- Hover state: overlay with quick actions (Open, Parse, Star, Delete).
- Selection: click to select (opens inspector), Cmd/Ctrl+click for multi-select, drag-select rectangle.
- When search is active, cards show a relevance badge and snippet overlay.

**Inspector panel (right)**
- **Single-click** a document: inspector panel slides in with quick summary (large thumbnail, name, status, page count, dates, tags, quick actions).
- **Double-click** (or "Open Viewer" button): transitions to full document viewer mode.
- Inspector sections (all collapsible):
  - Quick info (always open)
  - Tags (editable, default open)
  - Potential duplicates (collapsed)
  - Full metadata (collapsed)
  - Advanced options (collapsed): raw JSON, parse config

**Full Document Viewer (overlay mode)**
- Triggered by double-click or "Open Viewer" in inspector.
- **Takes over the gallery area** (nav rail stays visible, inspector transforms into viewer sidebar).
- Layout:

```
+------------------------------------------------------------------+
| [<- Back to Library]   filename.pdf          [Download] [FS] [X] |
+------------------------------------------------------------------+
| NAV  | PDF/IMAGE VIEWER                     | VIEWER SIDEBAR     |
| RAIL | (full PDF.js viewer)                 | [In-doc search]    |
| 64px |                                      | [Page thumbnails]  |
|      | [page nav] [zoom] [fit]              | [> Search results] |
|      |                                      | [> Duplicates]     |
|      |                                      | [> Tags]           |
|      |                                      | [> Metadata]       |
|      |                                      | [> Advanced]       |
+------+--------------------------------------+--------------------+
```

- **In-document search**: text input at top of viewer sidebar. Matches highlighted in the PDF view, listed as clickable items in the sidebar.
- **Page thumbnails**: vertical strip in sidebar, scrollable. Active page highlighted.
- **Duplicates, Tags, Metadata, Advanced**: collapsible accordion sections in the sidebar.

**Search (dedicated overlay)**
- Clicking the Search icon in the nav rail opens a **full-screen search overlay** (like Spotlight or Cmd+K palettes but full-featured).
- Large centered search input with auto-focus.
- Below: real-time results as thumbnail cards + snippets.
- Left side of overlay: facets (same as filter dropdown but laid out vertically).
- Clicking a result closes the overlay and opens that document in the inspector/viewer.
- Advanced search options available via `Advanced...` button below the search input: search mode, vector config, hybrid tuning, score breakdown toggle.

**Upload**
- Clicking Upload in nav rail opens an **upload drawer** from the left (slides over the gallery).
- Full upload workflow: drop zone, file queue, tags, progress.
- Advanced options (storage mode, recursive) behind a disclosure.

**Settings**
- Full page (matches current approach), but accessible from nav rail icon.

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| >= 1280px  | Rail + gallery + inspector |
| 1024-1279px | Rail + gallery; inspector as slide-over |
| 768-1023px  | Rail collapses to hamburger; gallery full; inspector/viewer as overlay |
| < 768px     | Bottom tab bar; gallery full; everything else as overlays/sheets |

### Routing

```
/                       → Library gallery (All collection)
/collection/recent      → Recent collection
/collection/tagged/:tag → Filtered by tag
/doc/:id                → Gallery with inspector open
/doc/:id/view           → Full viewer mode
/doc/:id/view?search=.. → Viewer with in-doc search active
/search?q=...           → Search overlay open with query
/upload                 → Upload drawer open
/settings               → Settings page
```

### Pros
- Visually rich -- thumbnails make document recognition fast.
- Familiar paradigm (photo library / file manager).
- Clean separation between browse (gallery) and deep-dive (viewer).
- Inspector provides a lightweight preview without committing to full viewer.

### Cons
- Two-step to get to full viewer (select -> open) may feel slow for power users.
- Search is a separate overlay, not integrated into browsing flow.
- Masonry layout is more complex to implement and can feel less structured.

---

## Option C -- "Unified Workspace"

*Inspiration: Linear + Notion + VS Code editor layout.*

### Philosophy

A single adaptive workspace where **the layout morphs based on what you're doing**. There are no separate "pages" -- the workspace has zones that expand and contract. Search, browse, and view are all simultaneously accessible, and the user controls how much screen real estate each zone gets.

### Layout (desktop >= 1024px)

```
+------------------------------------------------------------------+
| [=] MyDocs     / Search documents...  (Cmd+K)     [+] [gear] [?]|
+------------------------------------------------------------------+
| SIDEBAR (280px, resizable)  | MAIN AREA (flex, split-able)       |
|                              |                                    |
| [Search]                     | +----- GALLERY / RESULTS --------+|
| [___ quick search ___]       | | Sort: Relevance | Name | Date  ||
|                              | | View: [grid] [list] [detail]   ||
| [Filters]                    | |                                 ||
| > Status                     | | +--+ +--+ +--+ +--+ +--+ +--+ ||
|   [x] Parsed                 | | |  | |  | |  | |  | |  | |  | ||
|   [ ] New                    | | +--+ +--+ +--+ +--+ +--+ +--+ ||
|   [ ] Failed                 | | +--+ +--+ +--+ +--+ +--+ +--+ ||
| > File Type                  | | |  | |  | |  | |  | |  | |  | ||
|   [x] PDF  [x] DOCX         | | +--+ +--+ +--+ +--+ +--+ +--+ ||
| > Tags                       | |                                 ||
|   [contract] [invoice] [x]   | +---------------------------------+|
| > Date Range                 |                                    |
|   [Jan 1] -> [Feb 11]       | +----- DOCUMENT VIEWER -----------+|
|                              | | [filename.pdf]  pg 3/12  100%  ||
| [> Advanced Filters]         | | [====== PDF CONTENT ==========]||
|                              | | [    (rendered page)           ]||
| ─────────────────────        | | [================================]||
| [Navigation]                 | |                                 ||
|  All Documents (1,203)       | | [in-doc search] [> Dupes]      ||
|  Recent                      | | [> Metadata]    [> Advanced]   ||
|  Starred                     | +---------------------------------+|
|  Cases >                     |                                    |
|                              |                                    |
| ─────────────────────        |                                    |
| [> Upload Zone]              |                                    |
+------------------------------+------------------------------------+
```

### Key Behaviors

**Search bar (top bar, global)**
- Always visible, spans center of top bar.
- `Cmd+K` focuses it. Typing begins filtering immediately.
- Search covers file names AND content. Toggle between them via a small dropdown within the search input (`In: Names | Content | Both`).
- Results update the gallery zone in real-time.

**Left sidebar -- Everything in one place**
- The sidebar is a unified control panel, top to bottom:
  1. **Quick search** input (mirrors the top bar search, either can be used).
  2. **Filters** -- always-visible, collapsible facet groups:
     - Status (checkboxes)
     - File type (checkboxes)
     - Tags (chip selector with autocomplete)
     - Date range (inline mini calendar or preset buttons: Today, Last 7d, Last 30d, Custom)
  3. **Advanced filters** (disclosure): search mode, vector/hybrid config, score threshold, document IDs.
  4. **Separator**
  5. **Navigation shortcuts**: All Documents (with count), Recent, Starred, Cases (expandable sub-list).
  6. **Separator**
  7. **Upload zone** (disclosure): expands to show a compact drop zone right in the sidebar. Drag files onto it for quick upload. For full upload workflow, an "Expand" button opens a proper upload modal.
- Sidebar is resizable via drag handle. Can be collapsed entirely to a 48px icon strip.
- Active filters shown as a horizontal chip bar at the very top of the main area.

**Main area -- Adaptive split**
- The main area is a **vertical split** between the gallery (top) and the viewer (bottom). The split is resizable.
- Default state: gallery takes 100% (viewer hidden).
- Selecting a document: split appears -- gallery shrinks to ~40%, viewer takes ~60%.
- Three view modes for the gallery zone:
  1. **Grid**: thumbnail cards (name, date, status, type icon).
  2. **List**: compact table rows.
  3. **Detail**: wider cards with thumbnail + snippet + metadata preview (like email preview pane items).
- User can also switch to a **horizontal split** (gallery left, viewer right) via a layout toggle.

**Document viewer zone**
- Appears when a document is selected. Can be expanded to full main area (gallery hidden) or collapsed back.
- Top toolbar: document name, page navigation, zoom, download, fullscreen, close.
- **PDF/Image viewer**: full PDF.js rendering with text layer.
- **In-document search**: small search bar embedded in the viewer toolbar. Results highlighted in the PDF, with a collapsible hit-list panel.
- Below the viewer (or in a tabbed bar at the bottom):
  - **Potential duplicates** tab: shows documents with matching hashes or similar content. Each as a small card with name + similarity score.
  - **Metadata** tab: full file metadata table.
  - **Advanced** tab: raw JSON, parse config, re-parse.
  - **Tags** tab: editable tag chips.
- When opened from a search result, the viewer auto-navigates to the matched page and highlights the matched text region.

**Upload**
- Quick: drag files onto the sidebar upload zone for fast ingestion.
- Full: click "Expand" or use the `[+]` button in the top bar to open a modal with the complete upload workflow (drop zone, queue, tags, progress, advanced options).

**Settings**
- Gear icon opens a **settings modal** (not a page). Keeps the user in context.
- Tabs within the modal: Appearance, Search Defaults, Parser, Connection.

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| >= 1440px  | Sidebar + gallery + viewer (horizontal split option) |
| 1024-1439px | Sidebar + main area (vertical split only) |
| 768-1023px  | Sidebar as drawer; main area full; viewer as bottom sheet |
| < 768px     | Bottom tab bar; gallery full; sidebar as filter sheet; viewer as full-screen overlay |

### Routing

```
/                       → Workspace (all docs, no selection)
/?q=term&status=parsed  → Workspace with active search/filters
/doc/:id                → Workspace with doc selected (viewer open)
/doc/:id/search?q=...   → Viewer open with in-doc search
```

### Pros
- Maximum flexibility -- user controls the layout.
- No context switches at all -- everything is in one place.
- Power users can customize the workspace to their preferred split ratios.
- Compact upload zone in sidebar means uploading doesn't interrupt workflow.

### Cons
- Highest implementation complexity (resizable panels, split management).
- Risk of feeling overwhelming if not carefully tuned.
- Resizable panels can be finicky on touch devices.
- Less visually guided than Option B -- relies on user configuring their layout.

---

## Comparison Matrix

| Dimension                  | A: Search-First Explorer | B: Visual Library     | C: Unified Workspace   |
|----------------------------|--------------------------|-----------------------|------------------------|
| **Primary metaphor**       | Search engine + email    | Photo library         | IDE / workspace        |
| **Entry point**            | Search bar               | Visual browsing       | Adaptive (search or browse) |
| **Navigation model**       | Almost none (1 screen)   | Nav rail + overlays   | Sidebar shortcuts      |
| **Search integration**     | Fully integrated         | Separate overlay      | Integrated + sidebar   |
| **Three-panel layout**     | Facets / Gallery / Viewer | Rail / Gallery / Inspector | Sidebar / Gallery / Viewer |
| **Thumbnail emphasis**     | Medium                   | High (large cards)    | Medium (configurable)  |
| **List view**              | Toggle                   | Toggle                | Toggle (+ detail mode) |
| **Advanced options**       | Disclosure in sidebar + viewer | Disclosure everywhere | Disclosure in sidebar + tabs |
| **In-doc search**          | Viewer sidebar           | Viewer sidebar        | Viewer toolbar + panel |
| **Duplicates**             | Viewer collapsible       | Inspector collapsible | Viewer tab             |
| **Upload**                 | Modal from top bar       | Left drawer           | Sidebar zone + modal   |
| **Settings**               | Right drawer             | Full page             | Modal with tabs        |
| **Mobile approach**        | Progressive collapse     | Overlays/sheets       | Sheets/overlays        |
| **Implementation effort**  | Medium                   | Medium-High           | High                   |
| **Best for**               | Search-heavy workflows   | Visual browsing       | Power users            |

---

## Shared Components (all options)

Regardless of which option is chosen, these components are shared:

### Document Card (thumbnail mode)
```
+-------------------+
|  [page 1 thumb]   |
|                   |
|  filename.pdf     |
|  PDF  * Parsed    |
|  Feb 10, 2026     |
|  [contract] [inv] |
+-------------------+
```
- Aspect ratio: 3:4 (portrait-biased for documents).
- Thumbnail: server-generated page-1 preview, lazy-loaded.
- On hover: subtle scale + shadow lift + quick action icons overlay.
- Search mode: snippet text appears below the card metadata.

### Document Row (list mode)
```
+--+----------------------------------------------------------+------+--------+-------+-----------+
|  | filename.pdf                                             | PDF  | Parsed | 12 pg | Feb 10    |
|  | "...the contract stipulates that the party shall..."     |      |        |       | [tags...] |
+--+----------------------------------------------------------+------+--------+-------+-----------+
```
- Checkbox for bulk selection.
- Snippet row only visible when search is active.

### Search Facets
All options use the same facet types:
- **Status**: checkbox group with counts.
- **File type**: checkbox group with icons and counts.
- **Tags**: autocomplete multi-select, selected shown as chips.
- **Date range**: preset buttons (Today, 7d, 30d, 90d, Custom) + calendar picker.
- **Advanced** (on demand): search mode, score threshold, hybrid tuning, document ID filter.

### Document Viewer
All options use the same viewer internals:
- PDF.js canvas + text layer.
- Page navigation (prev/next, input, keyboard).
- Zoom controls (in/out, fit-width, fit-page, pinch).
- In-document search with highlight.
- Collapsible sections: Duplicates, Metadata, Tags, Advanced.

### Collapsible / On-Demand Pattern
Every "advanced" or "detail" section uses the same disclosure pattern:
```
[> Section Name]              ← collapsed (default)
[v Section Name]              ← expanded
   Content here...
```
- Chevron icon animates on toggle.
- State persisted per-section in localStorage.
- Keyboard accessible (Enter/Space to toggle).

---

## Recommendation

**Option A (Search-First Explorer)** is recommended as the starting point because:

1. It most directly addresses the brief: search as entry point, three-panel layout, everything on one screen.
2. It's the most natural fit for a document management tool where finding things fast is the primary workflow.
3. Medium implementation complexity -- reuses most existing components with layout restructuring.
4. Clean URL-driven state (query params) makes the app shareable and bookmarkable.
5. Degrades gracefully to mobile (progressive panel collapse).

Option B elements (larger thumbnails, masonry, collections) can be incorporated as gallery enhancements. Option C's resizable split can be added later as a power-user feature.
