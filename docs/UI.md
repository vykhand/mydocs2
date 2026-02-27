# UI — Actual State Documentation

| Field   | Value                |
|---------|----------------------|
| Package | `mydocs-ui`          |
| Version | 1.0.0                |
| Spec    | `docs/specs/UI.md` v2.0 |
| Date    | 2026-02-24           |

> This document captures the **actual implemented state** of the UI codebase, compared against the specification in `docs/specs/UI.md`. Deviations from the spec are marked with **[DEVIATION]**. Missing features are marked with **[NOT IMPLEMENTED]**.

---

## 1. Technology Stack

| Layer          | Spec                          | Actual                        | Status |
|----------------|-------------------------------|-------------------------------|--------|
| Framework      | Vue 3 (Composition API, `<script setup>`) | Vue 3.5.13 (Composition API, `<script setup>`) | Match |
| Build          | Vite                          | Vite 6.0.0                    | Match |
| Styling        | Tailwind CSS 4                | Tailwind CSS 4.0.0 (via `@tailwindcss/vite`) | Match |
| State          | Pinia + `pinia-plugin-persistedstate` | Pinia 2.3.0 + `pinia-plugin-persistedstate` 3.2.0 | Match |
| HTTP           | Axios                         | Axios 1.7.9                   | Match |
| Routing        | Vue Router 4                  | Vue Router 4.5.0              | Match |
| Icons          | Lucide Vue Next               | lucide-vue-next 0.469.0       | Match |
| PDF Viewer     | PDF.js (`pdfjs-dist`)         | pdfjs-dist 4.9.155            | Match |
| Date Picker    | `@vuepic/vue-datepicker`      | @vuepic/vue-datepicker 12.1.0 | Match |
| Notifications  | Vue Toastification            | vue-toastification 2.0.0-rc.5 | Match |
| Auth           | `@azure/msal-browser`         | @azure/msal-browser 4.8.0     | Match |

**Stack verdict: Fully aligned with spec.**

---

## 2. Directory Structure

### 2.1 Spec vs Actual File Inventory

The directory structure broadly matches the spec. Below are deviations:

#### Files present in spec but functioning differently in code

| File (spec) | Spec Says | Actual | Deviation |
|---|---|---|---|
| `views/UploadView.vue` | "(legacy, redirects to /upload modal)" | Full standalone upload page with drop zone, file queue, progress, storage mode, parse-after-upload, server-path ingestion | **[DEVIATION]** Not a redirect; full legacy page exists but is unused by the router |
| `views/DocumentsView.vue` | "(legacy, redirects to /)" | Full standalone documents list page with table, filters, pagination, bulk actions | **[DEVIATION]** Not a redirect; full legacy page exists but is unused by the router |
| `views/DocumentDetailView.vue` | "(legacy, redirects to /doc/:id)" | Full standalone document detail page with metadata, pages, elements, tags, parse config, JSON viewer | **[DEVIATION]** Not a redirect; full legacy page exists but is unused by the router |
| `views/SearchView.vue` | "(legacy, redirects to /?q=)" | Full standalone search page with bar, filters, advanced panel, results | **[DEVIATION]** Not a redirect; full legacy page exists but is unused by the router |
| `views/CasesView.vue` | "(legacy, redirects to /cases)" | "Coming Soon" placeholder with EmptyState | **[DEVIATION]** Not a redirect; shows placeholder message |
| `views/SettingsView.vue` | "(legacy, redirects to /settings drawer)" | Full standalone settings page with theme, search defaults, parser defaults, connection info, about | **[DEVIATION]** Not a redirect; full legacy page exists but is unused by the router |
| `views/DocumentViewerView.vue` | "(legacy, redirects to /doc/:id)" | Full standalone document viewer page with toolbar, PDF viewer, page navigation | **[DEVIATION]** Not a redirect; full legacy page exists but is unused by the router |

> **Impact:** The seven legacy views are dead code — they exist as full implementations but the router never loads them. They represent the pre-gallery-architecture UI and should either be deleted or converted to actual redirects per the spec.

#### File count comparison

| Directory | Spec | Actual | Match |
|---|---|---|---|
| `views/` | 11 files (2 active + 9 legacy) | 11 files | Match |
| `components/layout/` | 6 files | 6 files | Match |
| `components/gallery/` | 5 files | 5 files | Match |
| `components/common/` | 9 files | 9 files | Match |
| `components/upload/` | 3 files | 3 files | Match |
| `components/documents/` | 5 files | 5 files | Match |
| `components/search/` | 5 files | 5 files | Match |
| `components/viewer/` | 6 files | 6 files | Match |
| `components/cases/` | 4 files | 4 files | Match |
| `stores/` | 6 files | 6 files | Match |
| `composables/` | 5 files | 5 files | Match |
| `api/` | 6 files | 6 files | Match |
| `auth/` | 2 files | 2 files | Match |
| `router/` | 1 file | 1 file | Match |
| `types/` | 1 file | 1 file | Match |

