# UI Specification

| Field   | Value                |
|---------|----------------------|
| Package | `mydocs-ui`          |
| Version | 2.0                  |
| Status  | Draft                |
| Stack   | Vue 3, Vite, Tailwind CSS, Pinia |

## 1. Overview

A single-page application providing a modern, professional interface for document management, search, and case organization. The UI communicates exclusively with the FastAPI backend via `/api/v1/` endpoints.

The UI follows a **unified gallery architecture**: a single `GalleryView` serves as the primary entry point for documents and search, with upload and settings presented as modal/drawer overlays. A resizable right-side panel hosts the document viewer inline, avoiding full-page navigation. Cases have their own gallery view.

### 1.1 Design Principles

- **Mobile-first responsive** -- usable on phones, tablets, and desktops.
- **Simple by default, powerful when needed** -- every feature has a sensible default; advanced controls are hidden behind an "Advanced Settings" toggle.
- **Consistent visual language** -- clean typography, generous whitespace, subtle shadows, and a neutral color palette with a single accent color.
- **Immediate feedback** -- every user action produces visible feedback (toasts, progress bars, skeleton loaders).
- **Gallery-first** -- documents are browsed in a unified gallery with inline viewer, not navigated across separate pages.

### 1.2 Technology Stack

| Layer          | Choice               | Rationale                              |
|----------------|----------------------|----------------------------------------|
| Framework      | Vue 3 (Composition API, `<script setup>`) | Reactive, lightweight, strong ecosystem |
| Build          | Vite                 | Fast HMR, native ESM                   |
| Styling        | Tailwind CSS 4       | Utility-first, responsive breakpoints  |
| State          | Pinia + `pinia-plugin-persistedstate` | Official Vue store, devtools support, `localStorage` persistence |
| HTTP           | Axios                | Interceptors for error handling         |
| Routing        | Vue Router 4         | Lazy loading, route metadata for modals |
| Icons          | Lucide Vue Next      | Consistent, tree-shakeable icon set     |
| PDF Viewer     | PDF.js (`pdfjs-dist`)| Renders PDF pages on canvas, supports text layer and highlight annotations |
| Date Picker    | `@vuepic/vue-datepicker` | Rich date-range selection component  |
| Notifications  | Vue Toastification   | Toast messages for user feedback        |
| Auth           | `@azure/msal-browser` | Microsoft Entra ID OAuth redirect flow  |

## 2. Layout & Navigation

### 2.1 Shell Layout

#### Wide / Desktop (>= 1024px)

```
+-----------------------------------------------------------------------+
| Top Bar  [≡] [mydocs]   [____Search (Cmd+K)____]  [Upload] [⚙] [◑] [☀]|
+------------+------------------------------------+---------------------+
|            |                                    |                     |
| Sidebar    |        Gallery / Content           |   Right Viewer      |
| [Docs|Cases]        (grid or list)              |   Panel (resizable) |
| [Filters]  |                                    |                     |
| - Status   |                                    |   [Document name]   |
| - File Type|                                    |   [PDF/Image view]  |
| - Doc Type |                                    |   [Page nav]        |
| - Sort     |                                    |   [Metadata]        |
| - Advanced |                                    |   [Tags]            |
|   - Tags   |                                    |   [Advanced]        |
|   - Date   |                                    |                     |
+------------+------------------------------------+---------------------+
```

#### Tablet (768–1023px)

```
+-----------------------------------------------------------------------+
| Top Bar  [≡] [mydocs]   [____Search____]   [Upload] [⚙] [◑] [☀]      |
+-----------------------------------------------------------------------+
|                                                                       |
|              Gallery / Content (full width)                            |
|                                                                       |
+-----------------------------------------------------------------------+
  Sidebar: opens as drawer overlay on [≡] tap
  Viewer: opens as full-screen overlay
```

#### Mobile (< 768px)

```
+-----------------------------------------------------------------------+
| Top Bar  [mydocs]                        [Upload] [⚙] [◑] [☀]        |
+-----------------------------------------------------------------------+
|                                                                       |
|              Gallery / Content (full width)                            |
|                                                                       |
+-----------------------------------------------------------------------+
| [Documents]         [Cases]         [More ...]                        |
+-----------------------------------------------------------------------+
  Search bar: hidden (accessible via More menu or Cmd+K)
  Sidebar: hidden; filters via MobileFilterSheet
  Viewer: opens as full-screen overlay
  More menu: bottom sheet with Upload, Settings links
```

