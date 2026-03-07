# Brainstorming: Multitenant System with Client-Side Encryption

**Date**: 2026-03-07
**Status**: Brainstorming / Hypothetical
**Question**: How would we make MyDocs multitenant with end-to-end encryption where the server cannot see customer data?

---

## Current State Summary

Today MyDocs is **single-tenant with no encryption at the application level**:

- **Auth**: Azure Entra ID JWT tokens, but no tenant isolation — all authenticated users see all data
- **Data models**: No `tenant_id` or `org_id` on any collection (documents, pages, cases)
- **AI processing**: Server sends plaintext document content to Azure Document Intelligence (parsing) and Azure OpenAI (extraction, embeddings)
- **Search**: Full-text and vector indexes operate on plaintext content in MongoDB
- **Storage**: Files stored in local filesystem or Azure Blob — no application-level encryption at rest
- **Frontend**: Receives plaintext content (text, markdown, HTML) from the API

This means the server has **full access to all customer data** at every stage.

---

## The Core Tension

**Client-side encryption** (zero-knowledge) and **server-side AI processing** are fundamentally at odds:

| Capability | Requires Server to See Content? |
|---|---|
| Azure Document Intelligence (PDF parsing) | Yes — sends raw PDF bytes |
| LLM extraction (GPT-4) | Yes — sends document text in prompts |
| Vector embedding generation | Yes — sends text to embedding model |
| Full-text search indexing | Yes — indexes plaintext |
| Vector search | Yes — indexes embedding vectors |
| Thumbnail / PDF rendering | Yes (server-side) or No (client-side) |

If the server literally cannot decrypt any data, **all AI features break**. So we need to consider a spectrum of approaches, from pragmatic to aspirational.

---

## Approach 1: Tenant Isolation First (No E2E Encryption)

**Philosophy**: Separate tenants logically; encrypt at rest with platform-level keys. Server still processes data but tenants can't see each other's data.

### Changes Required

**Data model**:
- Add `tenant_id: str` to `Document`, `DocumentPage`, `Case`, `FieldResultRecord`
- Derive `tenant_id` from JWT claims (e.g., `tid` claim in Entra ID tokens = Azure AD tenant ID)
- Add compound indexes: `(tenant_id, ...)` on all query paths

**Query layer**:
- Create a `TenantContext` middleware that extracts `tenant_id` from every request
- Inject `tenant_id` filter into every MongoDB query automatically (repository pattern or ODM middleware)
- Fail-closed: if `tenant_id` is missing, reject the query

**Storage isolation**:
- Azure Blob: prefix all paths with `{tenant_id}/` (e.g., `az://container/{tenant_id}/{doc_id}.pdf`)
- MongoDB: shared collections with `tenant_id` field (simplest) or database-per-tenant (strongest)

**Search isolation**:
- Add `tenant_id` as a pre-filter to all Atlas Search and Vector Search queries
- Ensure search indexes include `tenant_id` as a filterable field

**API changes**:
- No API contract changes needed — tenant context is implicit from auth token
- Admin API could add cross-tenant query capability (with elevated permissions)

### Pros
- Straightforward to implement
- All AI features continue working
- Platform-level encryption at rest (MongoDB encryption, Azure Blob encryption) handles compliance checkboxes
- Standard SaaS pattern

### Cons
- Server operator can still see all data
- Compromise of the server = compromise of all tenants
- Does not meet "server can't see customer data" requirement

### Effort: Medium (2-4 weeks)

---

## Approach 2: Tenant-Managed Keys (Bring Your Own Key)

**Philosophy**: Each tenant provides their own encryption key. Data encrypted at rest with tenant's key. Server decrypts only during processing, in-memory.

### Architecture