---

## 3. Routing

### 3.1 Active Routes

| Path | Name | Component | Meta | Matches Spec |
|------|------|-----------|------|------|
| `/login` | login | LoginView | `{ public: true }` | Match |
| `/` | gallery | GalleryView | `{ tab: 'documents' }` | Match |
| `/doc/:id` | doc-viewer | GalleryView | `{ tab: 'documents' }` | Match |
| `/cases` | cases | CasesGalleryView | `{ tab: 'cases' }` | Match |
| `/cases/:id` | case-detail | CaseDetailView | `{ tab: 'cases' }` | Match |
| `/upload` | upload | GalleryView | `{ tab: 'documents', modal: 'upload' }` | Match |
| `/settings` | settings | GalleryView | `{ tab: 'documents', modal: 'settings' }` | Match |

### 3.2 Legacy Redirects

| Pattern | Target | Matches Spec |
|---------|--------|------|
| `/documents` | `/` | Match |
| `/documents/:id` | `/doc/:id` | Match |
| `/documents/:id/view` | `/doc/:id` | Match |
| `/search` | `/ (preserves query)` | Match |

### 3.3 Route Guard Behavior

- Auth guard redirects unauthenticated users to `/login` with `?redirect=` — **matches spec**
- Authenticated users visiting `/login` are redirected to `/` — **matches spec**
- `beforeEach` syncs `activeTab` from `route.meta.tab` — **matches spec**
- `/doc/:id` routes call `appStore.openViewer(id, page)` — **matches spec**
- Navigating away from `/doc/` routes closes the viewer — **matches spec**

**Routing verdict: Fully aligned with spec.**

---

## 4. Layout & Navigation

### 4.1 Shell Layout (AppShell)

Implemented as specified:
- Top Bar: fixed, with sidebar toggle, logo, search bar, action buttons
- Sidebar: collapsible, with Documents/Cases tabs and filter sections
- Main Content Area: scrollable, renders active route
- Right Viewer Panel: resizable side panel for document viewer
- Mobile Tab Bar: bottom navigation with Documents, Cases, More

### 4.2 Responsive Breakpoints

| Breakpoint | Spec | Actual | Match |
|---|---|---|---|
| `sm` (< 768px) | Hidden sidebar; bottom tab-bar; full-screen viewer overlay | Implemented | Match |
| `md` (768–1023px) | Drawer overlay on toggle; full-screen viewer overlay | Implemented | Match |
| `lg` (1024–1279px) | Icon rail (collapsible); inline side panel | Implemented | Match |
| `xl` (>= 1280px) | Expanded (icons + labels); inline side panel | Implemented | Match |

### 4.3 Simple / Advanced Mode

Global toggle in Pinia, persisted to `localStorage` — **matches spec**.

---

## 5. Views & Features — Detailed Comparison

### 5.1 Upload (`/upload` — modal overlay)

The `/upload` route renders GalleryView with `UploadModal` overlay — **matches spec architecture**.

| Element | Spec | Actual in UploadModal | Status |
|---|---|---|---|
| Drop zone | Drag-and-drop + clickable | DropZone component with drag-drop and click-to-select | Match |
| Folder picker button | Separate directory picker (`webkitdirectory`) | Present in DropZone | Match |
| File list | Table showing queued files with remove button | FileQueue component with file list and remove buttons | Match |
| Tags input | Chip/tag input for batch tags | TagInput component present | Match |
| Upload button | Starts ingestion, disabled when queue empty | Present, disables when queue empty | Match |
| Progress section | Per-file + overall progress bars with status | UploadProgress conditionally rendered | Match |
| **Advanced: Storage mode select** | Dropdown: managed/external | **Hardcoded to `managed`; no selector in modal** | **[NOT IMPLEMENTED]** |
| **Advanced: Recursive toggle** | Checkbox, default on | **Not present in modal** | **[NOT IMPLEMENTED]** |
| **Parse-after-upload toggle** | Optional toggle | **Not present in modal** | **[NOT IMPLEMENTED]** |
| **Server path ingestion** | Mentioned in API integration | **Not in modal (exists in legacy UploadView only)** | **[NOT IMPLEMENTED]** |

> **Note:** The legacy `UploadView.vue` has all these features (storage mode, recursive, parse-after-upload, server path). The `UploadModal.vue` that is actually used via routing is a simpler version.

### 5.2 Gallery View (`/` — main entry point)

