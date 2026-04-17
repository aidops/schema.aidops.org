# Better PublicSchema integration in the AidOps site

Status: **approved by Jeremi 2026-04-17, ready to implement.**
Authors: Claude (Opus 4.7), reviewed by Jeremi.
Date: 2026-04-17.
Revision notes:
- v1: initial research + plan.
- v2: folded in UX review findings.
- v3: Jeremi approved all suggested answers; "Questions" section replaced with "Locked decisions" below.

## Motivation

Two visible problems on concept pages today:

1. **Inherited PS properties show "unknown" type.** On `/AnthropometricProfile` (and every concept that inherits from a PS supertype), the inherited rows (`identifiers`, `subject`, `observation_date`, `performed_by`…) render with `type = unknown`. This is misleading and looks broken.
2. **PS-owned concepts feel missing.** A user reading a property like `subject` sees `concept:Person` as the type, but there's no landing for `Person` on schema.aidops.org. The current behavior (supertype links go out to `publicschema.org`) is OK for supertypes but nowhere else; most of the site silently ignores PS existence.

A secondary opportunity surfaced in brainstorming: the site is dense with cross-references (concept → property → vocab → concept). Navigation between them is costly. A **hover/focus preview card** for every cross-reference link — internal and external — would reduce that cost and also resolve the "missing concept" feeling for PS.

This plan covers both.

## Research: current state of the code

### Where "unknown" comes from

- `build/build.py:798-809` filters `out_concepts` / `out_properties` / `out_vocabularies` down to `source == "aidops"` before serializing `vocabulary.json` and `manifest.json`. The filter is load-bearing for not emitting PS pages, but also strips PS metadata the site would need for rendering inherited rows.
- `site/src/components/pages/ConceptDetail.astro:169, 219` reads `p.detail?.type || 'unknown'` where `p.detail` is `vocab.properties[ref.id]`. For inherited PS properties the lookup returns `undefined`, so `'unknown'` is the fallback.
- `site/src/data/concept-utils.ts:26-49` walks the supertype chain across AidOps → PS seamlessly (both live in the same `vocab.concepts` map during build), but in the emitted `vocabulary.json` PS entries are gone, so the attribution link (`p.from`) points to a concept the site doesn't know either.

### What already works well

- **Supertypes section** (`ConceptDetail.astro:111-122`): when a supertype is not in the local vocab, it renders as an external link to `https://publicschema.org/concepts/{id}/` with a "(PublicSchema)" hint. This is the right UX pattern and can generalize.
- **Build-time merged graph** (`build/loader.py:112-124`): AidOps and PS YAML are loaded into one tagged dict with `source` field. Type resolution sees the full graph. This is the reason the build can produce correct JSON-LD today.
- **Per-concept JSON-LD emission** (`build/build.py:760-783`): already filtered to AidOps-owned via `source` check. The filter pattern we'd apply to `getStaticPaths` mirrors this.

### Routing and iteration sites that would be affected if we keep PS in `vocabulary.json`

If we stop filtering PS items out, these sites will start seeing them and need guards:

- `site/src/pages/[...slug].astro:11-25` — `getStaticPaths` iterates every concept and property. Without a filter, PS items would try to generate pages at `/Person/`, which must NOT happen.
- `site/src/components/pages/ConceptsIndex.astro:22` — listing.
- `site/src/components/pages/PropertiesIndex.astro:18` — listing.
- `site/src/data/search-index.ts:35, 48, 61` — search would include PS items if we don't filter.

Every one of these needs a `source !== 'publicschema'` guard (or a helper like `isOwned(concept)`).

### Type definitions to update

- `site/src/data/vocabulary.ts` — `Concept`, `Property`, `Vocabulary` interfaces don't currently have a `source` field. Add `source: 'aidops' | 'publicschema'`.

## Prior art (hover previews)

Brainstorm notes, kept here for posterity:

**Card-style hover previews** (richest pattern, best fit for us)

- Wikipedia Page Previews: ~500ms open delay, short close delay, keyboard-accessible, Escape dismisses, disabled on mobile. Opt-out in settings.
- GitHub hovercards: async, non-blocking, disappear if you move away fast.
- Linear issue hovercards: very snappy, data is local, small footprint.
- Notion "peek": three tiers (hover → side panel → full nav). Overkill for a docs site.

**Docs-site precedents (most relevant)**