```
Client (Tenant A)
  │
  ├── Uploads file ──────────────────────► Server
  │                                          │
  │                                          ├── Encrypts file with Tenant A's key
  │                                          ├── Stores encrypted blob in Azure Blob
  │                                          │
  │   (Processing request)                   │
  │ ─────────────────────────────────────►   ├── Fetches Tenant A's key from Key Vault
  │                                          ├── Decrypts in memory
  │                                          ├── Sends to Azure DI / OpenAI
  │                                          ├── Encrypts results
  │                                          ├── Stores encrypted results
  │                                          └── Returns encrypted response
  │                                                │
  │   ◄─────────────────────────────────────────────┘
  └── Decrypts response with tenant key
```

### Key Management Options

**Option A: Azure Key Vault per tenant**
- Each tenant has their own Key Vault (or key within shared vault)
- Server accesses key via managed identity + RBAC
- Tenant can rotate/revoke keys
- Tenant can audit key usage via Key Vault logs

**Option B: Client-held key, envelope encryption**
- Client holds master key (never leaves client)
- Each document encrypted with a random Data Encryption Key (DEK)
- DEK encrypted with tenant's master key (becomes "wrapped DEK")
- Wrapped DEK stored alongside encrypted document
- For processing: client sends unwrapped DEK for specific documents (session-scoped)

**Option C: Hardware Security Module (HSM)**
- Tenant's key stored in dedicated HSM partition
- Server requests HSM to decrypt, but never sees the raw key
- Strongest key protection, most expensive

### Changes Required

**Encryption service**:
- New `EncryptionService` that wraps all storage read/write operations
- Per-tenant key resolution
- Envelope encryption: random DEK per document, wrapped with tenant's KEK

**Storage layer**:
- All blobs stored encrypted
- Metadata sidecar includes `wrapped_dek`, `key_id`, `encryption_algorithm`

**MongoDB**:
- `Document.content`, `DocumentPage.content_*` stored encrypted
- Or use MongoDB Client-Side Field Level Encryption (CSFLE) — MongoDB native feature
  - Automatically encrypts/decrypts specific fields
  - Uses AWS KMS, Azure Key Vault, or local key
  - Supports deterministic encryption (allows equality queries) and random encryption

**Search**:
- Encrypted content can't be full-text indexed — need to decrypt, index, and protect the index
- Option: maintain a separate search index per tenant in a secured context
- Or: accept that search indexes contain plaintext but are tenant-isolated (weaker guarantee)

**Processing pipeline**:
- Decrypt → process → re-encrypt pattern for DI and LLM calls
- All plaintext exists only in memory during processing
- Clear memory after processing (best-effort — hard to guarantee in managed runtimes)

### Pros
- Tenant controls their key — can revoke access
- Data at rest is always encrypted with tenant-specific keys
- Audit trail via Key Vault logs
- MongoDB CSFLE is a well-supported native feature
- All AI features still work

### Cons
- Server still sees plaintext during processing (in memory)
- Compromised server = temporary access to data being processed
- Search indexes are a weak point (contain decrypted content)
- Key management complexity
- Performance overhead from encrypt/decrypt cycles

### Effort: Large (4-8 weeks)

---

## Approach 3: Confidential Computing (TEE-Based)

**Philosophy**: Use Trusted Execution Environments (hardware enclaves) so the server processes data in a secure enclave that even the server operator cannot inspect.

### How It Works

```
Client
  │
  ├── Attests enclave (verifies it's genuine, unmodified code)
  ├── Establishes encrypted channel to enclave
  ├── Sends encrypted document + key
  │
  ▼
┌──────────────────────────────────────┐
│  Azure Confidential Computing        │
│  (SGX / SEV-SNP Enclave)            │
│                                      │
│  ┌─────────────────────────────┐    │
│  │  Enclave (trusted code)     │    │
│  │                             │    │
│  │  - Decrypts document        │    │
│  │  - Calls Azure DI           │◄───┤── Problem: DI is external
│  │  - Calls Azure OpenAI       │◄───┤── Problem: OpenAI is external
│  │  - Generates embeddings     │    │
│  │  - Encrypts results         │    │
│  │  - Returns to client        │    │
│  └─────────────────────────────┘    │
│                                      │
│  Host OS / Hypervisor: CANNOT see   │
│  enclave memory                     │
└──────────────────────────────────────┘
```

