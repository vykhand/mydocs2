# UI Specification

| Field   | Value                |
|---------|----------------------|
| Package | `mydocs-ui`          |
| Version | 1.0                  |
| Status  | Draft                |
| Stack   | Vue 3, Vite, Tailwind CSS, Pinia |

## 1. Overview

A single-page application providing a modern, professional interface for document management, search, and case organization. The UI communicates exclusively with the FastAPI backend via `/api/v1/` endpoints.

### 1.1 Design Principles

- **Mobile-first responsive** -- usable on phones, tablets, and desktops.
- **Simple by default, powerful when needed** -- every feature has a sensible default; advanced controls are hidden behind an "Advanced Settings" toggle.
- **Consistent visual language** -- clean typography, generous whitespace, subtle shadows, and a neutral color palette with a single accent color.
- **Immediate feedback** -- every user action produces visible feedback (toasts, progress bars, skeleton loaders).

### 1.2 Technology Stack

| Layer         | Choice               | Rationale                              |
|---------------|----------------------|----------------------------------------|
| Framework     | Vue 3 (Composition API, `<script setup>`) | Reactive, lightweight, strong ecosystem |
| Build         | Vite                 | Fast HMR, native ESM                   |
| Styling       | Tailwind CSS 4       | Utility-first, responsive breakpoints  |
| State         | Pinia                | Official Vue store, devtools support    |
| HTTP          | Axios                | Interceptors for error handling         |
| Routing       | Vue Router 4         | Nested routes, lazy loading             |
| Icons         | Lucide Vue           | Consistent, tree-shakeable icon set     |
| PDF Viewer    | PDF.js (`pdfjs-dist`)| Renders PDF pages on canvas, supports text layer and highlight annotations |
| Notifications | Vue Toastification   | Toast messages for user feedback        |

## 2. Layout & Navigation

### 2.1 Shell Layout

```
+---------------------------------------------------------------+
| Top Bar  [Logo / App Name]            [Simple|Advanced] [User]|
+----------+----------------------------------------------------+
|          |                                                    |
| Sidebar  |               Main Content Area                   |
| (nav)    |                                                    |
|          |                                                    |
+----------+----------------------------------------------------+
```

- **Top Bar** -- fixed; contains app logo/name on the left, mode toggle (Simple/Advanced) center-right, and a user avatar/menu on the far right.
- **Sidebar** -- collapsible; icons + labels on desktop, icons-only when collapsed, bottom tab-bar on mobile (< 768px). Navigation items:
  1. Upload
  2. Documents
  3. Search
  4. Cases
  5. Settings
- **Main Content Area** -- scrollable; renders the active route.

### 2.2 Responsive Breakpoints

| Breakpoint | Width       | Sidebar Behavior          |
|------------|-------------|---------------------------|
| `sm`       | < 768px     | Hidden; bottom tab-bar    |
| `md`       | 768–1023px  | Collapsed (icons only)    |
| `lg`       | >= 1024px   | Expanded (icons + labels) |

### 2.3 Simple / Advanced Mode

A global toggle stored in Pinia and persisted to `localStorage`.

- **Simple mode** -- hides advanced search parameters, parse config overrides, embedding options, and hybrid search tuning. Uses backend defaults.
- **Advanced mode** -- exposes all configurable fields as described in each section below.

## 3. Views & Features

### 3.1 Upload View (`/upload`)

Allows ingesting files and folders into the system.

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

### 3.2 Documents View (`/documents`)

Browse, filter, and manage all ingested documents.

#### UI Elements

| Element              | Description |
|----------------------|-------------|
| Filter bar           | Inline filters: status dropdown (`all`, `new`, `parsing`, `parsed`, `failed`), file type dropdown, tag selector (multi-select), date range picker, text search on file name. |
| Sort control         | Sort by: name, created date, modified date, status. Ascending/descending toggle. |
| Document table/grid  | Default: table view (columns: name, type, status, tags, pages, created). Toggle to grid/card view showing thumbnail + metadata. |
| Pagination           | Page size selector (25, 50, 100) and page navigation. |
| Bulk actions bar     | Appears when one or more rows are selected. Actions: Parse, Add Tags, Remove Tags, Assign to Case, Delete. |
| Document row actions | Inline icon buttons: View, Parse, Tag, Delete. |

#### Document Detail Panel (`/documents/:id`)

Opens as a side panel (desktop) or full page (mobile).