- **Top Bar** -- fixed; contains sidebar toggle and app logo on the left, a centered search bar with `Cmd+K` shortcut hint, and action buttons on the right: Upload, Settings, Simple/Advanced mode toggle, and theme cycle (Light → Dark → System).
- **Sidebar** -- contains two tab buttons (Documents / Cases) at the top. When the Documents tab is active, displays collapsible filter sections (status, file type, document type, sort, advanced filters with tags and date range). When collapsed, shows only icon buttons. On tablet, opens as a drawer overlay with backdrop. Hidden on mobile.
- **Main Content Area** -- scrollable; renders the active route (`GalleryView` or `CasesGalleryView`).
- **Right Viewer Panel** -- resizable side panel (300px – 75% viewport, default 420px) for the document viewer. Appears when a document is opened. On desktop/wide: inline panel with drag-to-resize handle. On tablet/mobile: full-screen overlay. The PDF viewer fills the full vertical space between the header and a bottom toolbar. Metadata, tags, duplicates, and advanced sections are in a slide-over info panel toggled by an info button in the header. Filter sections (Status, File Type) in the sidebar start **collapsed** by default to reduce visual clutter.
- **Mobile Tab Bar** -- bottom navigation with Documents, Cases, and More tabs. More opens a bottom sheet with Upload and Settings links.

### 2.2 Responsive Breakpoints

| Breakpoint | Width        | Sidebar Behavior              | Viewer Behavior          |
|------------|--------------|-------------------------------|--------------------------|
| `sm`       | < 768px      | Hidden; bottom tab-bar        | Full-screen overlay      |
| `md`       | 768–1023px   | Drawer overlay on toggle      | Full-screen overlay      |
| `lg`       | 1024–1279px  | Icon rail (collapsible)       | Inline side panel        |
| `xl`       | >= 1280px    | Expanded (icons + labels)     | Inline side panel        |

### 2.3 Simple / Advanced Mode

A global toggle stored in Pinia and persisted to `localStorage`.

- **Simple mode** -- hides advanced search parameters, parse config overrides, embedding options, and hybrid search tuning. Uses backend defaults.
- **Advanced mode** -- exposes all configurable fields as described in each section below.

## 3. Views & Features

### 3.1 Upload (`/upload` -- modal overlay)

Upload is presented as a **modal overlay** on top of the gallery view. Navigating to `/upload` renders `GalleryView` with the `UploadModal` component displayed over it.

#### UI Elements

| Element              | Description |
|----------------------|-------------|
| Drop zone            | Large dashed-border area accepting drag-and-drop of files or folders. Also clickable to open a file picker. |
| Folder picker button | Separate button that opens a directory picker (`webkitdirectory`). |
| File list            | Table/list showing queued files before upload: name, size, type. Each row has a remove button. |
| Tags input           | Chip/tag input allowing the user to assign one or more tags to the entire batch before upload. |
| Upload button        | Starts the ingestion process. Disabled when the queue is empty. |
| Progress section     | Per-file progress bars + overall progress bar. Shows status (uploading, ingested, failed). |

#### Advanced Mode Additions

| Element              | Description |
|----------------------|-------------|
| Storage mode select  | Dropdown: `managed` (default) / `external`. |
| Recursive toggle     | Checkbox (default on) -- whether to recurse into subfolders. |

#### API Integration

- Uploads files to the server, then calls `POST /api/v1/documents/ingest` with `{ source, storage_mode, tags, recursive }`.
- On success, displays a summary with document IDs and a link to browse.
- Optionally triggers parse immediately via `POST /api/v1/documents/parse` (toggle: "Parse after upload").

### 3.2 Gallery View (`/` -- main entry point)

The unified gallery serves as both the document browser and the search results view. URL query parameters drive the mode:

- **No `?q=` param** -- displays the document grid/list with filters and pagination.
- **With `?q=<term>`** -- displays search results (hybrid search on pages by default).

#### Gallery Toolbar

| Element              | Description |
|----------------------|-------------|
| Result count         | Displays total number of documents or search results. |
| View mode toggle     | Grid / List icons to switch `galleryViewMode` in the app store. |

#### Document Gallery Mode (no search query)

| Element              | Description |
|----------------------|-------------|
| Document grid/list   | `DocumentGrid` renders documents as cards (grid mode) or rows (list mode). Each item shows file name, type badge, status badge, tags, and created date. Clicking opens the Right Viewer Panel. |
| Sidebar filters      | In the sidebar: collapsible status filter (checkboxes), file type filter (checkboxes), document type dropdown, sort-by and sort-order dropdowns. Advanced filters section (collapsed by default) contains tags input and date range picker. Active filters shown as removable chips above the filter sections. |
| Pagination           | Page size selector (25, 50, 100) and page navigation at the bottom. |
| Bulk actions bar     | Appears when one or more documents are selected. Actions: Parse, Add Tags, Remove Tags, Assign to Case, Delete. |