### The External Service Problem

Even inside a TEE, we still need to call **external services**:
- Azure Document Intelligence — receives raw PDF bytes over HTTPS
- Azure OpenAI — receives plaintext prompts over HTTPS

These services run outside the enclave. Microsoft operates them. So the zero-knowledge guarantee is actually: "trust Microsoft's services but not your own server operator."

**Mitigation**: Azure Confidential AI (preview) is extending TEE guarantees to some Azure AI services, but it's not yet generally available for DI or OpenAI.

### Changes Required

**Infrastructure**:
- Deploy backend on Azure Confidential VMs (DCsv3 series with SGX or DCasv5 with SEV-SNP)
- Or use Azure Confidential Containers (ACI with SEV-SNP)
- Implement remote attestation flow

**Application**:
- Attestation endpoint: client verifies enclave before sending data
- Key exchange: client and enclave establish session keys via attested TLS
- All document processing happens inside enclave boundary
- Encrypted storage: enclave seals data with enclave-specific keys

**Client**:
- Attestation verification library in frontend (or via a trusted proxy)
- Key negotiation protocol

### Pros
- Strongest server-side guarantee: even the operator can't inspect memory
- Hardware-backed security (CPU-level isolation)
- All AI features work (within enclave)
- Verifiable via remote attestation

### Cons
- Still trusts Azure's external AI services (DI, OpenAI)
- Complex infrastructure setup
- Performance overhead from enclave transitions
- Limited enclave memory (SGX: ~256MB usable; SEV-SNP: full VM)
- Vendor lock-in to Azure Confidential Computing
- Attestation flow adds client complexity
- Early/evolving ecosystem

### Effort: Very Large (2-4 months)

---

## Approach 4: Client-Side Processing (True Zero-Knowledge)

**Philosophy**: Move all AI processing to the client. Server is a dumb encrypted storage backend. This is the only approach that truly achieves "server cannot see data."

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client (Browser or Desktop App)                        │
│                                                          │
│  1. User selects PDF                                    │
│  2. Client parses PDF locally (PDF.js or local DI)      │
│  3. Client runs local LLM for extraction                │
│  4. Client generates embeddings (local model)           │
│  5. Client builds search index locally                  │
│  6. Client encrypts everything (AES-256-GCM)           │
│  7. Client uploads encrypted blobs to server            │
│                                                          │
│  Search:                                                │
│  - Download encrypted index → decrypt → search locally  │
│  - Or: use Searchable Symmetric Encryption (SSE)        │
│                                                          │
│  View:                                                  │
│  - Download encrypted doc → decrypt → render locally    │
└─────────────┬───────────────────────────────────────────┘
              │
              │ Only encrypted blobs
              ▼
