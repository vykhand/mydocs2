# Page View PDF + Display Elements Feature

## Overview

Two related changes to the document viewer:

1. **Page mode PDF tab** — Page mode now uses `VuePdfViewer` (via `DocumentViewer`) instead of `PageImageViewer`, giving search highlighting and consistent rendering across both viewer modes.
2. **Display Elements** — A new feature that overlays color-coded element annotations on the PDF and provides a companion element browser panel with bidirectional navigation.

## Changes Summary

### Phase 1: Page View → PDF

**Problem**: Page mode showed a static high-res thumbnail image with no search highlighting.
**Solution**: Replaced `PageImageViewer` with the same `DocumentViewer` component used in document mode.

| File | Change |
|------|--------|
| `types/index.ts` | `PageViewerTab` changed from `'page-view' \| 'html' \| 'markdown'` to `'pdf' \| 'html' \| 'markdown'` |
| `stores/app.ts` | All `'page-view'` default values → `'pdf'` |
| `RightViewerPanel.vue` | Replaced `PageImageViewer` with `DocumentViewer` in page mode; tab label "Page View" → "PDF" |

### Phase 2: Display Elements Feature

**Problem**: Documents have rich element data (paragraphs, tables, KV pairs) from Azure Document Intelligence parsing, but no way to visualize them.
**Solution**: Toggle-based annotation overlay on the PDF + element browser panel.

#### New Files

| File | Purpose |
|------|---------|
| `composables/useElementDisplay.ts` | Converts element bounding region polygons to percentage-based annotation rectangles |
| `components/viewer/SplitViewContainer.vue` | Generic resizable split container (horizontal or vertical) with draggable divider |
| `components/viewer/ElementAnnotationOverlay.vue` | Renders color-coded semi-transparent boxes over PDF with tooltips |
| `components/viewer/ElementBrowser.vue` | Grouped element list with "All pages" toggle and collapsible type groups |
| `components/viewer/ElementCard.vue` | Individual element card with auto-scroll-into-view when active |

#### Modified Files

| File | Change |
|------|--------|
| `types/index.ts` | Added `ElementAnnotation` interface, `ELEMENT_TYPE_COLORS`, `ELEMENT_TYPE_BORDER_COLORS`, `ELEMENT_TYPE_LABELS` constants |
| `stores/app.ts` | Added `elementsDisplayActive`, `elementsDisplayExpanded`, `activeElementId` state + `toggleElementsDisplay()`, `toggleElementsExpanded()`, `setActiveElement()` actions |
| `RightViewerPanel.vue` | Layers toggle button, expand/collapse button, SplitViewContainer integration wrapping DocumentViewer + ElementAnnotationOverlay + ElementBrowser |
| `AppShell.vue` | `effectiveViewerWidth` computed for expanded mode (70% viewport), smooth width transition |

## Architecture

### Element Data Flow

```
Document.elements[]                   (from GET /documents/{id})
    ↓
useElementDisplay(elements, pages, currentPage)
    ↓
annotations: ElementAnnotation[]      (percentage-based positions)
    ↓
┌─────────────────────────────┐
│ SplitViewContainer          │
│ ┌─────────────────────────┐ │
│ │ DocumentViewer (PDF)    │ │
│ │ + ElementAnnotationOverlay│ │  ← color-coded boxes, tooltip, click → select
│ └─────────────────────────┘ │
│ ─────── divider ──────────  │  ← draggable
│ ┌─────────────────────────┐ │
│ │ ElementBrowser          │ │  ← grouped cards, click → select + go-to-page
│ │   └ ElementCard[]       │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

### Coordinate Conversion

Elements have bounding regions with polygons in document coordinate space (Azure DI format: inches). The `useElementDisplay` composable converts these to percentage-based positions:

```
polygon [x0,y0, x1,y1, x2,y2, x3,y3]  →  min/max  →  (minX / pageWidth * 100)%
```

This reuses the same pattern as `useHighlights.ts` and `HighlightOverlay.vue`.

### Element Type Colors

| Type | Background | Border |
|------|-----------|--------|
| `paragraph` | `rgba(59, 130, 246, 0.25)` (blue) | `rgba(59, 130, 246, 0.6)` |
| `table` | `rgba(34, 197, 94, 0.25)` (green) | `rgba(34, 197, 94, 0.6)` |
| `key_value_pair` | `rgba(168, 85, 247, 0.25)` (purple) | `rgba(168, 85, 247, 0.6)` |
| `image` | `rgba(234, 179, 8, 0.25)` (yellow) | `rgba(234, 179, 8, 0.6)` |
| `barcode` | `rgba(239, 68, 68, 0.25)` (red) | `rgba(239, 68, 68, 0.6)` |

### Bidirectional Navigation

- **PDF → Browser**: Click annotation box → `appStore.setActiveElement(id)` → ElementCard with matching ID gets colored ring border + `scrollIntoView({ behavior: 'smooth', block: 'nearest' })`
- **Browser → PDF**: Click ElementCard → if different page, `viewer.goToPage(el.page_number)` first → `appStore.setActiveElement(id)` → annotation gets box-shadow highlight, others dim to 0.3 opacity

### Layout Modes

| Mode | Direction | Viewer Width | Split |
|------|-----------|-------------|-------|
| Normal | `horizontal` | Default (420px) | Top: PDF+annotations, Bottom: browser |
| Expanded | `vertical` | `max(current, 70% viewport)` | Left: PDF+annotations, Right: browser |

### State Management

Three new refs in `stores/app.ts`:
- `elementsDisplayActive: boolean` — toggle on/off
- `elementsDisplayExpanded: boolean` — normal vs expanded layout
- `activeElementId: string | null` — selected element for bidirectional highlighting

All three reset on `closeViewer()`. `elementsDisplayExpanded` and `activeElementId` also reset when toggling elements off.

## No Backend Changes Required

Elements are stored inline in the Document MongoDB collection and returned as part of `GET /documents/{id}`. Page dimensions (`width`, `height`, `unit`) are available from `GET /documents/{id}/pages`. No new API endpoints needed.
