# Plan: Page View PDF + Display Elements Feature

## Context

The document viewer's page mode currently shows a static high-res thumbnail image (`PageImageViewer`). The user wants page mode to use the same PDF viewer (`VuePdfViewer`) with page jumping and search highlighting. Additionally, a new **Display Elements** feature is needed: a toggle that splits the viewer to show element annotations on the PDF (color-coded by type) and an element browser panel with bidirectional navigation.

**No backend changes required.** Elements are stored inline in the Document MongoDB collection and returned as part of `GET /documents/{id}`. The frontend already receives them via `useDocumentViewer` → `getDocument(id)` → `viewer.document.value.elements`. Page dimensions (`width`, `height`, `unit`) are available from `getPages(id)` → `viewer.pages.value`.

## Phase 1: Update Spec (`docs/specs/UI.md`)

Update the following spec sections:

### Section 3.3 — Document Viewer
- Change page mode tabs from `[Page View, HTML, Markdown]` to `[PDF, HTML, Markdown]`
- Page mode PDF tab uses `VuePdfViewer` jumped to the specific page with `highlight-text` prop
- Remove `PageImageViewer` from page mode tab descriptions
- Update the Panel Layout ASCII art to reflect new tabs

### New Section 3.8 — Display Elements
Add complete spec for the Display Elements feature covering:
- Toggle button in viewer header (Layers icon)
- Normal mode: horizontal split (top=PDF+annotations, bottom=element browser)
- Expanded mode: viewer expands, vertical split (left=PDF, right=browser)
- Annotation colors: paragraph=blue, table=green, kv=purple
- Tooltip on hover: element type, short_id, content preview
- Bidirectional navigation (click annotation ↔ highlight in browser)
- Element browser: grouped by type, collapsible groups, element cards

### Section 4.1 — Directory Structure
Add new files:
- `components/viewer/ElementAnnotationOverlay.vue`
- `components/viewer/ElementBrowser.vue`
- `components/viewer/ElementCard.vue`
- `components/viewer/SplitViewContainer.vue`
- `composables/useElementDisplay.ts`

### Section 4.2 — Key Composables
Add `useElementDisplay()` interface documentation.

---

## Phase 2: Implementation — Page View PDF Change

### 2.1 `mydocs-ui/src/types/index.ts`
- Change `PageViewerTab` from `'page-view' | 'html' | 'markdown'` to `'pdf' | 'html' | 'markdown'`

### 2.2 `mydocs-ui/src/stores/app.ts`
- Change all `'page-view'` references to `'pdf'`:
  - `viewerActivePageTab` default: `'page-view'` → `'pdf'`
  - `openViewer()`: `'page-view'` → `'pdf'`
  - `switchToPageMode()`: `'page-view'` → `'pdf'`
  - `closeViewer()`: `'page-view'` → `'pdf'`

### 2.3 `mydocs-ui/src/components/layout/RightViewerPanel.vue`
- Change `pageTabs` definition:
  ```typescript
  const pageTabs = [
    { key: 'pdf' as const, label: 'PDF' },
    { key: 'html' as const, label: 'HTML' },
    { key: 'markdown' as const, label: 'Markdown' },
  ]
  ```
- Replace page mode content: swap `PageImageViewer` for `DocumentViewer` with same props as document mode PDF tab
- Remove `PageImageViewer` import
- Update `setActiveTab` type cast: `'page-view'` → `'pdf'`

---

## Phase 3: Implementation — Display Elements Feature

### 3.1 New types in `mydocs-ui/src/types/index.ts`

```typescript
export interface ElementAnnotation {
  elementId: string
  shortId?: string
  type: DocumentElementType
  x: number        // % of page width
  y: number        // % of page height
  width: number    // % of page width
  height: number   // % of page height
  contentPreview: string
  pageNumber: number
}
```

Add element color constants:
- `paragraph`: blue `rgba(59, 130, 246, 0.25)` / border `rgba(59, 130, 246, 0.6)`
- `table`: green `rgba(34, 197, 94, 0.25)` / border `rgba(34, 197, 94, 0.6)`
- `key_value_pair`: purple `rgba(168, 85, 247, 0.25)` / border `rgba(168, 85, 247, 0.6)`
- `image`: yellow `rgba(234, 179, 8, 0.25)` / border `rgba(234, 179, 8, 0.6)`
- `barcode`: red `rgba(239, 68, 68, 0.25)` / border `rgba(239, 68, 68, 0.6)`