┌─────────────────────────────────────────────────────────┐
│  Server (Dumb Encrypted Storage)                        │
│                                                          │
│  - Stores encrypted blobs (documents, pages, metadata)  │
│  - Enforces tenant isolation (by auth token)            │
│  - Cannot decrypt anything                              │
│  - Provides sync/backup                                 │
│  - Manages user auth (no access to content)             │
└─────────────────────────────────────────────────────────┘
```

### Client-Side Components Needed

**PDF Parsing** (replacing Azure Document Intelligence):
- Use PDF.js for text extraction (decent for digital PDFs)
- For scanned PDFs: Tesseract.js (OCR in browser via WebAssembly)
- Quality will be lower than Azure DI for complex layouts, tables, forms
- Alternative: desktop companion app with better local parsing

**LLM Processing** (replacing Azure OpenAI):
- WebLLM / llama.cpp via WebAssembly for in-browser inference
- Or: desktop app with local model (Ollama, llama.cpp)
- Quality tradeoff: local models (7B-13B) vs. GPT-4 class models
- Extraction accuracy will be significantly lower

**Embeddings** (replacing text-embedding-3-large):
- Run a small embedding model locally (e.g., all-MiniLM-L6-v2 via ONNX.js)
- 384 dimensions vs. 3072 — less accurate vector search
- Alternative: client sends text to a trusted embedding service (weakens zero-knowledge)

**Search**:
- **Option A**: Download all encrypted page data, decrypt in browser, search locally
  - Works for small collections; doesn't scale beyond ~10K pages
- **Option B**: Searchable Symmetric Encryption (SSE)
  - Client builds encrypted index tokens (one per keyword)
  - Server stores and matches encrypted tokens without learning content
  - Supports equality search, not fuzzy/semantic
- **Option C**: Store encrypted HNSW index on server, download and decrypt for vector search
  - Feasible for moderate-sized collections

### Encryption Scheme

```
Master Key (derived from user password via Argon2id)
    │
    ├── Key Encryption Key (KEK)
    │       │
    │       ├── Document DEK 1 (random AES-256 key)
    │       │       └── Encrypts: PDF bytes, parsed content, elements
    │       ├── Document DEK 2
    │       │       └── ...
    │       └── Index DEK
    │               └── Encrypts: search index, embeddings
    │
    └── Auth Key (separate derivation)
            └── Used for server authentication (not encryption)
```

- Each document gets a random DEK (Data Encryption Key)
- DEKs wrapped with KEK derived from user's master key
- Wrapped DEKs stored on server alongside encrypted data
- Key rotation: re-wrap DEKs with new KEK (don't re-encrypt all data)

### Sharing & Collaboration

This is where zero-knowledge gets hard:

- **Sharing with another user**: Must re-encrypt the document DEK with the recipient's public key
- Requires a public key infrastructure (each user has a key pair)
- Server can store encrypted DEKs per user, but can't facilitate sharing of content
- **Team/org access**: Use a group key that's shared among team members
  - Group key encrypted per-member with their public key
  - Adding/removing members requires re-wrapping group key

### Pros
- True zero-knowledge: server never sees any content
- Maximum privacy guarantee
- Resistant to server compromise (attacker gets only encrypted blobs)
- No trust required in server operator

### Cons
- **Dramatically reduced AI quality**: Local models << GPT-4, local parsing << Azure DI
- **Heavy client requirements**: GPU recommended, significant RAM, slow processing
- **Doesn't scale for search**: Full-text and vector search on large collections requires downloading and decrypting data
- **Complex key management**: Lost password = lost data (no recovery possible)
- **No mobile/lightweight client**: Browser processing is limited
- **Collaboration is hard**: Key sharing, access revocation, group keys add significant complexity
- **Fundamentally different product**: More like an encrypted file manager than an AI document system

### Effort: Very Large (3-6 months), and results in a different product

---

## Approach 5: Hybrid — Encrypted Storage + Opt-In Server Processing

**Philosophy**: Data is encrypted by default. For AI features, the user explicitly opts in to server-side processing for specific documents, understanding the trust tradeoff.

### Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Client                                                       │
│                                                                │
│  Mode A: "Vault Mode" (default)                               │
│  ├── All data encrypted client-side                           │
│  ├── Server stores encrypted blobs                            │
│  ├── Basic features: view, organize, tag, manual search       │
│  └── No AI processing                                         │
│                                                                │
│  Mode B: "AI Mode" (opt-in per document/case)                 │
│  ├── User explicitly unlocks document for server processing   │
│  ├── Client sends DEK to server (session-scoped or persisted) │
│  ├── Server decrypts, runs AI pipeline, re-encrypts results   │
│  ├── Server discards DEK after processing (or tenant revokes) │
│  └── Full AI features: parsing, extraction, search, RAG       │
│                                                                │
│  User sees clear UI indication:                               │
│  🔒 "Encrypted — only you can access"                         │
│  🤖 "AI-enabled — server processes this document"             │
└───────────────────────────────────────────────────────────────┘
```