| Section        | Content |
|----------------|---------|
| Header         | File name, type badge, status badge, created/modified dates. |
| Metadata       | Size, MIME type, SHA-256, page count, author, title (from `file_metadata`). |
| Tags           | Editable chip list. Add/remove tags via `POST /api/v1/documents/{id}/tags` and `DELETE /api/v1/documents/{id}/tags/{tag}`. |
| Pages          | Paginated list/grid of page thumbnails. Click opens the Document Viewer (Section 3.4). |
| Elements       | Collapsible list of `DocumentElement` entries grouped by page, showing type badge and short_id. |
| Cases          | List of cases this document belongs to, with links. |
| Actions        | Re-parse button, Delete button (with confirmation dialog). |

#### Advanced Mode Additions

| Element           | Description |
|-------------------|-------------|
| Parse config      | Expandable section to override `azure_di_model`, `azure_di_kwargs`, and embedding configs before triggering parse. |
| Raw JSON toggle   | Button to view the raw document/page JSON from the API. |

### 3.3 Search View (`/search`)

Multifaceted search across documents and pages.

#### Simple Mode

| Element          | Description |
|------------------|-------------|
| Search bar       | Large, centered input with a search icon. Placeholder: "Search documents...". Supports Enter to submit. |
| Search target    | Toggle pills: "Pages" (default) / "Documents". |
| Quick filters    | Collapsible row: tags (multi-select), file type, date range. |
| Results list     | Cards showing: file name, page number (if page search), relevance score bar, snippet with highlighted matching terms, tags. |
| Result actions   | "View" opens the Document Viewer at the matched page with highlights. "Open Document" navigates to the document detail. |

The simple mode uses `search_mode: "hybrid"` with all default config values.

#### Advanced Mode Additions

| Element                  | Description |
|--------------------------|-------------|
| Search mode selector     | Radio group: Fulltext / Vector / Hybrid. |
| Fulltext config panel    | `content_field` input, fuzzy toggle + `max_edits` (1-2) + `prefix_length` slider, `score_boost` number input. |
| Vector config panel      | Index selector (populated from `GET /api/v1/search/indices`), embedding model input, `num_candidates` slider, `score_boost` number input. |
| Hybrid config panel      | Combination method radio (RRF / Weighted Sum), `rrf_k` input, weight sliders for fulltext and vector (summing to 1.0). |
| Filters panel            | Document IDs input (comma-separated), status dropdown, document type dropdown -- in addition to the simple-mode filters. |
| Result controls          | `top_k` input (default 10), `min_score` slider (0.0 – 1.0), `include_content_fields` multi-select. |
| Score breakdown          | Each result card shows individual fulltext and vector scores alongside the combined score. |

#### API Integration

- Calls `POST /api/v1/search` with the assembled `SearchRequest` body.
- Debounces input by 300ms for live-search (optional; can also be submit-only).

### 3.4 Document Viewer (`/documents/:id/view` or modal)

An in-app viewer for PDF and image documents with search-result highlighting.

#### PDF Viewer

| Element             | Description |
|---------------------|-------------|
| Page canvas         | Renders the current PDF page via PDF.js onto a `<canvas>` element at high resolution. |
| Text layer          | Transparent text overlay on top of the canvas for text selection and highlight positioning. |
| Page navigation     | Previous / Next buttons, page number input, total page count. Keyboard: arrow keys. |
| Zoom controls       | Zoom in, zoom out, fit-to-width, fit-to-page. Pinch-to-zoom on touch devices. |
| Thumbnail sidebar   | Vertical strip of page thumbnails on the left (hideable on mobile). Active page is highlighted. Click to jump. |
| Highlight overlay   | When opened from a search result, the viewer scrolls to the matched page and draws semi-transparent highlight rectangles over the matching content regions. Highlights are derived from `DocumentElement.element_data` bounding regions that overlap with the search result content. |
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
| Close            | Returns to previous view. |

### 3.5 Tags Management

Tags are free-form strings attached to documents.

#### Tag Input Component

A reusable component used in Upload, Document Detail, Bulk Actions, and Search Filters.

| Behavior              | Description |
|-----------------------|-------------|
| Autocomplete          | As the user types, suggests existing tags fetched from the backend (derived from aggregation on `documents.tags`). |
| Create on Enter       | Pressing Enter or comma creates a new tag chip. |
| Remove on Backspace   | Backspace in an empty input removes the last chip. |
| Click to remove       | Each chip has an "x" button. |
| Validation            | Tags are lowercased, trimmed, max 50 characters, no commas. Duplicates are silently ignored. |

#### Tag Assignment Flows