| Element | Spec | Actual | Status |
|---|---|---|---|
| Unified gallery: no `?q=` shows documents, with `?q=` shows search | Dual mode based on URL | Implemented: syncs URL params, switches between DocumentGrid and SearchResultsList | Match |
| Gallery Toolbar: result count + view toggle | Required | GalleryToolbar with count and grid/list toggle | Match |
| Document grid/list | DocumentGrid renders cards (grid) or rows (list) | DocumentGrid switches between card grid and DocumentTable list view | Match |
| Sidebar filters | Collapsible status, file type, doc type, sort, advanced (tags, date range) | SidebarNav with all filter sections | Match |
| Active filter chips | Colored pills, click to remove | Implemented in SidebarNav | Match |
| Pagination | Page size selector (25, 50, 100) + page navigation | PaginationBar component | Match |
| Bulk actions bar | Appears on selection: Parse, Add Tags, Remove Tags, Assign to Case, Delete | BulkActionsBar with parse, tag, delete, add-to-case | Match |
| Search results list | Cards with file name, page number, score, snippet, highlights | SearchResultsList + SearchResultCard | Match |
| Search debounce | 300ms in Top Bar | Debounced search input in TopBar | Match |
| Filter sync to URL | `router.replace()` for bookmarkable views | Implemented via URL query param sync | Match |
| **Filter sections collapsed by default** | Status, File Type start collapsed | **Need to verify default collapsed state** | Likely Match |

#### Advanced Mode Additions

| Element | Spec | Actual | Status |
|---|---|---|---|
| Search mode selector | Radio: Fulltext / Vector / Hybrid | SearchAdvancedPanel has mode selector | Match |
| Fulltext config | content_field, fuzzy toggle, max_edits, prefix_length, score_boost | SearchAdvancedPanel has fulltext config | Match |
| Vector config | Index selector, embedding model, num_candidates, score_boost | SearchAdvancedPanel fetches indices, has vector config | Match |
| Hybrid config | Combination method, rrf_k, weight sliders | SearchAdvancedPanel has hybrid config | Match |
| Result controls | top_k, min_score, include_content_fields | top_k and min_score present | Match |
| Score breakdown | Per-result fulltext + vector + combined scores | ScoreBreakdown component | Match |

### 5.3 Document Viewer (Right Panel)

| Element | Spec | Actual | Status |
|---|---|---|---|
| Resizable side panel | 300px – 75% viewport, default 420px | RightViewerPanel with mouse-drag resize | Match |
| Panel header | Doc name + Info, Maximize, Close buttons | Header with doc name, info toggle, close | Match |
| PDF Viewer (full height) | Canvas + text layer fills between header and toolbar | PdfViewer with canvas rendering + text layer | Match |
| Info panel slide-over | Toggled by info button; metadata, tags, duplicates, advanced | Slide-over panel with metadata, tags, duplicates (static "none detected"), advanced (ID, parser) | Match |
| Bottom toolbar | Page nav (Prev/Next + "Page N/Total") + search result nav ("Result X of Y") | Implemented with both page nav and search result navigation | Match |
| Tablet/mobile: full-screen overlay | Fixed position, z-50 | Responsive behavior implemented | Match |

#### PDF Viewer Details

| Element | Spec | Actual | Status |
|---|---|---|---|
| Page canvas | High-res PDF.js canvas | Canvas rendering with devicePixelRatio scaling | Match |
| Text layer | Transparent overlay for selection + highlight | PDF.js TextLayer API used | Match |
| Page navigation | Prev/Next, page input, total count, arrow keys | Implemented | Match |
| Zoom controls | Zoom in/out, fit-to-width, fit-to-page | ViewerToolbar has zoom controls | Match |
| **Pinch-to-zoom** | On touch devices | **Not implemented** | **[NOT IMPLEMENTED]** |
| **Thumbnail sidebar** | Vertical strip of page thumbnails, click to jump | **Page number buttons only — no actual rendered thumbnails** | **[DEVIATION]** Renders numbers, not thumbnail images |
| Highlight overlay | Mark elements on text layer spans for query matches | Implemented: `applyHighlights()` walks text spans, wraps matches in `<mark>` elements | Match |
| Search result nav | "Result X of Y" with Prev/Next across pages/documents | Implemented in bottom toolbar | Match |
| **Element annotations** | Tooltip on hover/click showing element type, short_id, text | **Not implemented** | **[NOT IMPLEMENTED]** |

#### Image Viewer Details

| Element | Spec | Actual | Status |
|---|---|---|---|
| Image display | Scaled to fit, zoom (scroll/pinch), pan (drag) | ImageViewer with zoom support | Match |
| **Highlight overlay** | Bounding-box highlights over matched regions | **Not implemented for images** | **[NOT IMPLEMENTED]** |

#### Viewer Toolbar

| Button | Spec | Actual | Status |
|---|---|---|---|
| Download | Downloads original file | Present in ViewerToolbar | Match |
| Fullscreen | Browser fullscreen mode | Present in ViewerToolbar | Match |
| Close | Closes viewer panel | Present in ViewerToolbar | Match |