### How "Unlocking" Works

1. User clicks "Enable AI Processing" on a document or case
2. Client sends the document's DEK to server, encrypted with a session key
3. Server stores DEK in a short-lived secure store (e.g., in-memory cache, or tenant Key Vault)
4. Server decrypts document → runs full pipeline (DI, LLM, embeddings) → encrypts results
5. Results stored encrypted; DEK retained only if user chooses "keep AI features active"
6. User can "re-lock" at any time: server deletes DEK, AI features deactivate for that document

### Changes Required

**Client**:
- Encryption/decryption library (Web Crypto API)
- Key derivation from user password
- Per-document key management
- UI for vault/AI mode toggle

**Server**:
- Encrypted storage layer (blobs + MongoDB CSFLE)
- DEK escrow service (temporary key storage for AI processing)
- Modified pipeline: decrypt → process → encrypt
- Tenant isolation (Approach 1 as foundation)

**Data model additions**:
```
Document:
  + tenant_id: str
  + encryption_status: "encrypted" | "unlocked_for_ai" | "plaintext_legacy"
  + wrapped_dek: str (DEK encrypted with user's KEK)
  + key_id: str (which KEK version wrapped this DEK)
```

### Pros
- User has explicit control over trust boundary
- Encrypted by default — strong baseline privacy
- Full AI features available when user opts in
- Transparent about what the server can/cannot see
- Incremental: can launch with Approach 1 (tenant isolation) and add encryption later
- Best of both worlds for users who want both privacy and AI

### Cons
- Two code paths (encrypted vs. AI-enabled) increases complexity
- When AI mode is on, same exposure as Approach 2
- UX complexity: users must understand the tradeoff
- Key management still complex (password recovery, sharing)

### Effort: Large (6-10 weeks), built on top of Approach 1

---

## Approach 6: Homomorphic Encryption (Future / Research)

**Philosophy**: Compute on encrypted data without decrypting it. The holy grail.

### State of the Art (2026)

- **Fully Homomorphic Encryption (FHE)**: Can compute arbitrary functions on encrypted data
- Libraries: Microsoft SEAL, Google FHE, Zama Concrete ML
- **Reality check**:
  - FHE for neural network inference is ~1000-10000x slower than plaintext
  - Embedding generation on encrypted text: theoretically possible, practically very slow
  - LLM inference on encrypted input: not yet feasible at scale
  - Full-text search on encrypted data: possible with specialized schemes but limited

### Practical FHE Applications Today

- Simple aggregations on encrypted numbers (e.g., sum, average)
- Encrypted keyword matching (very specific patterns)
- Encrypted classification with small models

### Not Yet Practical For

- Document parsing (complex vision + layout model)
- LLM-based extraction (transformer inference)
- Embedding generation with large models
- Semantic/vector search at scale

### Verdict

FHE is not ready for our use case. Revisit in 2-3 years as the field matures. Worth tracking:
- Zama's Concrete ML for encrypted ML inference
- Microsoft SEAL improvements
- Hardware FHE accelerators (Intel, DARPA programs)

---

## Recommended Phased Strategy

### Phase 1: Tenant Isolation (Foundation)
**Priority: High | Effort: 2-4 weeks**

- Add `tenant_id` to all data models
- Inject tenant filter into all queries
- Isolate storage paths by tenant
- This is prerequisite for everything else

### Phase 2: Tenant-Managed Keys + MongoDB CSFLE
**Priority: Medium | Effort: 4-6 weeks (after Phase 1)**

- Implement per-tenant encryption keys via Azure Key Vault
- Use MongoDB CSFLE for sensitive fields (content, elements, extraction results)
- Encrypt blobs in Azure Storage with tenant-specific keys
- All AI processing continues to work (server decrypts in memory)
- Tenant can revoke key to "brick" their data