#### Search Results Mode (with `?q=` query param)

| Element              | Description |
|----------------------|-------------|
| Search results list  | `SearchResultsList` renders results as cards showing: file name, page number, relevance score, content snippet with highlighted terms, tags. |
| Result actions       | Clicking a result opens the Right Viewer Panel at the matched page with highlights. |

Search is initiated from the **Top Bar search bar**, which debounces input by 300ms and updates the URL query parameter. The `GalleryView` watches `route.query` and switches between document listing and search results accordingly.

#### Sidebar Filter Sections (Documents tab)

| Section              | Behavior |
|----------------------|----------|
| Active filter chips  | Colored pills for each active filter. Click to remove. |
| Status               | Collapsible (collapsed by default). Checkbox list: New, Parsing, Parsed, Failed. Single-select (click again to deselect). |
| File Type            | Collapsible (collapsed by default). Checkbox list: PDF, DOCX, XLSX, PPTX, JPEG, PNG, TXT. Single-select. |
| Document Type        | Dropdown: All, Generic. |
| Sort By              | Dropdown: Created Date, Modified Date, Name, Status. Plus ascending/descending dropdown. |
| Advanced Filters     | Collapsed by default. Contains: Tags (chip input), Date Range (date picker). |

All filter changes sync to URL query params via `router.replace()`, enabling bookmarkable filtered views.

#### Advanced Mode Additions

| Element                  | Description |
|--------------------------|-------------|
| Search mode selector     | Radio group: Fulltext / Vector / Hybrid. |
| Fulltext config panel    | `content_field` input, fuzzy toggle + `max_edits` (1-2) + `prefix_length` slider, `score_boost` number input. |
| Vector config panel      | Index selector (populated from `GET /api/v1/search/indices`), embedding model input, `num_candidates` slider, `score_boost` number input. |
| Hybrid config panel      | Combination method radio (RRF / Weighted Sum), `rrf_k` input, weight sliders for fulltext and vector (summing to 1.0). |
| Filters panel            | Document IDs input (comma-separated), status dropdown, document type dropdown -- in addition to the sidebar filters. |
| Result controls          | `top_k` input (default 10), `min_score` slider (0.0 – 1.0), `include_content_fields` multi-select. |
| Score breakdown          | Each result card shows individual fulltext and vector scores alongside the combined score. |

#### API Integration

- **Document listing**: `GET /api/v1/documents` with filter/sort/pagination params from the documents store.
- **Search**: `POST /api/v1/search` with `{ query, search_target: 'pages', search_mode: 'hybrid', filters, top_k: 20 }`.

### 3.3 Document Viewer (Right Panel)

The document viewer is embedded in a **resizable right-side panel** (`RightViewerPanel`) within the `AppShell`. Opening a document (via gallery click or navigating to `/doc/:id`) sets `viewerOpen = true` in the app store and renders the panel alongside the gallery.

#### Panel Layout

```
+------------------------------------------+
| Header: [doc name]    [Info] [Max] [Close]|
+------------------------------------------+
|                                          |
|          PDF Viewer (full height)         |
|          (canvas + text layer)            |
|                                          |
+------------------------------------------+
| Bottom toolbar:                          |
| [Prev] Page X/Y [Next]  | Result 2/8 [<>]|
+------------------------------------------+
```

| Section              | Description |
|----------------------|-------------|
| Resize handle        | 6px-wide draggable area on the left edge. Changes cursor to `col-resize`. Panel width clamped to 300px – 75% viewport. |
| Header               | Document file name (truncated) with Info toggle, Maximize, and Close buttons. |
| Document viewer      | `DocumentViewer` component rendering the PDF or image. Fills the full vertical space between header and bottom toolbar (`flex-1 min-h-0`). |
| Info panel           | Slide-over panel on the right side of the viewer, toggled by the Info button in the header. Contains metadata, tags, duplicates, and advanced sections. Absolutely positioned overlay, scrollable. |
| Bottom toolbar       | Always visible (`shrink-0`). Page navigation (Prev/Next + "Page N / Total") on the left. Search result navigation ("Result X of Y" + Prev/Next) on the right when opened from search. |

On tablet and mobile, the viewer opens as a **full-screen overlay** (fixed position, z-50) instead of an inline panel.

#### PDF Viewer

