# Brainstorming: Consumer Product with EU Compliance & User Trust

**Date**: 2026-03-07
**Status**: Brainstorming / Hypothetical
**Builds on**: [20260307_01_multitenant_e2e_encryption.md](./20260307_01_multitenant_e2e_encryption.md)
**Question**: How to build a consumer-facing iOS/Android/Web app (NotebookLM-like for documents) that complies with EU regulations and earns user trust?

---

## Product Vision

A consumer "AI document notebook" — users upload personal documents (contracts, tax forms, medical records, receipts, legal papers, study materials) and the app helps them understand, search, extract info, and ask questions about their documents. Think NotebookLM, but focused on real-world documents rather than research papers.

**Key differentiator**: "Your documents stay yours. EU-hosted, encrypted, and transparent."

---

## Part 1: EU Regulatory Landscape

### 1.1 GDPR (General Data Protection Regulation)

The non-negotiable foundation. Key requirements:

| GDPR Principle | What It Means for Us | Implementation |
|---|---|---|
| **Lawful basis** | Need a legal reason to process data | Consent (for AI features) + Contract (for storage) |
| **Purpose limitation** | Only use data for stated purposes | No training on user data, no secondary use |
| **Data minimization** | Collect only what's needed | Don't store more than necessary, auto-delete parsed intermediates |
| **Storage limitation** | Don't keep data forever | User-controlled retention, right to deletion |
| **Integrity & confidentiality** | Protect data technically | Encryption at rest + in transit, access controls |
| **Accountability** | Prove you're compliant | Audit logs, DPIAs, documented policies |
| **Data subject rights** | Users can access, delete, port their data | Export all data, delete account, GDPR dashboard |

**Specific GDPR obligations**:

- **Privacy by Design and by Default** (Art. 25): Encryption, minimal data collection, privacy settings on by default
- **Data Protection Impact Assessment** (Art. 35): Required because we process sensitive personal documents at scale
- **Data Processing Agreement** (Art. 28): Needed with every sub-processor (Azure, OpenAI, MongoDB Atlas)
- **Records of Processing** (Art. 30): Maintain a register of all processing activities
- **Data Breach Notification** (Art. 33-34): 72-hour notification to DPA, inform users if high risk
- **Data Protection Officer** (Art. 37): Likely required if processing personal data at scale
- **Cross-border transfers** (Art. 44-49): User data must stay in EU or have adequate safeguards (see 1.4)

### 1.2 EU AI Act

Entered into force August 2024, phased enforcement through 2026-2027.

**Classification of our system**:
- We are an **AI system** under the Act (uses ML models for document understanding)
- Risk category: Likely **limited risk** (not high-risk unless used for legal/medical decisions)
- If users use it for legal document analysis → could be **high-risk** (AI systems in administration of justice)

**Obligations for limited-risk AI**:
- **Transparency**: Users must know they're interacting with AI
- **AI-generated content marking**: Clearly label AI outputs (extractions, summaries, answers)
- **Logging**: Keep logs of AI system operation for supervisory authorities

**Obligations if high-risk** (legal/medical document use):
- Risk management system
- Data governance requirements
- Technical documentation
- Record-keeping and logging
- Transparency and provision of information to users
- Human oversight capabilities
- Accuracy, robustness, and cybersecurity requirements
- Conformity assessment before market placement