- sphinx-hoverxref (Read the Docs ecosystem): tooltips on every internal cross-reference. Exactly our use case.
- Apple Developer docs / Stripe API refs: hover a type → popover with description.
- Material for MkDocs: tooltips supported.
- Obsidian "Page Preview" core plugin: hover `[[Link]]` → mini rendering.
- Schema.org itself: does NOT do this. We can be better than the model we inherit from.

**Technical building blocks**

- Positioning: `@floating-ui/dom` (modern successor to Popper). Handles viewport flip, collision.
- Complete library: `tippy.js` (~10kb, MIT).
- Delays: 300-700ms open, 100-200ms close. Fast enough to feel responsive, slow enough to avoid accidents.
- ARIA: `role="tooltip"` + `aria-describedby`, Escape dismisses, focus-visible triggers the same card as hover.
- Astro: one global `<script>` with event delegation on a marker attribute (e.g. `data-ps-ref`). Avoids per-link hydration.

## Proposed strategy

Two independent changes, shippable separately:

### Change 1 — Fix the "unknown" data bug (small, ship first)

**Approach:** keep PS concepts/properties/vocabularies in `vocabulary.json` with `source: 'publicschema'`. Add guards at every site of iteration so PS items don't leak into pages, indexes, or search.

**Files:**

- `build/build.py:798-809` — remove (or loosen) the filter so PS entries carry through to `vocabulary.json`. They're already built upstream at lines 471-496 and 500-535; just stop stripping them at the end.
- `site/src/data/vocabulary.ts` — add `source: 'aidops' | 'publicschema'` to `Concept`, `Property`, `Vocabulary`.
- `site/src/data/concept-utils.ts` — add a small helper `isOwned(item) => item?.source === 'aidops'` for reuse.
- `site/src/pages/[...slug].astro:11-25` — filter `getStaticPaths` to owned only.
- `site/src/components/pages/ConceptsIndex.astro:22` — filter listing to owned.
- `site/src/components/pages/PropertiesIndex.astro:18` — filter listing to owned.
- `site/src/data/search-index.ts:35, 48, 61` — filter search to owned.
- `site/src/components/pages/ConceptDetail.astro` — for any linked concept/property, branch on `source`:
  - AidOps → internal link (current behavior)
  - PS → external link to `publicschema.org` with the existing "(PublicSchema)" hint, now extended to property rows and type cells, not only supertypes.
- `site/src/components/pages/PropertyDetail.astro` — same branching (needs review; check what it does with concept types today).
- `site/src/components/pages/VocabDetail.astro` — same branching if vocabularies reference PS types.

**Also in Change 1 (copy, not code):** add a short "AidOps extends PublicSchema" explanation on concept pages so users understand why some links leave the site. Today the site doesn't make the relationship explicit anywhere prominent; the muted "(PublicSchema)" hint is too subtle to carry the mental model. Proposed placement: a one-line aside near the Supertypes section of `ConceptDetail.astro` when any supertype or inherited property is PS-sourced. Draft copy (for Jeremi to approve): "This concept builds on PublicSchema. Fields marked *PublicSchema* are defined there." Translate for fr/es.

**What changes for the user:** on `/AnthropometricProfile`, the inherited row now shows `Person` (linked to publicschema.org) instead of `unknown`, with real type info, real vocabulary labels, real definitions. The page header explains once why those links go off-site.

**What stays the same:** no new pages generated. PS items still route out to publicschema.org. No duplication.

**Tradeoff:** `vocabulary.json` grows (all PS concepts/properties/vocabs get included). For a static site consumed once at build time this is a non-issue. If it ever becomes one, we can emit a slim subset (only the PS items actually referenced from AidOps YAML) — but that's premature.

**Unknown:** exact shape of the PS URI in output today for concepts. `build/build.py:481` uses `_compute_path(domain, concept_id)` which returns `/concepts/{domain}/{id}` or `/concepts/{id}`. We must NOT use that path for the href — we want the external publicschema.org URL. The `uri` field (`_compute_uri(PS_BASE_URI, domain, concept_id)` at line 480) is the right one to link to.

### Change 2 — Hover/focus preview cards for cross-references

**Scope:** all link types on the site that point to a concept / property / vocabulary, whether the target is AidOps-owned or PS. Wherever we render a link today:

- Property tables on ConceptDetail (type column, property name column, inherited-from attribution)
- Supertypes / subtypes lists on ConceptDetail
- Used-by list on PropertyDetail
- Vocabulary value references
- Aligned-standards rows (external — optional, lower priority)