### 5.4 Tags Management

| Behavior | Spec | Actual | Status |
|---|---|---|---|
| Autocomplete | Suggests existing tags from backend | TagInput uses `useTagsStore` for suggestions | Match |
| Create on Enter/comma | Enter or comma creates chip | Implemented | Match |
| Remove on Backspace | Backspace in empty input removes last chip | Implemented | Match |
| Click to remove | "x" button on each chip | Implemented | Match |
| Validation | Lowercase, trimmed, max 50 chars, no commas, dedup | **Need to verify all validation rules** | Likely Match |
| Single document tags | Viewer panel add/remove | RightViewerPanel info panel shows tags as badges | **[DEVIATION]** Tags displayed as read-only badges, not editable TagInput |
| Bulk tag | Select docs > Bulk Actions > Add/Remove Tags | BulkActionsBar has tag modal | Match |
| At upload | Tags in upload form | TagInput in UploadModal | Match |

### 5.5 Cases View (`/cases`)

| Element | Spec | Actual | Status |
|---|---|---|---|
| Case card grid | Responsive grid with CaseCard components | CasesGalleryView renders case card grid | Match |
| "New Case" button | In header | Present | Match |
| Create Case Dialog | Modal with name + description | CreateCaseDialog with name and description inputs | Match |
| Empty state | Message + CTA | EmptyState component | Match |

#### Case Detail View (`/cases/:id`)

| Element | Spec | Actual | Status |
|---|---|---|---|
| Case header | Name, dates, description | CaseHeader with inline edit, back button, delete | Match |
| Document list | Table of assigned documents | Document list in CaseDetailView | Match |
| Add documents | AddToCaseMenu component | Dropdown to add documents to case | Match |
| Remove document | Per-row action to unassign | Implemented | Match |
| Extraction Results tab | Tab with extract button, progress, results accordion, field result cards | Implemented with sequential extraction, per-document results | Match |

### 5.6 Settings (`/settings` — drawer overlay)

**[DEVIATION]** The `SettingsDrawer` that is actually used via routing is significantly simpler than specified.

| Section | Spec | Actual in SettingsDrawer | Status |
|---|---|---|---|
| Theme | Light / Dark / System toggle | Implemented | Match |
| **Default search mode** | Dropdown: Hybrid / Fulltext / Vector | **Not present** | **[NOT IMPLEMENTED]** |
| **Default top_k** | Number input (default 10) | **Not present** | **[NOT IMPLEMENTED]** |
| **Parser defaults** | Azure DI model, embedding model (Advanced mode) | **Not present** | **[NOT IMPLEMENTED]** |
| **Connection info** | Backend URL, status indicator, latency | **Not present** | **[NOT IMPLEMENTED]** |
| About | App version, backend version | Simple about section present | Match |

> **Note:** The legacy `SettingsView.vue` has all these features (search defaults, parser defaults, connection info with health check). The `SettingsDrawer.vue` only exposes theme, mode toggle, and about.

### 5.7 Keyboard Shortcuts

| Shortcut | Spec | Actual | Status |
|---|---|---|---|
| `Cmd+K` / `Ctrl+K` | Focus search bar | Implemented in `useKeyboardShortcuts` | Match |
| `/` | Focus search bar (no input focused) | Implemented with `isInputFocused()` guard | Match |
| `Escape` | Close viewer panel | Implemented | Match |

---

## 6. Stores

### 6.1 App Store (`stores/app.ts`)

| State | Spec | Actual | Match |
|---|---|---|---|
| mode | `'simple' \| 'advanced'` | `AppMode = 'simple' \| 'advanced'` | Match |
| theme | `'light' \| 'dark' \| 'system'` | `ThemeMode = 'light' \| 'dark' \| 'system'` | Match |
| sidebarCollapsed | boolean | boolean | Match |
| viewerOpen | boolean | boolean | Match |
| viewerDocumentId | `string \| null` | `string \| null` | Match |
| viewerPage | number | number | Match |
| activeTab | `'documents' \| 'cases'` | `ActiveTab` type | Match |
| galleryViewMode | `'grid' \| 'list'` | `GalleryViewMode` type | Match |
| viewerHighlightQuery | string | string | Match |
| viewerSearchResults | SearchResult[] | SearchResult[] | Match |
| viewerCurrentResultIndex | number | number | Match |

Persistence: `['mode', 'theme', 'sidebarCollapsed', 'activeTab', 'galleryViewMode']` — covers all spec requirements.

### 6.2 Documents Store (`stores/documents.ts`)

| State | Type | Match |
|---|---|---|
| documents | Document[] | Match |
| total | number | Match |
| loading | boolean | Match |
| selectedIds | Set\<string\> | Match |
| filters | DocumentListParams (page, page_size, status, file_type, document_type, tags, sort_by, sort_order, search, date_from, date_to) | Match |