1. **Single document** -- Document Detail panel > Tags section > add/remove chips. Each change fires `POST /api/v1/documents/{id}/tags` or `DELETE /api/v1/documents/{id}/tags/{tag}`.
2. **Bulk** -- Select documents in the Documents table > Bulk Actions bar > "Add Tags" or "Remove Tags" opens a modal with a tag input. Applies to all selected documents via sequential API calls (with a progress indicator).
3. **At upload** -- Tags entered in the Upload view are passed to the ingest endpoint and applied to all ingested documents.

### 3.6 Cases View (`/cases`)

Cases group related documents for review or investigation.

#### Case List

| Element             | Description |
|---------------------|-------------|
| Case table          | Columns: case name, description (truncated), document count, created date, status badge. |
| Create Case button  | Opens a modal/form to create a new case. |
| Search/filter       | Text search on case name, status filter. |
| Case row actions    | View, Edit, Delete. |

#### Create / Edit Case Modal

| Field         | Type        | Description |
|---------------|-------------|-------------|
| Name          | Text input  | Required. Max 200 characters. |
| Description   | Textarea    | Optional. Markdown supported. |
| Status        | Dropdown    | `open` (default), `in_review`, `closed`. |
| Tags          | Tag input   | Optional tags for the case itself. |

#### Case Detail View (`/cases/:id`)

| Section             | Description |
|---------------------|-------------|
| Header              | Case name, status badge, created/modified dates, description. |
| Document list       | Table of documents assigned to this case: name, type, status, tags, date added. Sortable and filterable. |
| Add documents       | Button opens a document picker modal -- a searchable, filterable list of all documents with checkboxes. Selected documents are assigned to the case. |
| Remove document     | Per-row action to unassign a document from the case (does not delete the document). |
| Bulk actions        | Select multiple documents > Remove from Case, Add Tags. |
| Notes / Activity    | A simple timeline/log of actions taken on the case (document added, status changed, etc.). |

#### Data Model Note

Cases are not yet defined in the backend spec. The UI spec assumes the following endpoints will be added:

| Method   | Endpoint                              | Purpose |
|----------|---------------------------------------|---------|
| `GET`    | `/api/v1/cases`                       | List cases (with pagination, filters). |
| `POST`   | `/api/v1/cases`                       | Create a new case. |
| `GET`    | `/api/v1/cases/{case_id}`             | Get case details. |
| `PUT`    | `/api/v1/cases/{case_id}`             | Update case metadata. |
| `DELETE` | `/api/v1/cases/{case_id}`             | Delete a case (does not delete documents). |
| `POST`   | `/api/v1/cases/{case_id}/documents`   | Assign documents to a case. |
| `DELETE` | `/api/v1/cases/{case_id}/documents/{document_id}` | Remove a document from a case. |

Assumed backend model:

```python
class Case(MongoBaseModel):
    name: str
    description: Optional[str] = None
    status: str = "open"  # open, in_review, closed
    tags: list[str] = []
    document_ids: list[str] = []
    created_at: datetime
    modified_at: datetime

    class Settings:
        name = "cases"
```

### 3.7 Settings View (`/settings`)

Global application settings.

| Section              | Description |
|----------------------|-------------|
| Theme                | Light / Dark / System toggle (uses Tailwind `dark:` variant). |
| Default search mode  | Dropdown: Hybrid / Fulltext / Vector. Applied when search is used in Simple mode. |
| Default top_k        | Number input (default 10). |
| Parser defaults      | Azure DI model selector, embedding model selector. Only shown in Advanced mode. |
| Connection info      | Displays backend URL, connection status indicator (green/red dot with latency). |
| About                | App version, backend version (from a `/api/v1/health` endpoint). |

All settings are stored in `localStorage` via Pinia persisted state.

## 4. Component Architecture

### 4.1 Directory Structure