**Approach:** a single Astro island (global client script) + a small `dist/preview.json` artifact.

**Data delivery:** build emits `dist/preview.json` keyed by full path (internal) or by URI (external PS). Each entry carries: `label`, `definition_excerpt` (build-time truncated per locale: ~220 chars `en`, ~260 `fr` / `es`, word-boundary-safe), `type` (for properties), `vocabulary` (for properties), `maturity`, `href` (where "open" goes), `source`, `locale_used` (when falling back to a different locale than requested). Loaded once on first hover, cached. Keeps HTML slim.

**Card content (final):**
- Label (bold)
- Source badge — "Defined in PublicSchema" for PS, omitted for AidOps-owned (no-op for own content)
- Maturity badge (draft / candidate / stable) when not `stable`, styled to match existing page badges
- Truncated definition (build-time, word-boundary-safe)
- Language-fallback tag when `locale_used !== requested_locale` (e.g., small "EN" pill if a French user sees English fallback)
- For properties: type line (e.g. `concept:Person`) and vocabulary reference if any
- "Open →" CTA linking to the full page (or publicschema.org for PS)

**Nested links policy:** cards are read-only. Links rendered inside a card (e.g. a property card showing `concept:Person` as its type) navigate on click; they do NOT open another card on hover. This avoids card-on-card stacking and ambiguous focus traps. Documented here so it's a deliberate choice, not an omission.

**Discoverability:** rejected the reviewer's suggestion of `ⓘ` icons and one-time nudges — too much visual noise for a link-heavy docs site, and nudges get dismissed unread. Accepted compromise: a subtle link-hover style (slight color shift or dotted underline variant) on any link carrying `data-preview-key`, so a user mousing over gets a visual cue that something extra is there without a dedicated affordance. Tune during Phase 2 styling.

**Timing:** 500ms open delay, 200ms close delay, pointer-settling gate (card only opens if pointer has been still for ~100ms at end of delay). These numbers are tuned for a user scanning a dense property table — 400/150 would trigger too aggressively on pass-through hovers.

**Component:** `site/src/components/HoverCard.astro` renders nothing server-side; it's mostly a `<script>` that attaches listeners. Links across the site get a marker attribute at render time (e.g. `data-preview-key="/concepts/Person/"` or `data-preview-key="https://publicschema.org/concepts/Person/"`). The script:

1. On `mouseenter` or `focusin` on a `[data-preview-key]`, start a 500ms timer with pointer-settling gate.
2. On timer fire, load `/preview.json` if not yet loaded, look up the entry, render a card positioned with `@floating-ui/dom`.
3. Card gets `role="tooltip"`, `aria-describedby` wired up on the anchor link.
4. On `mouseleave`, 200ms close timer. Movement onto the card cancels it. Escape dismisses.
5. Touch devices: listeners only on fine-pointer media (`(hover: hover)`). Tap navigates as today.
6. Respect `prefers-reduced-motion: reduce` — suppress open/close animation, use instant show/hide.
7. Keyboard path: Tab onto link triggers card; Tab again moves to "Open →" CTA inside card (single Tab stop, not full traversal of card content).
8. Screen reader: card content announces as supplementary to the anchor link via `aria-describedby`; does NOT auto-steal focus. Verify announce order with VoiceOver + NVDA before Phase 3 ships.

**Library choice:** start with `@floating-ui/dom` + custom (~150 LOC). If it feels like too much plumbing, swap to `tippy.js`. I'd rather not pay for tippy's full feature set.

**Styling:** match existing concept-page look. Card shows label (bold), source badge (AidOps / PublicSchema), 2-3 line truncated definition, type line if property, "Open →" link. Max-width ~360px.

**Files:**

- `build/build.py` or new `build/preview_export.py` — emit `dist/preview.json` at end of build.
- `site/src/components/HoverCard.astro` — new. The island.
- `site/src/scripts/hover-card.ts` — new. Event delegation + positioning logic.
- `site/src/layouts/Base.astro` — mount `<HoverCard />` once globally.
- `site/package.json` — add `@floating-ui/dom` dependency.
- Every component that renders cross-ref links — add `data-preview-key` attribute. A helper like `previewKey(item)` would centralize this.

**Tradeoff: `preview.json` size.** Full preview dataset for all concepts/properties/vocabs (AidOps + PS) is probably 100-300 KB. That's fine for on-demand load; we don't block page render on it. If too big, shard (`/preview/concepts.json`, `/preview/properties.json`) later.