| Element             | Description |
|---------------------|-------------|
| Page canvas         | Renders the current PDF page via PDF.js onto a `<canvas>` element at high resolution. |
| Text layer          | Transparent text overlay on top of the canvas for text selection and highlight positioning. |
| Page navigation     | Previous / Next buttons, page number input, total page count. Keyboard: arrow keys. |
| Zoom controls       | Zoom in, zoom out, fit-to-width, fit-to-page. Pinch-to-zoom on touch devices. |
| Thumbnail sidebar   | Vertical strip of page thumbnails on the left (hideable on mobile). Active page is highlighted. Click to jump. |
| Highlight overlay   | When opened from a search result, the viewer scrolls to the matched page and highlights matching text. **MVP implementation** uses the pdf.js text layer: after rendering the text layer spans, the viewer walks them to find case-insensitive query matches and wraps them with `<mark>` elements styled with `--color-highlight`. Future versions may use element bounding boxes from `DocumentElement.element_data`. |
| Search result nav   | When opened from search, the bottom toolbar shows "Result X of Y" with Prev/Next buttons to cycle through search results across pages and documents. |
| Element annotations | On hover/click of a highlighted region, a tooltip shows the element type, short_id, and extracted text. |

#### Image Viewer

| Element           | Description |
|-------------------|-------------|
| Image display     | Renders the image scaled to fit the viewport. Supports zoom (scroll wheel / pinch) and pan (drag). |
| Highlight overlay | Bounding-box highlights over matched regions, same behavior as PDF highlights. |

#### Viewer Toolbar

| Button           | Action |
|------------------|--------|
| Download         | Downloads the original file. |
| Fullscreen       | Enters browser fullscreen mode. |
| Close            | Closes the viewer panel and navigates back to the gallery. |

### 3.4 Tags Management

Tags are free-form strings attached to documents.

#### Tag Input Component

A reusable component used in Upload, Sidebar Filters, Viewer Panel, Bulk Actions, and Search Filters.

| Behavior              | Description |
|-----------------------|-------------|
| Autocomplete          | As the user types, suggests existing tags fetched from the backend (derived from aggregation on `documents.tags`). |
| Create on Enter       | Pressing Enter or comma creates a new tag chip. |
| Remove on Backspace   | Backspace in an empty input removes the last chip. |
| Click to remove       | Each chip has an "x" button. |
| Validation            | Tags are lowercased, trimmed, max 50 characters, no commas. Duplicates are silently ignored. |

#### Tag Assignment Flows

1. **Single document** -- Viewer panel > Tags section > add/remove chips. Each change fires `POST /api/v1/documents/{id}/tags` or `DELETE /api/v1/documents/{id}/tags/{tag}`.
2. **Bulk** -- Select documents in the gallery > Bulk Actions bar > "Add Tags" or "Remove Tags" opens a modal with a tag input. Applies to all selected documents via sequential API calls (with a progress indicator).
3. **At upload** -- Tags entered in the Upload modal are passed to the ingest endpoint and applied to all ingested documents.

### 3.5 Cases View (`/cases`)

Cases group related documents for review or investigation.

#### Case Gallery

| Element             | Description |
|---------------------|-------------|
| Header              | "Cases" heading with a "New Case" button. |
| Case card grid      | Responsive grid (1 column on mobile, 2 on tablet, 3 on desktop) of `CaseCard` components showing case name, description preview, document count, and created date. Clicking navigates to `/cases/:id`. |
| Empty state         | Centered message: "No cases yet. Create your first case to start organizing documents." |

#### Create Case Dialog

A modal dialog (`CreateCaseDialog`) with:

| Field         | Type        | Description |
|---------------|-------------|-------------|
| Name          | Text input  | Required. Max 200 characters. |
| Description   | Textarea    | Optional. Markdown supported. |

#### Case Detail View (`/cases/:id`)

| Section             | Description |
|---------------------|-------------|
| Header              | Case name, created/modified dates, description. (`CaseHeader` component) |
| Document list       | Table of documents assigned to this case: name, type, status, tags, date added. Sortable and filterable. |
| Add documents       | `AddToCaseMenu` component for assigning documents to the case. |
| Remove document     | Per-row action to unassign a document from the case (does not delete the document). |
| Bulk actions        | Select multiple documents > Remove from Case, Add Tags. |

#### Extraction Results Tab

The Case Detail view includes an **Extraction Results** tab alongside the Documents tab.

| Element              | Description |
|----------------------|-------------|
| Tab button           | "Extraction Results" in the sub-navigation tabs. Clicking loads any existing results from the backend. |
| Extract button       | Primary action button ("Extract") in the tab toolbar. Triggers LLM extraction for each document in the case sequentially, sending `POST /api/v1/extract` per document. |
| Progress indicator   | Shown during extraction: spinner with "Extracting N/M: filename" message. |
| Results accordion    | Per-document collapsible sections. Each section header shows the document name and field count. Expanding reveals field results. |
| Field result card    | Shows field name (uppercase label), content value, and optional justification and citation sections. |
| Empty state          | "No extraction results yet. Click Extract to run extraction on case documents." |