### 3.2 State additions in `mydocs-ui/src/stores/app.ts`

New state:
```typescript
const elementsDisplayActive = ref(false)
const elementsDisplayExpanded = ref(false)
const activeElementId = ref<string | null>(null)
```

New actions:
- `toggleElementsDisplay()` — toggles active; resets expanded+activeElement when turning off
- `toggleElementsExpanded()` — toggles expanded mode
- `setActiveElement(id: string | null)` — sets active element for bidirectional nav

Modify `closeViewer()` to reset all three new state values.

### 3.3 New composable: `mydocs-ui/src/composables/useElementDisplay.ts`

Reuses polygon→rect conversion pattern from existing `useHighlights.ts`.

**Inputs:** `elements: Ref<DocumentElement[]>`, `pages: Ref<DocumentPage[]>`, `currentPage: Ref<number>`

**Outputs:**
- `pageElements` — elements filtered to current page
- `currentPageDimensions` — `{ width, height, unit }` from pages array for current page
- `annotations` — `ElementAnnotation[]` with percentage-based positions computed from `element_data.boundingRegions` polygons divided by page dimensions
- `pageElementsByType` — `Record<string, DocumentElement[]>` grouped by type for current page

**Key logic:**
- For standard elements: extract from `element_data.boundingRegions[].polygon`
- For key-value pairs: union `element_data.key.boundingRegions[]` + `element_data.value.boundingRegions[]`
- Content preview: KV → `"key: value"`, Table → `"Table: NxM"`, Others → first 120 chars of `content`
- Coordinates: `(minX / pageWidth * 100)%` for percentage-based positioning

### 3.4 New component: `mydocs-ui/src/components/viewer/SplitViewContainer.vue`

Generic resizable split container. Props:
- `direction: 'horizontal' | 'vertical'` — horizontal=top/bottom, vertical=left/right
- `initialRatio: number` (default 0.6)
- `minRatio / maxRatio` (default 0.2 / 0.8)

Slots: `#first`, `#second`. Draggable divider between panels using mousedown/mousemove/mouseup on document.

### 3.5 New component: `mydocs-ui/src/components/viewer/ElementAnnotationOverlay.vue`

Renders colored semi-transparent boxes over PDF. Props:
- `annotations: ElementAnnotation[]`
- `activeElementId: string | null`

Uses same positioning approach as existing `HighlightOverlay.vue` — `position: absolute; inset: 0; pointer-events: none` container with individual `pointer-events: auto` boxes.

Each box:
- Background color from `ELEMENT_TYPE_COLORS[ann.type]`
- 1px solid border from `ELEMENT_TYPE_BORDER_COLORS[ann.type]`
- Active element gets box-shadow highlight; others dim to 0.3 opacity when any is active
- Custom tooltip on mouseenter (fixed-positioned div near cursor) showing type label, short_id, content preview
- Click emits `select(elementId)`

### 3.6 New component: `mydocs-ui/src/components/viewer/ElementCard.vue`

Individual element card. Props: `element: DocumentElement`, `isActive: boolean`.

Shows short_id, page number badge, content preview (line-clamp-2). When `isActive` becomes true, calls `scrollIntoView({ behavior: 'smooth', block: 'nearest' })`. Active card gets colored ring border. Full content shown in expandable section when active.

### 3.7 New component: `mydocs-ui/src/components/viewer/ElementBrowser.vue`

Element list grouped by type. Props:
- `elements: DocumentElement[]`
- `currentPage: number`
- `activeElementId: string | null`

Header with "All pages" toggle checkbox and element count. Groups with colored indicator dots, type labels, counts, collapsible via ChevronDown toggle. Each group contains `ElementCard` components.

Emits: `select(elementId)`, `go-to-page(pageNumber)`. When clicking a card on a different page, emits both.

### 3.8 Integrate into `mydocs-ui/src/components/layout/RightViewerPanel.vue`

**Header:** Add `Layers` icon button (from lucide-vue-next) next to Info button. Shown only when `viewer.document.value?.elements?.length > 0`. Highlighted when `elementsDisplayActive`. When elements are active, add an expand/collapse button (`Maximize2`/`Minimize2`).