**Tradeoff: vs. stub pages for PS.** This plan assumes hover previews substitute for the stub-page idea. Parking the stub-page decision, but the UX review flagged that this is not only an SEO tradeoff: without stub pages, any URL like `schema.aidops.org/concepts/Person/` returns 404, so shared links from external tools, policy docs, or training materials will break for PS concepts. Hover cards help in-site browsing but don't fix deep linking. The call to defer rests on this premise: **PS concepts on this site are context, not primary destinations.** If that premise turns out to be wrong (for example, humanitarians start Googling "Person schema" and landing here), stub pages become necessary. Revisit after Phase 3 ships and there's usage data. Stub pages can reuse `preview.json` if built later.

**Coexistence with `ExpandableDefinition`.** Today the Definition column of property tables uses `ExpandableDefinition` for inline expand/collapse. Hover cards over the *property name* in the same row must not duplicate that surface. Resolution: card over the property name leans on **metadata** (type, vocab, maturity, source) with a **short** definition excerpt (~220 chars truncated). The Definition column keeps the full text inline. Audit every co-occurrence before Phase 3 wires links — prerequisite step in the checklist.

**Unknown:**

- Whether we want the card to work on the aligned-standards rows (external non-PS links like SDMX, ILO). Currently we have no preview data for those. Defer.
- Draft copy for the "AidOps extends PublicSchema" page-header aside and the "Defined in PublicSchema" badge label — needs Jeremi's approval.

## Phasing

### Phase 1 — Data fix + "AidOps extends PS" copy (Change 1)

- [ ] **1.1** `build/build.py`: stop filtering PS items out of `vocabulary.json` / `manifest.json`. Keep the `source` tag on every output.
- [ ] **1.2** `site/src/data/vocabulary.ts`: add `source: 'aidops' | 'publicschema'` to `Concept`, `Property`, `Vocabulary`.
- [ ] **1.3** `site/src/data/concept-utils.ts`: add `isOwned(item)` helper, plus `externalHref(item)` (returns `item.uri` for PS, `item.path` for AidOps).
- [x] **1.4** `site/src/pages/[...slug].astro`: guard `getStaticPaths` to owned only.
- [x] **1.5** `site/src/components/pages/ConceptsIndex.astro`: filter listing to owned only.
- [x] **1.6** `site/src/components/pages/PropertiesIndex.astro`: filter listing to owned only.
- [x] **1.7** `site/src/data/search-index.ts`: filter search records to owned only.
- [x] **1.8** `site/src/components/pages/ConceptDetail.astro`: every concept/property link chooses internal vs. external via `isOwned`. Inherited-from attribution gets real link + (PublicSchema) hint when PS. Type cells render real type for PS properties instead of 'unknown'.
- [x] **1.9** `site/src/components/pages/PropertyDetail.astro`: same pattern where applicable.
- [x] **1.10** `site/src/components/pages/VocabDetail.astro`: same pattern where applicable.
- [ ] **1.11** Get Jeremi to approve copy for the "AidOps extends PublicSchema" one-liner (draft: "This concept builds on PublicSchema. Fields marked *PublicSchema* are defined there.") and its translations for fr/es. Copy goes in `site/src/i18n/` locale files.
- [x] **1.12** Render the one-liner in `ConceptDetail.astro` near the Supertypes section, conditional on the page having any PS-sourced supertype or inherited property. Don't show it on pure-AidOps pages (noise).
- [ ] **1.13** Tests:
  - [ ] Python: `tests/` — assert `vocabulary.json` contains entries with `source == 'publicschema'` for concepts/properties referenced transitively.
  - [ ] Visual / integration: `just dev` → `/AnthropometricProfile` shows real types for inherited rows; clicking `Person` goes to publicschema.org; the "AidOps extends PublicSchema" aside is visible.
- [ ] **1.14** Run `just check`.
- [ ] **1.15** Commit (`fix: surface PS metadata for inherited rows, explain PS relationship`).

### Phase 2 — Hover preview foundation (Change 2, part A)