**API Integration**:
- **Extract**: `POST /api/v1/extract` with `{ case_id, case_type, document_type: "generic", document_ids: [doc_id], content_mode: "markdown", reference_granularity: "none" }`
- **Load results**: `GET /api/v1/field-results?document_id=<id>` for each document in the case

#### Data Model

The `Case` model is defined in `mydocs/models.py:Case`. See [backend.md](backend.md) Section 3.9 for the full Case API contract (8 endpoints).

### 3.6 Settings (`/settings` -- drawer overlay)

Settings are presented as a **slide-in drawer** (`SettingsDrawer`) overlaying the gallery view. Navigating to `/settings` renders `GalleryView` with the drawer displayed.

| Section              | Description |
|----------------------|-------------|
| Theme                | Light / Dark / System toggle (uses Tailwind `dark:` variant). |
| Default search mode  | Dropdown: Hybrid / Fulltext / Vector. Applied when search is used in Simple mode. |
| Default top_k        | Number input (default 10). |
| Parser defaults      | Azure DI model selector, embedding model selector. Only shown in Advanced mode. |
| Connection info      | Displays backend URL, connection status indicator (green/red dot with latency via `GET /health`). |
| About                | App version, backend version. |

All settings are stored in `localStorage` via Pinia persisted state (in the `settings` store).

### 3.7 Keyboard Shortcuts

Global keyboard shortcuts registered via the `useKeyboardShortcuts` composable:

| Shortcut             | Action |
|----------------------|--------|
| `Cmd+K` / `Ctrl+K`  | Focus the search bar in the Top Bar. |
| `/`                  | Focus the search bar (when no input is focused). |
| `Escape`             | Close the document viewer panel if open. |

## 4. Component Architecture

### 4.1 Directory Structure

```
mydocs-ui/
  index.html
  vite.config.ts
  tsconfig.json
  package.json
  src/
    main.ts                          # App bootstrap (initializes MSAL before mount)
    App.vue                          # Root component, registers keyboard shortcuts
    auth/
      msalConfig.ts                  # MSAL configuration (reads VITE_ENTRA_* env vars)
      useAuth.ts                     # Auth composable: login, logout, getAccessToken
    router/
      index.ts                       # Route definitions with meta-driven modals + auth guard
    stores/
      app.ts                         # Global state (mode, theme, sidebar, viewer, activeTab, galleryViewMode)
      documents.ts                   # Document list state, filters, pagination
      search.ts                      # Search state, results
      cases.ts                       # Case list state
      tags.ts                        # Tag autocomplete cache
      settings.ts                    # User preferences (search defaults, parser defaults)
    api/
      client.ts                      # Axios instance, interceptors
      documents.ts                   # Document API calls
      search.ts                      # Search API calls
      cases.ts                       # Case API calls
      extract.ts                     # Extraction API calls
      health.ts                      # Health check with latency measurement
    views/
      LoginView.vue                  # Sign-in page (Microsoft Entra ID redirect)
      GalleryView.vue                # Primary view: document gallery + search results
      CasesGalleryView.vue           # Cases card grid with create dialog
      CaseDetailView.vue             # Single case detail with document list
      UploadView.vue                 # (legacy, redirects to /upload modal)
      DocumentsView.vue              # (legacy, redirects to /)
      DocumentDetailView.vue         # (legacy, redirects to /doc/:id)
      SearchView.vue                 # (legacy, redirects to /?q=)
      CasesView.vue                  # (legacy, redirects to /cases)
      SettingsView.vue               # (legacy, redirects to /settings drawer)
      DocumentViewerView.vue         # (legacy, redirects to /doc/:id)
    components/
      layout/
        AppShell.vue                 # Top bar + sidebar + content slot + right viewer panel
        TopBar.vue                   # Logo, search bar, upload/settings/mode/theme buttons
        SidebarNav.vue               # Tabs (Docs/Cases) + collapsible filter sections
        MobileTabBar.vue             # Bottom nav: Documents, Cases, More
        RightViewerPanel.vue         # Resizable document viewer side panel
        MobileFilterSheet.vue        # Mobile filter bottom sheet
      gallery/
        GalleryToolbar.vue           # Result count + grid/list view toggle
        DocumentGrid.vue             # Renders documents in grid or list layout
        SearchResultsList.vue        # Renders search result cards
        UploadModal.vue              # Upload modal overlay
        SettingsDrawer.vue           # Settings slide-in drawer overlay
      common/
        TagInput.vue                 # Reusable tag chip input with autocomplete
        StatusBadge.vue              # Colored status pills
        FileTypeBadge.vue
        ConfirmDialog.vue
        EmptyState.vue               # Illustration + message for empty lists
        LoadingSkeleton.vue
        PaginationBar.vue
        DateRangePicker.vue          # Uses @vuepic/vue-datepicker
        ModeToggle.vue               # Simple/Advanced toggle
      upload/
        DropZone.vue
        FileQueue.vue
        UploadProgress.vue
      documents/
        DocumentTable.vue
        DocumentCard.vue
        DocumentFilters.vue
        BulkActionsBar.vue
        ParseConfigForm.vue          # Advanced parse settings
      search/
        SearchBar.vue
        SearchFilters.vue
        SearchAdvancedPanel.vue
        SearchResultCard.vue
        ScoreBreakdown.vue           # Fulltext/vector/combined scores
      viewer/
        DocumentViewer.vue           # Orchestrates PDF or image viewer
        PdfViewer.vue                # PDF.js canvas + text layer
        ImageViewer.vue              # Zoomable image
        HighlightOverlay.vue         # Bounding box highlights
        ThumbnailSidebar.vue
        ViewerToolbar.vue
      cases/
        CaseCard.vue                 # Card for case grid display
        CaseHeader.vue               # Case detail header
        CreateCaseDialog.vue         # Create case modal form
        AddToCaseMenu.vue            # Assign documents to a case
    composables/
      useSearch.ts                   # Search logic, debouncing
      useDocumentViewer.ts           # PDF.js lifecycle, page navigation, file URL
      useHighlights.ts              # Compute highlight rects from elements
      useKeyboardShortcuts.ts        # Global keyboard shortcut handler
      useResponsive.ts               # Breakpoint-aware reactive state (4 breakpoints)
    types/
      index.ts                       # TypeScript interfaces mirroring backend models
    assets/
      logo.svg
      main.css
```