### 6.3 Search Store (`stores/search.ts`)

| State | Type | Match |
|---|---|---|
| query | string | Match |
| searchTarget | SearchTarget | Match |
| searchMode | SearchMode | Match |
| loading | boolean | Match |
| response | SearchResponse \| null | Match |
| config | Partial\<SearchRequest\> | Match |

### 6.4 Cases Store (`stores/cases.ts`)

| State | Type | Match |
|---|---|---|
| cases | Case[] | Match |
| currentCase | Case \| null | Match |
| total | number | Match |
| loading | boolean | Match |

### 6.5 Tags Store (`stores/tags.ts`)

| State | Type | Match |
|---|---|---|
| allTags | string[] | Match |

### 6.6 Settings Store (`stores/settings.ts`)

| State | Default | Match |
|---|---|---|
| defaultSearchMode | `'hybrid'` | Match |
| defaultTopK | 10 | Match |
| defaultParserModel | `'prebuilt-layout'` | Match |
| defaultEmbeddingModel | `'azure/text-embedding-3-large'` | Match |

Persisted with `persist: true` — **matches spec**.

---

## 7. Composables

### 7.1 `useSearch()`

| Member | Spec | Actual | Match |
|---|---|---|---|
| query | `Ref<string>` | `Ref<string>` | Match |
| config | `Ref<SearchRequest>` | `Ref<SearchRequest>` | Match |
| results | `Ref<SearchResponse>` | `Ref<SearchResponse \| null>` | Match (null-safe) |
| loading | `Ref<boolean>` | `Ref<boolean>` | Match |
| error | `Ref<string \| null>` | `Ref<string \| null>` | Match |
| execute() | `Promise<void>` | `Promise<void>` | Match |
| reset() | void | void | Match |

### 7.2 `useDocumentViewer(documentId, initialPage?)`

| Member | Spec | Actual | Match |
|---|---|---|---|
| document | `Ref<Document \| null>` | `Ref<Document \| null>` | Match |
| pages | `Ref<DocumentPage[]>` | `Ref<DocumentPage[]>` | Match |
| currentPage | `Ref<number>` | `Ref<number>` | Match |
| totalPages | `Ref<number>` | `Ref<number>` | Match |
| zoom | `Ref<number>` | `Ref<number>` | Match |
| loading | `Ref<boolean>` | `Ref<boolean>` | Match |
| pdfDoc | `Ref<any>` | `Ref<any>` | Match |
| fileUrl | `Ref<string>` | `Ref<string>` | Match |
| goToPage(n) | void | void | Match |
| nextPage() | void | void | Match |
| prevPage() | void | void | Match |
| setZoom(level) | void | void | Match |
| fitToWidth() | void | void | Match |
| fitToPage() | void | void | Match |

Accepts both string and `Ref<string | null>` for documentId — **matches spec**.

### 7.3 `useHighlights(elements, pageNumber, searchContent?)`

| Member | Spec | Actual | Match |
|---|---|---|---|
| highlights | `Computed<HighlightRect[]>` | `ComputedRef<HighlightRect[]>` | Match |
| activeHighlight | `Ref<HighlightRect \| null>` | `Ref<HighlightRect \| null>` | Match |
| scrollToFirstHighlight() | void | void | Match |

### 7.4 `useKeyboardShortcuts()`

Registers `Cmd+K`, `/`, `Escape` — **matches spec exactly**.

### 7.5 `useResponsive()`

| Member | Breakpoint | Spec | Actual | Match |
|---|---|---|---|---|
| isMobile | < 768px | Yes | Yes | Match |
| isTablet | 768–1023px | Yes | Yes | Match |
| isDesktop | 1024–1279px | Yes | Yes | Match |
| isWide | >= 1280px | Yes | Yes | Match |

---

## 8. API Client

| Feature | Spec | Actual | Match |
|---|---|---|---|
| baseURL | `/api/v1` | `/api/v1` | Match |
| timeout | 30_000 | 30_000 | Match |
| Content-Type | application/json | application/json | Match |
| Auth interceptor | Attach Bearer token | Implemented | Match |
| 401 response | Redirect to login via `logout()` | Implemented | Match |
| Error toast | Show `detail` from response | Implemented | Match |
| health.ts | `checkHealth()` returns status + latencyMs | Implemented (uses raw axios, 5s timeout) | Match |

### API Modules

| Module | Functions | Matches Spec |
|---|---|---|
| documents.ts | listDocuments, getDocument, uploadAndIngest, ingestFromPath, batchParse, parseSingle, getPages, getPage, addTags, removeTag, deleteDocument, getDocumentFileUrl | Match |
| search.ts | search, getIndices | Match |
| cases.ts | listCases, getCase, createCase, updateCase, deleteCase, addDocumentsToCase, removeDocumentFromCase, getCaseDocuments (8 functions) | Match |
| extract.ts | extractFields, getFieldResults | Match |
| health.ts | checkHealth | Match |

