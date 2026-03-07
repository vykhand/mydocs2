# Plan: Show parent document subdocuments when clicking a search result

## Context
When searching, the UI returns a list of pages in the middle panel. Clicking a page correctly opens it in the right viewer, but the middle panel stays on search results. The user wants the middle panel to switch to showing the parent document's subdocument list (SubDocumentGrid) — the same view as when clicking a document from the gallery.

## Step 0: Update Spec (before coding)

### `docs/specs/UI.md`

**Line 178** — Search Results Mode "Result actions" row:
- Change from: "Clicking a page result opens the Right Viewer Panel in **page mode** at the matched page with highlights."
- Change to: "Clicking a page result opens the Right Viewer Panel in **page mode** at the matched page with highlights. If the parent document has sub-documents, the middle panel transitions to the **sub-document view** for that document (same as clicking a document card with sub-documents from the gallery). Clicking 'Back' returns to search results."

**Line 231** — Sub-document View section, after "When a document with sub-documents...":
- Add: "The sub-document view can also be entered from search results: clicking a search result fetches the parent document and, if it has sub-documents, transitions the middle panel to this view. The breadcrumb shows 'Search Results / {document name}' instead of 'Documents / {document name}' in this case."

**Line 241** — State section:
- Add `subdocViewFromSearch` (boolean) to the tracked state, indicating whether the view was entered from search results (affects breadcrumb label).

## Step 1: Code Changes

### 1a. `mydocs-ui/src/stores/app.ts` — Track subdoc view origin
- Add `subdocViewFromSearch` ref (boolean, default false)
- Update `enterSubdocView(doc, fromSearch = false)` to set it
- Update `exitSubdocView()` to clear it
- Export the new ref

### 1b. `mydocs-ui/src/components/search/PageResultCard.vue` — Fetch doc on click
- Import `getDocument` from `@/api/documents`
- Make `handleClick` async
- After opening viewer (immediate, no wait), fetch parent document
- If doc has subdocuments, call `appStore.enterSubdocView(doc, true)`
- Guard against stale state: skip if `viewerDocumentId` changed during fetch

### 1c. `mydocs-ui/src/components/search/SearchResultCard.vue` — Same treatment
- Import `getDocument`, `useRoute`
- Extract inline `@click` into async `handleClick` method
- Call `appStore.openViewer(...)` + `router.push(...)` immediately
- Then fetch document and enter subdoc view (same logic as PageResultCard)
- Update both `@click` handlers (card and Eye button) to use the method

### 1d. `mydocs-ui/src/components/documents/SubDocumentGrid.vue` — Dynamic breadcrumb
- Change breadcrumb label from hardcoded "Documents" to:
  `appStore.subdocViewFromSearch ? 'Search Results' : 'Documents'`
- Update back button title similarly

### 1e. `mydocs-ui/src/views/GalleryView.vue` — Preserve highlight on subdoc click
- In `handleOpenSubdoc`, pass `route.query.q` as highlight query when `subdocViewFromSearch` is true

## Step 2: Update Docs (after coding)

### `docs/UI.md`

**Line 181** — Search results row:
- Add note: "Clicking a result also shows the parent document's sub-documents in the middle panel (if any)."

**Line 677** — User story US-SRCH-5:
- Update description to: "As a user, clicking a search result opens the viewer at the matched page with highlights, and shows the parent document's sub-documents in the middle panel."

**Add new user story US-SRCH-9:**
- "As a user, when I click a search result for a document with sub-documents, the middle panel shows the sub-document list with a 'Search Results' breadcrumb. Clicking 'Back' returns to search results."

## Edge cases
- **No subdocuments**: Skip `enterSubdocView` — middle panel stays on search results
- **Rapid clicks**: Guard (`viewerDocumentId !== docId`) prevents stale fetch from entering wrong subdoc view
- **Back button**: `exitSubdocView()` clears state → falls through to search results (URL still has `?q=`)

## Verification
1. Search for something, click a result in grid mode → middle panel shows SubDocumentGrid, right panel shows page
2. Breadcrumb says "Search Results / {filename}"
3. Click "back" → returns to search results
4. Repeat in list mode (SearchResultCard)
5. Test document with no subdocuments → middle panel stays on search results
6. Click different subdocuments in the grid → right viewer updates correctly
7. Run frontend lint: `cd mydocs-ui && npm run lint`