### 4.2 Key Composables

#### `useSearch()`

```typescript
interface UseSearch {
  query: Ref<string>
  config: Ref<SearchRequest>     // Full config; simple mode populates defaults
  results: Ref<SearchResponse>
  loading: Ref<boolean>
  error: Ref<string | null>
  execute(): Promise<void>       // Fires the search API call
  reset(): void
}
```

#### `useDocumentViewer(documentId, initialPage?)`

Accepts either a string or a `Ref<string | null>` for `documentId`. When a ref is passed, the composable watches for changes and reloads automatically.

```typescript
interface UseDocumentViewer {
  document: Ref<Document | null>
  pages: Ref<DocumentPage[]>
  currentPage: Ref<number>
  totalPages: Ref<number>
  zoom: Ref<number>
  loading: Ref<boolean>
  pdfDoc: Ref<any>               // Raw PDF.js document object
  fileUrl: Ref<string>           // URL to the original file for rendering
  goToPage(n: number): void
  nextPage(): void
  prevPage(): void
  setZoom(level: number): void
  fitToWidth(): void
  fitToPage(): void
}
```

#### `useHighlights(elements, pageNumber, searchContent?)`

```typescript
interface UseHighlights {
  highlights: Computed<HighlightRect[]>  // Array of { x, y, width, height, text, elementId, elementType }
  activeHighlight: Ref<HighlightRect | null>
  scrollToFirstHighlight(): void
}
```

Computes highlight rectangles by:
1. Taking the search result's matched content.
2. Finding `DocumentElement` entries on the current page whose text overlaps with the matched content.
3. Extracting bounding region polygons from `element_data`.
4. Converting polygon coordinates to page-relative rectangles scaled to the current zoom level.

#### `useKeyboardShortcuts()`

Registers global `keydown` listeners for `Cmd+K`, `/`, and `Escape`. Automatically cleans up on component unmount.

#### `useResponsive()`

```typescript
interface UseResponsive {
  isMobile: Ref<boolean>   // < 768px
  isTablet: Ref<boolean>   // 768–1023px
  isDesktop: Ref<boolean>  // 1024–1279px
  isWide: Ref<boolean>     // >= 1280px
}
```

Uses `matchMedia` listeners for efficient breakpoint tracking.

## 5. Routing

```typescript
const routes = [
  // Public routes
  { path: '/login',     name: 'login',       component: LoginView,          meta: { public: true } },

  // Authenticated routes
  { path: '/',          name: 'gallery',     component: GalleryView,        meta: { tab: 'documents' } },
  { path: '/doc/:id',   name: 'doc-viewer',  component: GalleryView,        meta: { tab: 'documents' } },
  { path: '/cases',     name: 'cases',       component: CasesGalleryView,   meta: { tab: 'cases' } },
  { path: '/cases/:id', name: 'case-detail', component: CaseDetailView,     meta: { tab: 'cases' } },
  { path: '/upload',    name: 'upload',      component: GalleryView,        meta: { tab: 'documents', modal: 'upload' } },
  { path: '/settings',  name: 'settings',    component: GalleryView,        meta: { tab: 'documents', modal: 'settings' } },

  // Legacy redirects (backward compatibility)
  { path: '/documents',          redirect: '/' },
  { path: '/documents/:id',      redirect: to => `/doc/${to.params.id}` },
  { path: '/documents/:id/view', redirect: to => `/doc/${to.params.id}` },
  { path: '/search',             redirect: to => ({ path: '/', query: to.query }) },
]
```