- [ ] **2.1** Build step: emit `dist/preview.json` keyed by path and URI, carrying label / `definition_excerpt` (build-time word-boundary truncation per locale: en ~220 chars, fr/es ~260) / type / vocabulary / maturity / href / source / `locale_used` tag when falling back to a non-requested locale.
- [ ] **2.2** Unit test the build step (inputs/outputs, ensures PS entries are keyed by publicschema.org URI, AidOps entries by local path; verifies word-boundary truncation doesn't cut mid-word; verifies locale fallback behavior).
- [ ] **2.3** `npm install @floating-ui/dom` in `site/`.
- [ ] **2.4** `site/src/components/HoverCard.astro` + `site/src/scripts/hover-card.ts`:
  - Event delegation on `[data-preview-key]`.
  - Fetch `/preview.json` on first hover, cache.
  - Floating-ui positioning with viewport flip/shift.
  - Open timer 500ms with **pointer-settling gate** (card opens only if pointer has been still ~100ms at end of delay, to avoid triggering during fast table-scanning).
  - Close timer 200ms, cancellable by moving onto card.
  - ARIA: `role="tooltip"`, `aria-describedby` wired to anchor.
  - Escape dismisses.
  - Hover-capable-pointer only (`(hover: hover)` media).
  - Respect `prefers-reduced-motion: reduce` → suppress animation, instant show/hide.
  - Keyboard: Tab onto link triggers card; Tab again reaches the "Open →" CTA (single extra Tab stop).
  - Screen reader: card content is supplementary via `aria-describedby`, does NOT auto-steal focus.
  - Nested links inside card navigate on click; do NOT open another card.
  - Render source badge ("Defined in PublicSchema") for PS, omitted for AidOps.
  - Render fallback-language tag when `locale_used !== requested_locale`.
  - Maturity badge shown when not `stable`.
- [ ] **2.5** Mount `<HoverCard />` in `site/src/layouts/Base.astro`.
- [ ] **2.6** Helper in `site/src/data/concept-utils.ts` for `previewKey(item)`.
- [ ] **2.7** Subtle hover style for `[data-preview-key]` links as passive discoverability cue (e.g. slight color shift or dotted underline on hover). Tune during styling; no icons or nudges.
- [ ] **2.8** Accessibility verification: Tab focus shows card; Escape dismisses; VoiceOver + NVDA announce order documented; `prefers-reduced-motion` honored.

### Phase 3 — Wire links (Change 2, part B)

- [ ] **3.0** Prerequisite audit: every place where `data-preview-key` would coexist with `ExpandableDefinition` on the same row. Decide per surface whether the card definition excerpt and the inline expandable definition both add value, or whether one should be suppressed. Default: property-name cell gets the card (metadata-forward), Definition cell keeps `ExpandableDefinition` (full text). Document decisions inline.
- [ ] **3.1** Instrument `ConceptDetail.astro` links (supertypes, subtypes, property table type cells and name cells, inherited-from).
- [ ] **3.2** Instrument `PropertyDetail.astro` links (used-by, type).
- [ ] **3.3** Instrument `VocabDetail.astro` links.
- [ ] **3.4** ~~Instrument listing pages~~ — **skip for v1.** Listings are scanning surfaces; cards would be noise. Revisit only if user feedback points to the gap.
- [ ] **3.5** Instrument footer/meta links where they reference PS (if any).
- [ ] **3.6** Visual pass across all locales (en, fr, es). Check that truncated definitions at the per-locale char limits render without overflow at 360px card width.
- [ ] **3.7** `just check` + `just site-build`. Verify card bundle size is sane.
- [ ] **3.8** Commit (`feat: hover previews for cross-reference links`).

### Out of scope, explicitly

- **Stub pages for PS concepts.** Parked. This is not just an SEO concern: without stub pages, any URL like `schema.aidops.org/concepts/Person/` returns 404, so externally-shared deep links to PS concepts will break. The deferral rests on the premise that PS concepts on this site are context, not primary destinations. Revisit once Phase 1+2+3 are live; if usage data shows users landing on missing PS concept URLs, promote this.
- **Previews for non-PS external links** (SDMX, ILO, etc.) in the aligned-standards table. Would need separately-curated preview data.
- **Opt-out setting for users who don't want hovercards.** Skip for v1.
- **Touch-device tap-to-preview.** Skip for v1 (matches Wikipedia's behavior).
- **`ⓘ` icon affordance on preview-enabled links** and **one-time hovercard onboarding nudges.** Rejected: would add visual noise to a link-heavy docs surface, and nudges typically get dismissed unread. Relying on a subtle hover style (task 2.7) plus organic discovery by power users instead.
- **Hover cards on listing pages** (ConceptsIndex, PropertiesIndex). Would be noise on a scanning surface (see task 3.4).

## Verification

- `just validate`, `just build`, `just test`, `just check` all clean.
- Manual: load `/AnthropometricProfile` and confirm (a) no "unknown" rows, (b) hover on `Person` shows a card, (c) click on `Person` goes to publicschema.org.
- Manual: Tab through the page with keyboard, verify card appears on focus and dismisses on Escape.
- Manual: load on a phone (or devtools mobile emulation), verify no hovercards and navigation still works.

## Locked decisions (Jeremi approved 2026-04-17)

1. **Library**: `@floating-ui/dom` + custom script (~150 LOC). Reject `tippy.js` for v1.
2. **Page-header copy**: "This concept builds on PublicSchema. Fields marked *PublicSchema* are defined there." Translate to fr/es in same voice. Lives in `site/src/i18n/` locale files.
3. **Source badge wording in card**: "Defined in PublicSchema".
4. **Stub pages for PS concepts**: deferred, not rejected. Working assumption: PS concepts are mostly context here, occasionally primary. Revisit post-launch with usage data.
5. **Accessibility criteria are firm**: treat `prefers-reduced-motion`, keyboard-only Tab path, and screen-reader announce-order verification as acceptance criteria for Phase 2 completion, not aspirational checks.
6. **Build emission**: new `build/preview_export.py` module. Keeps `build.py` from sprawling.
7. **Phasing**: ship Phase 1 alone first. Phase 2/3 land behind it without pressure.

## UX review response (v2 revision log)

This section documents which UX-review findings got folded in, which got reframed, and which got pushed back on, with rationale. Read alongside the revised plan above.

### Accepted in full

- **Mental-model copy (#2).** The site had no explicit "AidOps extends PublicSchema" statement. Added to Phase 1 as tasks 1.11 and 1.12. Copy needs Jeremi's approval.
- **Nested-link policy (#3).** Cards are read-only; links inside navigate rather than open further cards. Documented in the Change 2 approach and task 2.4.
- **Timing (#4).** Changed from 400/150ms to 500/200ms, added pointer-settling gate. Reflects that dense property tables are scanning surfaces where false triggers are costly.
- **ExpandableDefinition coexistence (#6).** Added task 3.0 as a prerequisite audit. Default resolution: card over property-name leans on metadata, Definition cell keeps full inline text.
- **Accessibility gaps (#7).** `prefers-reduced-motion`, single-Tab-stop keyboard path, explicit "no auto-focus-steal" for screen readers, VoiceOver + NVDA verification. Added to task 2.4 and 2.8.
- **Truncation by locale (#8).** Replaced "2-3 lines" with build-time char limits (en ~220, fr/es ~260), word-boundary-safe. Added locale-fallback tagging in `preview.json`. Tasks 2.1 and 2.2.
- **Skip listing pages (#9).** Task 3.4 struck from Phase 3. Added to "Out of scope".

### Accepted with reframing

- **Stub pages / deep linking (#5).** Keeping the deferral but rewrote the "Out of scope" note to name the real cost: shared URLs to `/concepts/Person/` return 404, not just lost SEO. Deferral rests on the premise that PS concepts are context here, not primary destinations. To revisit with usage data post-launch.

### Partial push back

- **Discoverability (#1).** The reviewer's concern is real (users won't know cards exist), but the proposed fixes — `ⓘ` icons on every preview-enabled link, one-time onboarding nudges — would clutter a link-dense docs surface more than the discoverability problem warrants. Nudges also routinely get dismissed unread. Accepted compromise: a subtle hover style (color shift or dotted-underline variant) on `[data-preview-key]` links as a passive cue. Task 2.7. Rejected the icon/nudge approach; documented in "Out of scope".

### Decisions I made with defaults

- **Locale fallback visibility**: when a card falls back from requested-locale to English, the card shows a small language-tag pill. Silent fallback would erode trust for fr/es users.
- **Maturity badge in card**: default yes, shown only when not `stable`. Technical audience cares about signalling non-normative content.
- **Source badge wording**: "Defined in PublicSchema" (rather than bare "PublicSchema"). Communicates authority and avoids the muted-label problem the reviewer flagged. Still open for Jeremi's approval in question 3.

### Surfaced to Jeremi as explicit questions

- Canonical one-sentence AidOps↔PS explanation (question 2).
- PS concepts as primary destinations or context (question 4).
- Keyboard-only / screen-reader-only user prevalence (question 5).