**Content area:** When `elementsDisplayActive && activeTabKey === 'pdf'`:
- Wrap content in `SplitViewContainer`:
  - `direction`: `elementsDisplayExpanded ? 'vertical' : 'horizontal'`
  - `#first` slot: `DocumentViewer` + `ElementAnnotationOverlay` inside a `relative` div
  - `#second` slot: `ElementBrowser`
- When not active or non-PDF tab: render normally (current behavior)

**Use composable:** Initialize `useElementDisplay(viewer.document.elements, viewer.pages, viewer.currentPage)` and pass outputs to child components.

**Element selection handler:** `handleElementSelect(elementId)` — calls `appStore.setActiveElement(id)`, if element is on different page, calls `viewer.goToPage(element.page_number)`.

### 3.9 Modify `mydocs-ui/src/components/layout/AppShell.vue`

Add expanded mode support. When `appStore.elementsDisplayActive && appStore.elementsDisplayExpanded`:
- Override viewer panel width to `Math.max(viewerPanelWidth, Math.floor(window.innerWidth * 0.7))`
- Add `transition-[width] duration-300` class for smooth animation

Compute effective width:
```typescript
const effectiveViewerWidth = computed(() => {
  if (appStore.viewerOpen && appStore.elementsDisplayActive && appStore.elementsDisplayExpanded) {
    return Math.max(viewerPanelWidth.value, Math.floor(window.innerWidth * 0.7))
  }
  return viewerPanelWidth.value
})
```

Bind `:style` to `effectiveViewerWidth` instead of `viewerPanelWidth`.

---

## Phase 4: Update Actual State Docs (`docs/UI.md`)

Update all relevant sections:
- Section 5.3: Document Viewer — page mode tabs changed, elements display feature added
- Section 12: Deviation Summary — remove M2 (annotation overlay) as it's now implemented
- Section 13: User Stories — add new stories for elements display, update VIEW stories for page mode PDF
- New file inventory in Section 2

---

## File Summary

| Action | File | Description |
|--------|------|-------------|
| Modify | `docs/specs/UI.md` | Spec updates |
| Modify | `mydocs-ui/src/types/index.ts` | `PageViewerTab` change, new types |
| Modify | `mydocs-ui/src/stores/app.ts` | Page tab default, elements state |
| Modify | `mydocs-ui/src/components/layout/RightViewerPanel.vue` | Page mode PDF, elements split view |
| Modify | `mydocs-ui/src/components/layout/AppShell.vue` | Expanded mode width |
| Create | `mydocs-ui/src/composables/useElementDisplay.ts` | Element display logic |
| Create | `mydocs-ui/src/components/viewer/SplitViewContainer.vue` | Generic split container |
| Create | `mydocs-ui/src/components/viewer/ElementAnnotationOverlay.vue` | Colored annotation boxes |
| Create | `mydocs-ui/src/components/viewer/ElementBrowser.vue` | Grouped element list |
| Create | `mydocs-ui/src/components/viewer/ElementCard.vue` | Individual element card |
| Modify | `docs/UI.md` | Actual state updates |

---

## Verification Checklist

1. **Page mode PDF**: Search → click result → viewer opens with PDF tab at correct page → search terms highlighted via `highlight-text` prop
2. **Tab labels**: Page mode shows [PDF, HTML, Markdown] not [Page View, ...]
3. **Elements toggle**: Click Layers button → content splits → annotations appear on PDF
4. **Annotation colors**: Paragraphs blue, tables green, KV pairs purple
5. **Tooltip**: Hover annotation → tooltip with type, short_id, content
6. **Browser → viewer**: Click element card → annotation highlights; if different page, viewer navigates first
7. **Viewer → browser**: Click annotation → corresponding card scrolls into view and highlights
8. **Expanded mode**: Toggle expand → panel widens, layout switches to left/right split
9. **Collapse expanded**: Toggle again → returns to normal width and top/bottom
10. **Draggable divider**: Drag split divider → panels resize proportionally
11. **No elements**: Documents with no elements → Layers button hidden
12. **Page navigation**: Change page while elements active → annotations update for new page
13. **Dark mode**: Verify annotation colors contrast in both themes