### Phase 3: Hybrid Vault/AI Mode (Optional, for high-security customers)
**Priority: Low | Effort: 6-8 weeks (after Phase 2)**

- Client-side encryption for documents in "vault mode"
- Opt-in server processing for AI features
- Per-document encryption status tracking
- Key derivation from user credentials

### Phase 4: Confidential Computing (Future)
**Priority: Research | Effort: 2-4 months**

- Evaluate Azure Confidential AI maturity
- If available: run AI pipeline in TEE enclaves
- Combine with Phase 2 keys for defense in depth

---

## Key Decisions to Make

1. **What trust model do we promise customers?**
   - "We isolate your data from other tenants" (Phase 1) — standard SaaS
   - "We encrypt your data and you control the key" (Phase 2) — enhanced SaaS
   - "We literally cannot see your data" (Phase 3-4) — zero-knowledge
   - Each level trades off AI capability for privacy

2. **Is AI quality or privacy the higher priority?**
   - If AI quality: Phase 1-2 (server processes plaintext, strong isolation)
   - If privacy: Phase 3-4 (reduced AI capability, client-side processing)
   - Most enterprise customers want Phase 2 (encryption at rest + key control)

3. **Database isolation model?**
   - Shared collections with `tenant_id` (simplest, cheapest)
   - Database-per-tenant (strongest isolation, higher cost)
   - Hybrid: shared for small tenants, dedicated for enterprise

4. **Search in an encrypted world?**
   - If server can decrypt: standard full-text + vector search (Phase 1-2)
   - If server cannot decrypt: client-side search or SSE (Phase 3-4)
   - This is the hardest problem — no good solution exists for encrypted semantic search

5. **Key recovery?**
   - Password-derived keys: lost password = lost data
   - Key Vault managed: server-accessible (weaker guarantee but recoverable)
   - Escrow: trusted third party holds recovery key
   - This decision shapes the entire UX

---

## Impact Analysis by Component

| Component | Phase 1 (Tenant Isolation) | Phase 2 (BYOK) | Phase 3 (Client Encrypt) |
|---|---|---|---|
| **Data models** | Add `tenant_id` everywhere | Add `wrapped_dek`, `key_id` | Add `encryption_status` |
| **Auth middleware** | Extract `tenant_id` from JWT | Key Vault integration | Client key exchange |
| **MongoDB queries** | Add tenant filter to all queries | Enable CSFLE | Encrypted field handling |
| **Storage (Blob)** | Prefix paths with tenant_id | Encrypt blobs with tenant key | Client-encrypted uploads |
| **Parsing (DI)** | No change | Decrypt → parse → encrypt | Client-side parsing |
| **Extraction (LLM)** | No change | Decrypt → extract → encrypt | Client-side LLM or opt-in |
| **Search (FT)** | Add tenant filter | No change (decrypted index) | Client-side or SSE |
| **Search (Vector)** | Add tenant filter | No change (decrypted embeddings) | Client-side vector search |
| **Frontend** | No change | Key management UI | Encryption/decryption lib |
| **API contract** | Implicit (from token) | Key management endpoints | Encrypted payload handling |

---

## References & Prior Art

- **Proton Mail/Drive**: True zero-knowledge, but no server-side AI features
- **Tresorit**: Client-side encryption for file storage, limited server processing
- **Virtru**: Email encryption with key management — hybrid model similar to Approach 5
- **CipherStash**: Searchable encryption for databases — worth investigating for Phase 3
- **MongoDB CSFLE**: Native client-side field-level encryption — natural fit for Phase 2
- **Azure Confidential Computing**: TEE-based approach — maturing but not yet ready for full AI pipeline
- **Signal Protocol**: End-to-end encryption with perfect forward secrecy — inspiration for key exchange