All routes are lazy-loaded for optimal bundle splitting.

**Route guard behavior:**
- **Auth guard**: If the route does not have `meta.public: true` and the user is not authenticated, redirect to `/login` with a `?redirect=` query param. If the user is authenticated and visits `/login`, redirect to `/`.
- `beforeEach` syncs `activeTab` from `route.meta.tab`.
- For `/doc/:id` routes, the guard calls `appStore.openViewer(id, page)` to open the right panel.
- Navigating away from `/doc/` routes closes the viewer.

## 6. API Client

```typescript
// api/client.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach Bearer token to every request
api.interceptors.request.use(async (config) => {
  const { getAccessToken, isAuthenticated } = useAuth()
  if (isAuthenticated.value) {
    const token = await getAccessToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired or invalid — redirect to login
      useAuth().logout()
      return Promise.reject(error)
    }
    const detail = error.response?.data?.detail || 'An unexpected error occurred'
    toast.error(detail)
    return Promise.reject(error)
  }
)
```

The request interceptor acquires a fresh token silently via MSAL on each request. If the cached token is expired and a silent refresh fails, MSAL triggers an interactive redirect to Entra ID automatically.

Additional API module:

```typescript
// api/health.ts
export async function checkHealth(): Promise<{ status: string; latencyMs: number }>
```

## 7. Visual Design Guidelines

### 7.1 Color Palette

| Token             | Light Mode     | Dark Mode      | Usage |
|-------------------|----------------|----------------|-------|
| `--bg-primary`    | `#FFFFFF`      | `#0F172A`      | Page background |
| `--bg-secondary`  | `#F8FAFC`      | `#1E293B`      | Cards, sidebar |
| `--bg-tertiary`   | `#F1F5F9`      | `#334155`      | Hover states, inputs |
| `--text-primary`  | `#0F172A`      | `#F1F5F9`      | Body text |
| `--text-secondary`| `#64748B`      | `#94A3B8`      | Labels, captions |
| `--accent`        | `#2563EB`      | `#3B82F6`      | Primary buttons, links, active nav |
| `--accent-hover`  | `#1D4ED8`      | `#60A5FA`      | Button hover |
| `--success`       | `#16A34A`      | `#22C55E`      | Parsed status, success toasts |
| `--warning`       | `#D97706`      | `#F59E0B`      | Parsing status |
| `--danger`        | `#DC2626`      | `#EF4444`      | Failed status, delete actions |
| `--highlight`     | `#FBBF24` / 40% opacity | `#FBBF24` / 30% opacity | Search result highlights |

### 7.2 Typography

| Element     | Font              | Size   | Weight |
|-------------|-------------------|--------|--------|
| Body        | Inter             | 14px   | 400    |
| Headings    | Inter             | 18–28px| 600    |
| Monospace   | JetBrains Mono    | 13px   | 400    |
| Labels      | Inter             | 12px   | 500    |

### 7.3 Spacing & Sizing

- Base unit: 4px (Tailwind default).
- Card padding: 16px (desktop), 12px (mobile).
- Card border-radius: 8px.
- Button height: 36px (default), 32px (compact), 40px (large).
- Sidebar width: 240px expanded, 64px collapsed (icon rail).
- Top bar height: defined by `--height-topbar` CSS variable.
- Right viewer panel: 420px default, 300px – 75% viewport resize range.

### 7.4 Shadows & Borders

- Cards: `shadow-sm` with `border border-gray-200 dark:border-gray-700`.
- Modals: `shadow-xl` with backdrop overlay (`bg-black/50`).
- Dropdowns: `shadow-lg` with `ring-1 ring-gray-200`.

## 8. Error Handling & Loading States

| Scenario              | Behavior |
|-----------------------|----------|
| API error             | Toast notification with the `detail` message from the error response. |
| Network error         | Full-width banner at the top: "Unable to connect to the server. Check your connection." with retry button. |
| Empty state           | Centered illustration + message + CTA button (e.g., "No documents yet. Upload your first file."). |
| Loading               | Skeleton placeholders matching the layout shape of the content being loaded. |
| File upload failure   | Inline error on the specific file row with a retry button. |
| Long operations       | Indeterminate progress bar in the top bar for global operations (batch parse). |