---

## 9. Authentication

| Feature | Spec | Actual | Match |
|---|---|---|---|
| MSAL redirect flow | Yes | Yes | Match |
| Initialize before mount | `main.ts` calls `initialize()` before `createApp()` | Implemented | Match |
| `handleRedirectPromise()` | In initialize | Implemented | Match |
| Module-level singletons | Shared MSAL instance | Implemented | Match |
| Login scopes | `api://{clientId}/access_as_user` | Implemented | Match |
| Cache location | localStorage | localStorage | Match |
| Env vars | VITE_ENTRA_CLIENT_ID, VITE_ENTRA_AUTHORITY | Implemented in env.d.ts | Match |
| TopBar integration | User name + logout button | Implemented | Match |
| Login View | Centered card with logo + "Sign in with Microsoft" button | Implemented | Match |

---

## 10. Visual Design

### 10.1 Color Palette

All spec colors are defined as CSS custom properties in `main.css`:

| Token | Light | Dark | Status |
|---|---|---|---|
| `--color-bg-primary` | `#FFFFFF` | `#0F172A` | Match |
| `--color-bg-secondary` | `#F8FAFC` | `#1E293B` | Match |
| `--color-bg-tertiary` | `#F1F5F9` | `#334155` | Match |
| `--color-text-primary` | `#0F172A` | `#F1F5F9` | Match |
| `--color-text-secondary` | `#64748B` | `#94A3B8` | Match |
| `--color-accent` | `#2563EB` | `#3B82F6` | Match |
| `--color-accent-hover` | `#1D4ED8` | `#60A5FA` | Match |
| `--color-success` | `#16A34A` | `#22C55E` | Match |
| `--color-warning` | `#D97706` | `#F59E0B` | Match |
| `--color-danger` | `#DC2626` | `#EF4444` | Match |
| `--color-highlight` | `#FBBF24` | `#FBBF24` | Match |
| `--color-border` | `#E2E8F0` | (dark variant) | Match |

### 10.2 Typography

Fonts loaded via Google Fonts in `index.html`:
- `Inter` (body, headings, labels) — **matches spec**
- `JetBrains Mono` (monospace) — **matches spec**

### 10.3 Layout Variables

| Variable | Spec | Actual in CSS | Match |
|---|---|---|---|
| Sidebar width (expanded) | 240px | `--width-sidebar: 240px` | Match |
| Sidebar width (collapsed) | 64px | `--width-sidebar-collapsed: 64px` | Match |
| Viewer panel default | 420px | `--width-viewer: 420px` | Match |
| Top bar height | defined by CSS var | `--height-topbar: 56px` | Match |

---

## 11. Performance Considerations

| Feature | Spec | Actual | Status |
|---|---|---|---|
| Code splitting | Every route lazy-loaded | **Routes use direct component imports, not lazy-loaded** | **[DEVIATION]** Not lazy-loaded |
| **Virtual scrolling** | Lists > 100 items | **Not implemented** | **[NOT IMPLEMENTED]** |
| Debounced search | 300ms debounce | Implemented in TopBar | Match |
| PDF page caching | LRU max 10 pages | **Not implemented; renders single current page** | **[NOT IMPLEMENTED]** |
| **Image thumbnails** | Server-generated thumbnails with lazy loading | **Not implemented** | **[NOT IMPLEMENTED]** |
| Bundle size | PDF.js worker as separate chunk; Tailwind purge | PDF.js worker loaded; Tailwind v4 auto-purges | Match |
| URL-driven state | Filters synced to URL params | Implemented | Match |

---

## 12. Deviation Summary

### Critical Deviations (user-facing functionality gaps)

| # | Area | Description | Spec Section |
|---|---|---|---|
| D1 | Settings Drawer | Missing: default search mode, default top_k, parser defaults, connection info. Only has theme, mode, and about. | 3.6 |
| D2 | Upload Modal | Missing: storage mode selector, recursive toggle, parse-after-upload toggle, server-path ingestion. All hardcoded to defaults. | 3.1 |
| D3 | Thumbnail Sidebar | Renders page numbers instead of actual PDF page thumbnail images. | 3.3 |
| D4 | Tag Editing in Viewer | Tags displayed as read-only badges in the info panel, not as editable TagInput. | 3.4 |

### Missing Features