**Practical approach**: Design for high-risk compliance from day one (it's mostly good engineering practice), but market as limited-risk unless the use case is explicitly high-risk.

### 1.3 Digital Services Act (DSA) & Digital Markets Act (DMA)

Less directly relevant unless we reach "very large platform" status (45M+ EU users), but:
- **Transparency in content moderation**: If we filter/flag documents, explain why
- **Terms of Service**: Must be clear and accessible

### 1.4 Data Residency & Sovereignty

**The EU data residency requirement is the single biggest architectural driver.**

Options:

**Option A: EU-only infrastructure**
- All servers, storage, and AI processing in EU data centers
- Azure: West Europe (Netherlands), North Europe (Ireland), France Central, Germany West Central, Sweden Central
- MongoDB Atlas: Available in EU Azure/AWS regions
- Azure OpenAI: Available in Sweden Central, France Central
- Azure Document Intelligence: Available in West Europe, North Europe, France Central

**Option B: EU hosting with DPA-covered sub-processors**
- Primary infrastructure in EU
- Azure OpenAI API calls may route through Microsoft's global infrastructure
- Requires Data Processing Addendum with Microsoft confirming EU data processing
- Microsoft's EU Data Boundary commitment (effective Jan 2024) helps

**Option C: Sovereign cloud**
- Use a European sovereign cloud provider (OVHcloud, Scaleway, IONOS, or Azure EU sovereign regions)
- Most restrictive, most compliant
- Limits cloud service options

**Recommendation**: Option A with Microsoft's EU Data Boundary. Azure has strong EU data residency commitments and all needed services are available in EU regions.

### 1.5 ePrivacy Directive (& upcoming ePrivacy Regulation)

- Governs cookies and electronic communications
- For our app: minimal cookie usage, no tracking pixels, no third-party analytics that transfer data outside EU
- Use privacy-respecting analytics (Plausible, Matomo self-hosted) instead of Google Analytics

### 1.6 Consumer Protection (EU Consumer Rights Directive)

For a paid consumer product:
- 14-day withdrawal right for online purchases
- Clear pricing, no hidden costs
- Accessible complaint handling
- If subscription: easy cancellation (recent "click to cancel" rulings)

---

## Part 2: Trust Architecture

Trust is built through three pillars: **transparency**, **control**, and **verification**.

### 2.1 Transparency

**What the user should always know**:

1. **Where their data is stored**: "Your documents are stored in [EU region], encrypted at rest."
2. **What AI processing happens**: "When you ask a question, the relevant pages are sent to [specific AI service] for analysis."
3. **Who can access their data**: "Only you. Our engineers cannot read your documents." (must be true!)
4. **What sub-processors are involved**: Public sub-processor list (required by GDPR anyway)
5. **What happens on deletion**: "When you delete a document, all copies including AI-generated data are permanently removed within 30 days."

**Implementation**:
- **Trust Dashboard** in app: real-time view of where data is, what's been processed, who accessed it
- **Processing receipts**: After every AI operation, show the user what data was sent where
- **Open-source client**: Publish the client-side encryption and key management code (verifiable)
- **Public security audit**: Annual third-party security audit, published results

### 2.2 User Control

**Data sovereignty features**:

| Feature | Description |
|---|---|
| **Granular consent** | Per-feature consent: "Allow AI summaries? Allow search indexing? Allow cross-document Q&A?" |
| **Data export** | One-click export of all data (GDPR portability right) in standard formats (PDF + JSON metadata) |
| **Account deletion** | Immediate soft-delete, 30-day hard purge, cryptographic proof of deletion |
| **Processing opt-out** | Disable AI features entirely, use as encrypted document vault only |
| **Retention controls** | Auto-delete documents after N days, or keep forever |
| **Sharing controls** | Share specific documents with specific people, revocable |
| **AI training opt-out** | "We never train on your data" (make it policy, not opt-out) |

### 2.3 Verification

Users should be able to verify claims, not just trust them:

- **Open-source client code**: Users/researchers can verify encryption implementation
- **Reproducible builds**: Published app matches source code (difficult but valuable)
- **Third-party audits**: SOC 2 Type II, ISO 27001, annual penetration test
- **Bug bounty program**: Incentivize security researchers
- **Canary / warrant canary**: Transparency about government data requests
- **Encryption verification**: Technical users can verify their data is actually encrypted at rest

---

## Part 3: Recommended Architecture for Consumer Product

### 3.1 The "Transparent Trust" Model

This is a pragmatic architecture that maximizes AI quality while being honest and compliant about the trust boundary. It corresponds to a refined version of Approach 2 + elements of Approach 5 from the previous brainstorming.

```
┌───────────────────────────────────────────────────────────────────┐
│  Client Apps (iOS / Android / Web)                                │
│                                                                    │
│  ┌──────────────────────────┐  ┌───────────────────────────────┐ │
│  │  Document Vault           │  │  AI Notebook                  │ │
│  │                           │  │                               │ │
│  │  - Upload / scan docs     │  │  - Ask questions about docs   │ │
│  │  - Organize into folders  │  │  - Get summaries              │ │
│  │  - View / annotate        │  │  - Extract key information    │ │
│  │  - Client-side encrypt    │  │  - Cross-document search      │ │
│  │  - Offline access         │  │  - AI-generated insights      │ │
│  │                           │  │                               │ │
│  │  Always works.            │  │  Requires consent for server  │ │
│  │  No server processing.    │  │  processing. Clear indication │ │
│  │                           │  │  of what data is sent where.  │ │
│  └──────────────────────────┘  └───────────────────────────────┘ │
│                                                                    │
│  Encryption layer (Web Crypto API / iOS CryptoKit / Android JCA)  │
│  - Per-document AES-256-GCM encryption                            │
│  - Key derived from user credentials (Argon2id)                   │
│  - Encrypted at rest on device AND on server                      │
└──────────────┬────────────────────────────┬───────────────────────┘
               │                            │
               │  Encrypted blobs           │  Consent-gated
               │  (always)                  │  AI requests
               ▼                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  Backend (EU-hosted, FastAPI)                                     │
│                                                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────────┐ │
│  │  Storage Layer  │  │  Auth & IAM    │  │  AI Pipeline        │ │
│  │                 │  │                │  │  (consent-gated)    │ │
│  │  Encrypted      │  │  Auth0 / Entra │  │                     │ │
│  │  blob store     │  │  Per-user      │  │  Decrypt (in-mem)   │ │
│  │  (Azure Blob,   │  │  isolation     │  │  → Parse (Azure DI) │ │
│  │   EU region)    │  │  RBAC          │  │  → Extract (LLM)    │ │
│  │                 │  │                │  │  → Embed (Azure OAI) │ │
│  │  Encrypted      │  │  Rate limiting │  │  → Re-encrypt       │ │
│  │  MongoDB        │  │  Abuse detect  │  │  → Store results    │ │
│  │  (Atlas, EU)    │  │                │  │                     │ │
│  └────────────────┘  └────────────────┘  └─────────────────────┘ │
│                                                                    │
│  All infrastructure in EU (Azure West Europe / Sweden Central)    │
│  Sub-processors: Azure DI (EU), Azure OpenAI (EU), Atlas (EU)    │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 User Account & Identity

**Consumer auth** (not enterprise Entra ID):

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **Auth0** | Full-featured, social login, MFA, EU hosting | Cost at scale ($), vendor dependency | Good for launch |
| **Firebase Auth** | Free tier, Google ecosystem | Data may leave EU, Google dependency | Avoid (EU concerns) |
| **Supabase Auth** | Open-source, self-hostable, EU-deployable | Smaller ecosystem | Good alternative |
| **Custom (Passkeys + email)** | Full control, no vendor | Build cost, security responsibility | Long-term goal |
| **Apple/Google Sign-In** | Frictionless onboarding | Platform dependency, less control | Offer as option |

**Recommended**: Auth0 (EU deployment) at launch, with Apple/Google social login options. Migrate to Passkeys (WebAuthn) as the primary method over time — passwordless, phishing-resistant, and aligns with the "modern, trustworthy" brand.

**Key derivation for encryption**:
- User's encryption key must be separate from auth — so even if auth provider is compromised, data is safe
- At signup: generate random Master Key → encrypt with user-chosen password (Argon2id KDF) → store encrypted Master Key on server
- At login: auth via Auth0 → then user enters encryption password to unlock Master Key client-side
- OR: derive encryption key from auth credentials (simpler UX, weaker separation)
- OR: use device-bound keys via Secure Enclave (iOS) / StrongBox (Android) — best UX for mobile

### 3.3 Data Model Changes (from current MyDocs)

```
User:
  id: str (UUID)
  email: str
  display_name: str
  auth_provider_id: str (Auth0 sub)
  encryption_public_key: str (X25519, for sharing)
  wrapped_master_key: bytes (Master Key encrypted with password-derived key)
  kdf_params: dict (Argon2id params: salt, memory, iterations)
  subscription_tier: "free" | "pro" | "team"
  consent_flags:
    ai_processing: bool (GDPR consent for AI features)
    analytics: bool (anonymized usage analytics)
  data_region: "eu-west" | "eu-north" (user's chosen data region)
  created_at: datetime
  deleted_at: Optional[datetime] (soft delete)

Document:
  id: str
  user_id: str (owner — replaces tenant_id for consumer)
  folder_id: Optional[str]

  # Encrypted fields (server cannot read without user's DEK)
  encrypted_content: bytes (AES-256-GCM encrypted parsed text)
  encrypted_metadata: bytes (encrypted original filename, tags, notes)

  # Plaintext metadata (needed for server-side operations)
  file_type: str (pdf, docx, jpg — needed for processing routing)
  file_size_bytes: int (needed for quota enforcement)
  created_at: datetime
  modified_at: datetime

  # Encryption metadata
  wrapped_dek: bytes (document DEK wrapped with user's KEK)
  key_version: int
  encryption_algo: str ("AES-256-GCM")

  # AI processing state (only populated if user consented)
  ai_status: "none" | "processing" | "ready" | "failed"
  ai_consent_timestamp: Optional[datetime] (when user consented to AI for this doc)

DocumentPage:
  id: str
  document_id: str
  user_id: str
  page_number: int
  encrypted_content: bytes
  encrypted_content_markdown: bytes
  encrypted_embedding: bytes (encrypted vector — decrypted for search)

Folder:
  id: str
  user_id: str
  name: str (encrypted client-side? or plaintext for server-side listing)
  parent_folder_id: Optional[str]

SharedAccess:
  id: str
  document_id: str
  owner_user_id: str
  recipient_user_id: str
  wrapped_dek_for_recipient: bytes (document DEK re-encrypted with recipient's public key)
  permissions: "view" | "comment" | "edit"
  expires_at: Optional[datetime]
  created_at: datetime
```

### 3.4 Mobile App Architecture

**Cross-platform approach options**:

| Option | iOS | Android | Web | Offline | Encryption Performance |
|---|---|---|---|---|---|
| **Native (Swift + Kotlin)** | Excellent | Excellent | N/A | Excellent | Best (CryptoKit / JCA) |
| **Flutter** | Good | Good | Good | Good | Good (via platform channels) |
| **React Native** | Good | Good | Possible | Good | Medium (bridge overhead) |
| **Capacitor + Vue** | Good | Good | Excellent | Medium | Medium (WebCrypto) |
| **PWA** | Medium | Medium | Excellent | Good | Medium (WebCrypto) |

**Recommendation**: **Capacitor + Vue** for v1 (reuse existing Vue frontend), then native apps for iOS/Android as the product matures.

Rationale:
- Reuses the existing MyDocs Vue codebase
- Capacitor gives native shell for iOS/Android with access to Secure Enclave / StrongBox
- Web app works immediately
- Migrate to native when you need performance-critical crypto or platform-specific features

**Offline-first design** (critical for mobile):
1. Documents cached encrypted on device (SQLite + encrypted blob files)
2. AI results cached locally after first processing
3. Sync encrypted deltas when online
4. Conflict resolution: last-write-wins for metadata, append-only for annotations

### 3.5 AI Processing — The Consent-Gated Pipeline

This is the core UX innovation: **AI features are explicitly consent-gated, per-document, with full transparency**.

**First-time AI consent flow**:
```
┌──────────────────────────────────────────────────────┐
│                                                       │
│  "Enable AI Features for this document?"              │
│                                                       │
│  What happens:                                        │
│  - Your document text is sent to our AI service       │
│    (Azure OpenAI, hosted in EU)                       │
│  - AI analyzes the content and generates:             │
│    summaries, key facts, and a search index           │
│  - Results are encrypted and stored with your         │
│    encryption key                                     │
│  - The unencrypted text exists only during            │
│    processing and is not retained                     │
│                                                       │
│  Your rights:                                         │
│  - You can disable AI and delete all AI-generated     │
│    data at any time                                   │
│  - Your documents are NEVER used to train AI models   │
│  - Processing happens in the EU (Sweden Central)      │
│                                                       │
│  [Learn more about our AI processing]                 │
│                                                       │
│      [ Not now ]          [ Enable AI ]               │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**Processing receipt** (shown after AI completes):
```
┌──────────────────────────────────────────────────────┐
│  AI Processing Complete                               │
│                                                       │
│  Document: contract_2026.pdf                          │
│  Processed at: 2026-03-07 14:23 UTC                  │
│  AI Service: Azure OpenAI (Sweden Central)            │
│  Data sent: 12 pages of extracted text (43 KB)        │
│  Data retained by AI provider: None (zero retention)  │
│  Results generated: Summary, 8 extracted fields,      │
│                     search index                      │
│  Results encrypted with: Your personal key            │
│                                                       │
│  [Delete AI data]  [View processing log]              │
└──────────────────────────────────────────────────────┘
```

### 3.6 Sub-Processor Configuration for EU Compliance

**Azure OpenAI** (for LLM and embeddings):
- Deploy in **Sweden Central** (EU, with data residency guarantees)
- Use **Azure OpenAI** (not OpenAI API directly) — data stays within Azure boundary
- Enable **Azure OpenAI Data, Privacy, and Security** settings:
  - Opt out of abuse monitoring (available for approved use cases)
  - Zero data retention for completions
  - No model training on customer data (default for Azure OpenAI)
- Document in DPA: "LLM processing occurs within Microsoft Azure EU boundary"

**Azure Document Intelligence**:
- Deploy in **West Europe** or **France Central**
- Data processed in-region, not retained after processing
- DPA with Microsoft covers this

**MongoDB Atlas**:
- Deploy in **Azure West Europe** or **Azure North Europe**
- Enable **Encryption at Rest** (AES-256, customer-managed keys via Azure Key Vault)
- Enable **Audit Logging** for access tracking
- DPA with MongoDB Inc.

**Blob Storage**:
- Azure Blob in **West Europe**
- Enable **Customer-Managed Keys** (CMK) via Azure Key Vault
- Enable **Soft Delete** (for recovery) + **Immutable Storage** (for audit compliance)
- Geo-redundancy: **ZRS** (Zone-Redundant Storage) — stays within single EU region

### 3.7 Encryption Implementation Detail

**Key hierarchy**:

```
User Password
    │
    ├── (Argon2id, salt=random, t=3, m=64MB, p=4)
    │
    ▼
Password-Derived Key (PDK)
    │
    ├── Encrypts/decrypts ──► Master Key (MK) [random 256-bit, generated at signup]
    │                              │
    │                              ├── Derives ──► Key Encryption Key (KEK)
    │                              │                    │
    │                              │                    ├── Wraps ──► Document DEK 1
    │                              │                    ├── Wraps ──► Document DEK 2
    │                              │                    └── Wraps ──► ...
    │                              │
    │                              └── Derives ──► Sharing Key Pair (X25519)
    │                                                   │
    │                                                   ├── Public key: stored on server (for receiving shares)
    │                                                   └── Private key: encrypted with MK, stored on server
    │
    └── On mobile: MK also protected by device Secure Enclave / biometrics
        (so user doesn't enter password every time)
```

**What the server stores per user**:
- `wrapped_master_key`: MK encrypted with PDK (server can't decrypt without password)
- `kdf_params`: salt, cost parameters (needed to re-derive PDK from password)
- `public_key`: X25519 public key (plaintext — it's public)
- `wrapped_private_key`: X25519 private key encrypted with MK

**What the server stores per document**:
- `wrapped_dek`: Document DEK encrypted with user's KEK
- `encrypted_blob`: Document file encrypted with DEK
- `encrypted_content`: Parsed text encrypted with DEK
- `encrypted_ai_results`: AI outputs encrypted with DEK
- Plaintext: `file_type`, `file_size`, `created_at`, `ai_status` (operational metadata only)

**Password change**:
1. Derive old PDK from old password
2. Decrypt MK with old PDK
3. Derive new PDK from new password
4. Re-encrypt MK with new PDK
5. Upload new `wrapped_master_key` (no document re-encryption needed!)

**Account recovery**:
- **Option A: Recovery key** (Proton-style) — at signup, show user a recovery key (random string), store recovery-key-encrypted MK on server. User writes it down.
- **Option B: Device-bound recovery** — if user has another logged-in device, that device can re-wrap the MK
- **Option C: No recovery** — lost password = lost data (strongest guarantee, worst UX)
- **Recommended**: Option A (recovery key) + Option B (device-bound) for consumer product

### 3.8 Search in a Consumer Context

**The search problem** is more tractable in a consumer context than enterprise:
- Individual users have ~100s to low 1000s of documents (not millions)
- This makes client-side search feasible

**Hybrid search strategy**:

| Search Type | How It Works | Where It Runs |
|---|---|---|
| **Filename / tag search** | Encrypted metadata decrypted client-side, filtered locally | Client |
| **Full-text search** | Download encrypted page content, decrypt, search with lunr.js / MiniSearch | Client |
| **Semantic search** | Download encrypted embeddings, decrypt, run vector similarity locally | Client |
| **AI Q&A ("Ask your docs")** | Client selects relevant pages (via local search), sends decrypted context to server AI pipeline | Server (consent-gated) |

For a user with 500 documents (~2000 pages):
- Encrypted search index: ~5-10 MB (download once, cache on device)
- Encrypted embeddings: ~25 MB at 384 dims (small local model) or ~100 MB at 3072 dims
- Both are feasible for mobile with local caching

**Scaling check**: At 10,000 pages the local search index is ~50-100 MB. Still workable on modern phones. Beyond that, could implement an encrypted server-side index (SSE) or segment by folder.

### 3.9 Pricing Model & Free Tier

Trust-first pricing — the free tier should be genuinely useful:

| Tier | Price | Documents | AI Features | Storage |
|---|---|---|---|---|
| **Free** | 0 | 50 documents | 10 AI queries/month | 500 MB |
| **Pro** | 9.99/mo | Unlimited | Unlimited AI | 10 GB |
| **Family** | 14.99/mo | Unlimited, shared vault | Unlimited AI | 50 GB, 5 users |

**Trust-building pricing decisions**:
- Free tier includes encryption (not a paid upsell)
- No "privacy tax" — encryption is default for all tiers
- Family tier uses the sharing key infrastructure from 3.7
- Transparent about what changes between tiers (capacity, not privacy)

---

## Part 4: Compliance Checklist

### 4.1 Pre-Launch Legal Requirements

- [ ] **Privacy Policy**: GDPR-compliant, plain language, covers all processing activities
- [ ] **Terms of Service**: EU Consumer Rights Directive compliant, clear cancellation
- [ ] **Cookie Policy**: Minimal cookies, consent banner (ePrivacy)
- [ ] **Sub-processor list**: Published and maintained (Azure, MongoDB, Auth0)
- [ ] **Data Processing Agreements**: Signed with all sub-processors
- [ ] **DPIA** (Data Protection Impact Assessment): Completed for AI processing of personal documents
- [ ] **DPO appointment**: Data Protection Officer designated (can be external)
- [ ] **Records of Processing Activities**: Documented (Art. 30)
- [ ] **EU representative**: If company is not EU-based, appoint EU representative (Art. 27)
- [ ] **Legal entity**: Consider EU subsidiary for trust (Irish or Dutch entity common)

### 4.2 Technical Compliance Requirements

- [ ] **Data residency**: All processing and storage in EU Azure regions
- [ ] **Encryption at rest**: AES-256 for all user data (blobs, database, backups)
- [ ] **Encryption in transit**: TLS 1.3 for all connections
- [ ] **Access controls**: RBAC, principle of least privilege, no engineer access to user data
- [ ] **Audit logging**: All data access logged, tamper-proof (Azure Monitor / Immutable Blob)
- [ ] **Data deletion pipeline**: Automated purge within 30 days of deletion request
- [ ] **Data export**: GDPR portability endpoint (download all your data)
- [ ] **Breach detection**: Monitoring + alerting for unauthorized access
- [ ] **Backup encryption**: Backups encrypted with same key hierarchy
- [ ] **AI model data controls**: Azure OpenAI zero-retention, no training on customer data
- [ ] **Vulnerability management**: Regular scanning, patching SLA
- [ ] **Penetration testing**: Annual, by third party, results published (summary)

### 4.3 AI Act Compliance

- [ ] **Transparency notices**: Clear labeling of AI-generated content in the app
- [ ] **Technical documentation**: Architecture of AI system documented
- [ ] **Logging**: AI processing logs retained (encrypted) for supervisory review
- [ ] **Human oversight**: Users can always override/delete AI outputs
- [ ] **Accuracy documentation**: Known limitations of AI features documented for users
- [ ] **Risk classification**: Self-assessment of risk category, documented reasoning

### 4.4 Certifications to Pursue (Post-Launch)

| Certification | Why | Timeline |
|---|---|---|
| **SOC 2 Type I** | Baseline trust signal for security controls | 3-6 months |
| **SOC 2 Type II** | Proves controls work over time | 12 months |
| **ISO 27001** | International security standard, valued in EU | 12-18 months |
| **C5 (BSI, Germany)** | Cloud security standard, important for German market | 12-18 months |
| **EUCS** (EU Cloud Certification) | Upcoming EU cloud security scheme | When available |

---

## Part 5: Competitive Positioning

### 5.1 Comparison with Alternatives

| Feature | Our Product | NotebookLM | Apple Notes | Proton Drive | Tresorit |
|---|---|---|---|---|---|
| AI document understanding | Yes | Yes | Basic | No | No |
| E2E encryption | Yes (vault mode) | No | iCloud E2E | Yes | Yes |
| EU data residency | Yes (guaranteed) | No (US) | No (Apple infra) | Yes (Swiss) | Yes (Swiss/EU) |
| Cross-document search | Yes | Yes | Basic | No | Metadata only |
| Open-source client | Yes | No | No | Yes | No |
| Mobile apps | Yes | Web only | Yes | Yes | Yes |
| Document parsing (OCR) | Yes | Yes | No | No | No |
| GDPR compliance | Full | Partial | Partial | Full | Full |
| AI Act compliance | Full | Unknown | N/A | N/A | N/A |

### 5.2 Trust Differentiators

What we can say that competitors can't (or don't):

1. **"Your documents never leave the EU."** — NotebookLM can't say this.
2. **"Our AI never trains on your data."** — Azure OpenAI guarantee, documented.
3. **"Encrypted by default, AI by choice."** — Proton can't offer AI; NotebookLM can't offer encryption.
4. **"Open-source client, audited annually."** — Verifiable trust, not just marketing.
5. **"You hold the key. We can't read your data even if we wanted to."** — For vault-mode documents.
6. **"Every AI operation shows you exactly what data was processed and where."** — Processing receipts.

---

## Part 6: Implementation Roadmap

### Phase 0: Foundation (4-6 weeks)
- User model with per-user isolation (replaces tenant_id for consumer)
- Auth0 integration with EU deployment
- EU Azure infrastructure setup (West Europe primary, Sweden Central for OpenAI)
- Basic privacy policy and ToS

### Phase 1: Encrypted Storage MVP (4-6 weeks)
- Client-side encryption library (Web Crypto API)
- Key derivation and master key management
- Encrypted document upload/download
- Basic document viewer (client-side decryption + PDF.js)
- Capacitor shell for iOS/Android
- No AI features yet — pure encrypted document vault

### Phase 2: Consent-Gated AI (4-6 weeks)
- Consent flow UI for AI processing
- Server-side decrypt → process → re-encrypt pipeline
- Azure DI parsing with EU-region endpoint
- Basic Q&A and summarization via Azure OpenAI (Sweden Central)
- Processing receipts
- Client-side search index (lunr.js + cached encrypted index)

### Phase 3: Full Consumer Features (6-8 weeks)
- Cross-document search (hybrid: local full-text + server-side semantic with consent)
- Document sharing (X25519 key exchange)
- Folder organization
- Offline mode with sync
- Push notifications for shared documents
- Native mobile optimizations

### Phase 4: Trust & Compliance Hardening (ongoing)
- SOC 2 Type I preparation
- Third-party penetration test
- Bug bounty program launch
- DPIA completion and publication
- Open-source client code release
- AI Act conformity documentation

### Phase 5: Growth Features (ongoing)
- Family/team tier with shared vaults
- Advanced extraction (taxes, contracts, medical records)
- Integrations (email import, cloud storage sync)
- Passkey authentication
- Native iOS/Android apps (replacing Capacitor)

---

## Part 7: Open Questions & Risks

### Open Questions

1. **Encryption password UX**: Separate encryption password vs. derived from login password? Separate is more secure but terrible UX for consumers. Leaning toward device-bound keys (Secure Enclave) with recovery key backup.

2. **Free tier AI costs**: Azure OpenAI is expensive. 10 free AI queries/month per user — is that sustainable? Need to model unit economics. Could the free tier be vault-only (no AI)?

3. **Document types**: Start with PDF only (like current MyDocs) or support photos of documents (camera capture on mobile)? Camera capture is killer feature for consumer — "scan your receipt, AI extracts the data."

4. **Jurisdiction of company**: Where to incorporate? EU entity (Ireland, Netherlands) for maximum trust? Or Swiss (like Proton) for neutrality? Affects tax, regulatory obligations, and brand perception.

5. **AI provider diversification**: Currently Azure OpenAI only. Should we support Mistral (EU-based) or Anthropic (EU availability)? Mistral would strengthen the "EU-first" narrative.

6. **Metadata leakage**: Even with E2E encryption, the server sees file sizes, upload times, number of documents, sharing patterns. How much does this matter for trust? Should we pad file sizes or add dummy traffic?

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **EU AI Act reclassification** | Our system classified as high-risk | Design for high-risk from day one |
| **Azure OpenAI EU data residency change** | Data leaves EU | Contractual guarantees, ability to switch to Mistral |
| **Key loss / password loss** | User permanently loses data | Recovery key + device-bound recovery |
| **Encryption performance on mobile** | Slow UX on older phones | Benchmark early, optimize critical path, lazy decryption |
| **Consumer market education** | Users don't understand/value encryption | Lead with "AI for your documents", encryption as trust signal |
| **Cost at scale** | AI processing costs per user | Aggressive caching, smart retrieval (don't send whole doc to LLM) |
| **Regulatory fragmentation** | Different EU countries add local requirements | Legal counsel per target market, start with DE/FR/NL |

---

## Summary

The sweet spot for a consumer product is the **"Transparent Trust" model**:

- **Encrypted by default** — documents are E2E encrypted in a vault
- **AI by explicit consent** — per-document, with full transparency about what happens
- **EU-hosted everything** — Azure EU regions, no data leaves the continent
- **Open-source client** — verifiable encryption, not just a marketing claim
- **GDPR + AI Act compliant** — from day one, not retrofitted

This positions the product uniquely: NotebookLM's AI capabilities + Proton's privacy guarantees + EU regulatory compliance. No current product occupies this space.

The main UX challenge is making encryption invisible to non-technical users while keeping AI features feel seamless despite the consent gate. The main technical challenge is client-side search performance at scale.