## 9. Accessibility

- All interactive elements are keyboard-navigable with visible focus rings.
- ARIA labels on icon-only buttons (sidebar toggle, theme toggle, settings, close, maximize).
- Color contrast ratios meet WCAG 2.1 AA (4.5:1 for text, 3:1 for UI components).
- Screen-reader announcements for toast notifications via `aria-live="polite"`.
- Drop zone is activatable via keyboard (Enter/Space).

## 10. Performance Considerations

- **Code splitting** -- every route is lazy-loaded.
- **Virtual scrolling** -- document and search result lists use virtual scrolling for lists exceeding 100 items.
- **Debounced search** -- 300ms debounce on search input in the Top Bar to avoid excessive API calls.
- **PDF page caching** -- PDF.js renders only the visible page and one page ahead/behind; decoded pages are cached in memory (LRU, max 10 pages).
- **Image thumbnails** -- document grid view uses server-generated thumbnails (future backend endpoint) with lazy loading via `IntersectionObserver`.
- **Bundle size** -- PDF.js worker loaded as a separate chunk; Tailwind purges unused styles in production.
- **URL-driven state** -- filters and search queries are synced to URL params, avoiding unnecessary store hydration on navigation.

## 11. Authentication

### 11.1 Overview

The UI uses **Microsoft Entra ID** (Azure AD) for authentication via the `@azure/msal-browser` library. The flow is redirect-based (no pop-ups) and initializes before the Vue app mounts.

### 11.2 Bootstrap Sequence

1. `main.ts` calls `useAuth().initialize()` **before** `createApp()`.
2. `initialize()` calls `msalInstance.handleRedirectPromise()` to complete any in-flight redirect.
3. If an account is found (from redirect or cache), it is set as the active account.
4. The Vue app mounts, and the router auth guard determines whether to show the app or redirect to `/login`.

### 11.3 Auth Composable (`useAuth`)

```typescript
interface UseAuth {
  isInitialized: Ref<boolean>
  isAuthenticated: ComputedRef<boolean>
  account: Ref<AccountInfo | null>
  userName: ComputedRef<string>
  initialize(): Promise<void>
  login(): Promise<void>          // Triggers MSAL redirect to Entra ID
  logout(): Promise<void>         // Triggers MSAL redirect to post-logout URI
  getAccessToken(): Promise<string>  // Silent token acquisition, falls back to redirect
}
```

The composable uses module-level singletons for the MSAL instance and reactive state, so all components share the same auth state regardless of where `useAuth()` is called.

### 11.4 Login View (`/login`)

A centered card with the app logo, a brief message, and a "Sign in with Microsoft" button. Clicking the button calls `useAuth().login()`, which triggers the MSAL redirect flow to Entra ID. After successful login, the user is redirected back to the app and the router guard sends them to the originally requested page (via the `?redirect=` query param).

### 11.5 TopBar Integration

The `TopBar` component displays the authenticated user's name (from the Entra ID token claims) and a logout button (LogOut icon) on the right side of the header bar.

### 11.6 Configuration

| Variable | Provided via | Description |
|----------|-------------|-------------|
| `VITE_ENTRA_CLIENT_ID` | Vite env / Docker build arg | Entra ID app registration client ID |
| `VITE_ENTRA_AUTHORITY` | Vite env / Docker build arg | Authority URL, e.g. `https://login.microsoftonline.com/<tenant-id>` |

When `VITE_ENTRA_CLIENT_ID` is empty, the MSAL instance is created with an empty client ID. In practice this means the redirect login will fail, but the router guard still enforces the login page. For local development, the backend should have `ENTRA_TENANT_ID` unset so API calls succeed without tokens.

---

## 12. Future Considerations

- **Case timeline / activity log** -- a timeline of actions taken on a case (document added, status changed, etc.).
- **DocumentElement collapsible list** -- browsable list of parsed elements grouped by page in the viewer panel.
- **Raw JSON toggle** -- button in the viewer panel (advanced mode) to view raw document/page JSON from the API.
- **Real-time updates** -- WebSocket or SSE for parse-status changes and batch progress.
- **Collaborative annotations** -- multiple users highlighting and commenting on document pages.
- **Saved searches** -- persist search configurations as named presets.
- **Export** -- export search results or case document lists as CSV/PDF reports.
- **Drag-and-drop case assignment** -- drag documents from the gallery directly onto a case in the sidebar.
- **Offline support** -- service worker caching for recently viewed documents.
- **Duplicate detection** -- surface duplicate documents in the viewer panel (UI placeholder exists).