| # | Area | Description | Spec Section |
|---|---|---|---|
| M1 | Pinch-to-zoom | Touch device pinch-to-zoom for PDF viewer not implemented. | 3.3 |
| M2 | Element annotations | Hover/click tooltips showing element type, short_id, extracted text not implemented. | 3.3 |
| M3 | Image highlight overlay | Bounding-box highlights for image documents not implemented. | 3.3 |
| M4 | Virtual scrolling | No virtual scrolling for long document or search result lists. | 10 |
| M5 | PDF page caching | No LRU cache for decoded PDF pages. | 10 |
| M6 | Image thumbnails | No server-generated thumbnails for document grid. | 10 |
| M7 | Lazy route loading | Routes use direct imports instead of lazy-loaded dynamic imports. | 5 / 10 |

### Dead Code

| # | File | Description |
|---|---|---|
| DC1 | `views/UploadView.vue` | Full standalone upload page; unused by router. |
| DC2 | `views/DocumentsView.vue` | Full standalone documents page; unused by router. |
| DC3 | `views/DocumentDetailView.vue` | Full standalone document detail page; unused by router. |
| DC4 | `views/SearchView.vue` | Full standalone search page; unused by router. |
| DC5 | `views/CasesView.vue` | "Coming Soon" placeholder; unused by router. |
| DC6 | `views/SettingsView.vue` | Full standalone settings page; unused by router. |
| DC7 | `views/DocumentViewerView.vue` | Full standalone viewer page; unused by router. |

---

## 13. User Stories (Current State)

These user stories reflect what is **actually working** in the current codebase, organized by feature area.

### Authentication

| ID | Story | Status |
|---|---|---|
| US-AUTH-1 | As a user, I can sign in with my Microsoft account via Entra ID redirect flow. | Working |
| US-AUTH-2 | As a user, I am redirected to `/login` when visiting any protected page without authentication. | Working |
| US-AUTH-3 | As a user, after login I am redirected back to the page I originally requested. | Working |
| US-AUTH-4 | As a user, I can see my name in the top bar and log out. | Working |
| US-AUTH-5 | As a user, my session persists across page refreshes via localStorage token cache. | Working |

### Document Upload

| ID | Story | Status |
|---|---|---|
| US-UP-1 | As a user, I can open the upload modal from the top bar or by navigating to `/upload`. | Working |
| US-UP-2 | As a user, I can drag-and-drop files or click to select files for upload. | Working |
| US-UP-3 | As a user, I can select a folder for upload. | Working |
| US-UP-4 | As a user, I can review queued files and remove individual files before uploading. | Working |
| US-UP-5 | As a user, I can assign tags to the batch before uploading. | Working |
| US-UP-6 | As a user, I can see upload progress and results (ingested/skipped). | Working |
| US-UP-7 | As a user, I can choose storage mode (managed/external) before upload. | Not Working (hardcoded in modal) |
| US-UP-8 | As a user, I can toggle recursive ingestion for folder uploads. | Not Working (missing from modal) |
| US-UP-9 | As a user, I can trigger parsing immediately after upload. | Not Working (missing from modal) |

### Document Browsing

| ID | Story | Status |
|---|---|---|
| US-DOC-1 | As a user, I can see all my documents in a grid or list view on the main gallery page. | Working |
| US-DOC-2 | As a user, I can switch between grid and list view modes. | Working |
| US-DOC-3 | As a user, I can filter documents by status, file type, document type, tags, and date range. | Working |
| US-DOC-4 | As a user, I can sort documents by created date, modified date, name, or status. | Working |
| US-DOC-5 | As a user, I can see active filters as removable chips. | Working |
| US-DOC-6 | As a user, I can paginate through documents with configurable page size (25, 50, 100). | Working |
| US-DOC-7 | As a user, I can bookmark filtered/sorted views because filters sync to URL params. | Working |
| US-DOC-8 | As a user, I can select multiple documents and perform bulk actions (parse, tag, delete, assign to case). | Working |
| US-DOC-9 | As a user, I can click a document card to open it in the right viewer panel. | Working |

### Document Viewing

| ID | Story | Status |
|---|---|---|
| US-VIEW-1 | As a user, I can view PDF documents rendered in a resizable right-side panel. | Working |
| US-VIEW-2 | As a user, I can navigate between PDF pages using Prev/Next buttons and page input. | Working |
| US-VIEW-3 | As a user, I can zoom in/out and fit-to-width/fit-to-page. | Working |
| US-VIEW-4 | As a user, I can select text in the PDF via the text layer overlay. | Working |
| US-VIEW-5 | As a user, I can see search term highlights on the PDF when opened from search results. | Working |
| US-VIEW-6 | As a user, I can toggle an info panel showing document metadata, tags, and advanced details. | Working |
| US-VIEW-7 | As a user, I can resize the viewer panel by dragging its left edge. | Working |
| US-VIEW-8 | As a user, on mobile/tablet the viewer opens as a full-screen overlay. | Working |
| US-VIEW-9 | As a user, I can download the original file from the viewer toolbar. | Working |
| US-VIEW-10 | As a user, I can enter fullscreen mode for the viewer. | Working |
| US-VIEW-11 | As a user, I can close the viewer with the Close button or Escape key. | Working |
| US-VIEW-12 | As a user, I can navigate between search results from the viewer bottom toolbar. | Working |
| US-VIEW-13 | As a user, I can view images in the viewer with zoom support. | Working |
| US-VIEW-14 | As a user, I can jump to a page using the thumbnail sidebar page numbers. | Working (numbers only, not thumbnails) |
| US-VIEW-15 | As a user, I can edit tags on a document from the viewer info panel. | Not Working (read-only display) |