```
mydocs-ui/
  index.html
  vite.config.ts
  tailwind.config.ts
  tsconfig.json
  package.json
  src/
    main.ts                          # App bootstrap
    App.vue                          # Root component (shell layout)
    router/
      index.ts                       # Route definitions
    stores/
      app.ts                         # Global state (mode, theme, sidebar)
      documents.ts                   # Document list state, pagination
      search.ts                      # Search state, results
      cases.ts                       # Case list state
      tags.ts                        # Tag autocomplete cache
    api/
      client.ts                      # Axios instance, interceptors
      documents.ts                   # Document API calls
      search.ts                      # Search API calls
      cases.ts                       # Case API calls
    views/
      UploadView.vue
      DocumentsView.vue
      DocumentDetailView.vue
      SearchView.vue
      CasesView.vue
      CaseDetailView.vue
      SettingsView.vue
    components/
      layout/
        AppShell.vue                 # Top bar + sidebar + content slot
        SidebarNav.vue
        TopBar.vue
        MobileTabBar.vue
      common/
        TagInput.vue                 # Reusable tag chip input
        StatusBadge.vue              # Colored status pills
        FileTypeBadge.vue
        ConfirmDialog.vue
        EmptyState.vue               # Illustration + message for empty lists
        LoadingSkeleton.vue
        PaginationBar.vue
        DateRangePicker.vue
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
        CaseTable.vue
        CaseForm.vue
        DocumentPicker.vue           # Modal for assigning docs to case
        CaseTimeline.vue
    composables/
      useSearch.ts                   # Search logic, debouncing
      useDocumentViewer.ts           # PDF.js lifecycle, page navigation
      useHighlights.ts              # Compute highlight rects from elements
      useTags.ts                     # Tag autocomplete, CRUD
      useResponsive.ts               # Breakpoint-aware reactive state
    types/
      index.ts                       # TypeScript interfaces mirroring backend models
    assets/
      logo.svg
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

```typescript
interface UseDocumentViewer {
  document: Ref<Document>
  pages: Ref<DocumentPage[]>
  currentPage: Ref<number>
  totalPages: Ref<number>
  zoom: Ref<number>
  goToPage(n: number): void
  nextPage(): void
  prevPage(): void
  setZoom(level: number): void
  fitToWidth(): void
  fitToPage(): void
}
```

#### `useHighlights(page, searchResult?)`

```typescript
interface UseHighlights {
  highlights: Ref<HighlightRect[]>  // Array of { x, y, width, height } in page coordinates
  activeHighlight: Ref<HighlightRect | null>
  scrollToFirstHighlight(): void
}
```

Computes highlight rectangles by:
1. Taking the search result's matched content.
2. Finding `DocumentElement` entries on the current page whose text overlaps with the matched content.
3. Extracting bounding region polygons from `element_data`.
4. Converting polygon coordinates to page-relative rectangles scaled to the current zoom level.

## 5. Routing

```typescript
const routes = [
  { path: '/',            redirect: '/documents' },
  { path: '/upload',      component: () => import('./views/UploadView.vue') },
  { path: '/documents',   component: () => import('./views/DocumentsView.vue') },
  { path: '/documents/:id', component: () => import('./views/DocumentDetailView.vue') },
  { path: '/documents/:id/view', component: () => import('./views/DocumentViewer.vue') },
  { path: '/search',      component: () => import('./views/SearchView.vue') },
  { path: '/cases',       component: () => import('./views/CasesView.vue') },
  { path: '/cases/:id',   component: () => import('./views/CaseDetailView.vue') },
  { path: '/settings',    component: () => import('./views/SettingsView.vue') },
]
```

All routes are lazy-loaded for optimal bundle splitting.

## 6. API Client

```typescript
// api/client.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  response => response,
  error => {
    const detail = error.response?.data?.detail || 'An unexpected error occurred'
    toast.error(detail)
    return Promise.reject(error)
  }
)
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
- Sidebar width: 240px expanded, 64px collapsed.

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
- ARIA labels on icon-only buttons.
- Color contrast ratios meet WCAG 2.1 AA (4.5:1 for text, 3:1 for UI components).
- Screen-reader announcements for toast notifications via `aria-live="polite"`.
- Drop zone is activatable via keyboard (Enter/Space).

## 10. Performance Considerations

- **Code splitting** -- every route is lazy-loaded.
- **Virtual scrolling** -- document and search result lists use virtual scrolling for lists exceeding 100 items.
- **Debounced search** -- 300ms debounce on search input to avoid excessive API calls.
- **PDF page caching** -- PDF.js renders only the visible page and one page ahead/behind; decoded pages are cached in memory (LRU, max 10 pages).
- **Image thumbnails** -- document grid view uses server-generated thumbnails (future backend endpoint) with lazy loading via `IntersectionObserver`.
- **Bundle size** -- PDF.js worker loaded as a separate chunk; Tailwind purges unused styles in production.

## 11. Future Considerations

- **Real-time updates** -- WebSocket or SSE for parse-status changes and batch progress.
- **Collaborative annotations** -- multiple users highlighting and commenting on document pages.
- **Saved searches** -- persist search configurations as named presets.
- **Export** -- export search results or case document lists as CSV/PDF reports.
- **Drag-and-drop case assignment** -- drag documents from the document list directly onto a case in the sidebar.
- **Offline support** -- service worker caching for recently viewed documents.