### Search

| ID | Story | Status |
|---|---|---|
| US-SRCH-1 | As a user, I can search documents from the top bar search input. | Working |
| US-SRCH-2 | As a user, search is debounced (300ms) to avoid excessive API calls. | Working |
| US-SRCH-3 | As a user, I can focus the search bar with Cmd+K or `/`. | Working |
| US-SRCH-4 | As a user, search results show file name, page number, relevance score, and content snippet. | Working |
| US-SRCH-5 | As a user, clicking a search result opens the viewer at the matched page with highlights. | Working |
| US-SRCH-6 | As a user (advanced), I can choose between fulltext, vector, and hybrid search modes. | Working |
| US-SRCH-7 | As a user (advanced), I can configure search parameters (top_k, min_score, fuzzy, vector index). | Working |
| US-SRCH-8 | As a user (advanced), I can see score breakdowns for each search result. | Working |

### Cases

| ID | Story | Status |
|---|---|---|
| US-CASE-1 | As a user, I can view all cases in a card grid on the Cases tab. | Working |
| US-CASE-2 | As a user, I can create a new case with a name and optional description. | Working |
| US-CASE-3 | As a user, I can view case details with assigned documents. | Working |
| US-CASE-4 | As a user, I can add documents to a case from the case detail view or from the gallery bulk actions. | Working |
| US-CASE-5 | As a user, I can remove documents from a case. | Working |
| US-CASE-6 | As a user, I can edit a case's name and description inline. | Working |
| US-CASE-7 | As a user, I can delete a case. | Working |
| US-CASE-8 | As a user, I can run field extraction on all documents in a case. | Working |
| US-CASE-9 | As a user, I can view extraction results per document with field names, values, and justifications. | Working |

### Settings & Preferences

| ID | Story | Status |
|---|---|---|
| US-SET-1 | As a user, I can toggle between Light, Dark, and System themes. | Working |
| US-SET-2 | As a user, I can toggle between Simple and Advanced modes. | Working |
| US-SET-3 | As a user, my theme and mode preferences persist across sessions. | Working |
| US-SET-4 | As a user, I can configure default search mode and top_k. | Not Working (missing from drawer; exists in unused SettingsView) |
| US-SET-5 | As a user (advanced), I can configure default parser and embedding models. | Not Working (missing from drawer; exists in unused SettingsView) |
| US-SET-6 | As a user, I can see backend connection status and latency. | Not Working (missing from drawer; exists in unused SettingsView) |

### Navigation & Responsiveness

| ID | Story | Status |
|---|---|---|
| US-NAV-1 | As a user, I can switch between Documents and Cases tabs in the sidebar. | Working |
| US-NAV-2 | As a user on mobile, I navigate via a bottom tab bar (Documents, Cases, More). | Working |
| US-NAV-3 | As a user on mobile, I can access Upload and Settings from the More menu. | Working |
| US-NAV-4 | As a user on tablet, the sidebar opens as a drawer overlay. | Working |
| US-NAV-5 | As a user on desktop, the sidebar can be collapsed to an icon rail. | Working |

---

## 14. Architecture Notes

### What's Working Well
- The unified gallery architecture (single GalleryView as hub) is implemented and functional.
- Modal/drawer overlay pattern for Upload and Settings works correctly via route meta.
- Responsive breakpoints cover all four tiers (mobile, tablet, desktop, wide).
- PDF viewing with text layer highlighting is robust.
- Search result navigation through the viewer is smooth.
- State management with Pinia is clean and well-organized.
- Authentication flow with MSAL is complete.

### What Needs Attention
1. **Dead legacy views** — Seven full-page views exist but are unreachable. They contain features (like full settings, standalone upload) that the modal/drawer equivalents lack.
2. **Feature parity gap** — The UploadModal and SettingsDrawer are simpler than their legacy view counterparts. Either the drawers need to be enhanced or the feature requirements relaxed in the spec.
3. **Performance features** — Virtual scrolling, lazy route loading, and PDF page caching are specified but not implemented. These will matter as document collections grow.
4. **Tag editing in viewer** — Tags are displayed read-only in the info panel. Users must leave the viewer context to manage tags.
