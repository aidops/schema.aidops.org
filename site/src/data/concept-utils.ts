import type { VocabularyData, Concept, Property, Vocabulary, PropertyGroup } from './vocabulary';
import type { Locale } from '../i18n/languages';

/**
 * True for items AidOps owns (routable, renderable as local pages).
 * False for PublicSchema items, which are kept in vocabulary.json for
 * lookup/display but must not get local pages or appear in listings/search.
 */
export function isOwned(
  item: Concept | Property | Vocabulary | undefined,
): boolean {
  return item?.source === 'aidops';
}

/**
 * Resolve the href for a concept/property/vocabulary link. AidOps items
 * route to the local path; PublicSchema items route to their canonical
 * publicschema.org URI.
 */
export function externalHref(
  item: Concept | Property | Vocabulary | undefined,
): string | null {
  if (!item) return null;
  return item.source === 'aidops' ? item.path : item.uri;
}

/**
 * Stable lookup key for the hover-card preview data. AidOps items use their
 * local path; PublicSchema items use their canonical URI. Matches the keying
 * in `build/preview_export.py` so `data-preview-key` attributes resolve
 * against `preview/{locale}.json` entries.
 */
export function previewKey(
  item: Concept | Property | Vocabulary | undefined,
): string | null {
  if (!item) return null;
  return item.source === 'aidops' ? item.path : item.uri;
}

/** Look up a concept's path by ID. Falls back to `/{id}` if unknown. */
export function conceptPath(vocab: VocabularyData, id: string): string {
  return vocab.concepts[id]?.path || `/${id}`;
}

/** Look up a property's path by ID. Falls back to `/{id}` if unknown. */
export function propPath(vocab: VocabularyData, id: string): string {
  return vocab.properties[id]?.path || `/${id}`;
}

export interface InheritedProperty {
  id: string;
  detail: Property | undefined;
  from: string;
}

/**
 * Walk the full supertype chain and collect properties declared on ancestors.
 * Each property is attributed to the nearest ancestor that declares it.
 * Caller passes a set of IDs already seen (typically the concept's own
 * properties) so inherited entries don't duplicate own entries.
 */
export function collectInheritedProperties(
  vocab: VocabularyData,
  conceptId: string,
  seenIds: Set<string>,
  visited: Set<string> = new Set(),
): InheritedProperty[] {
  const result: InheritedProperty[] = [];
  const concept = vocab.concepts[conceptId];
  if (!concept) return result;
  for (const st of concept.supertypes) {
    if (visited.has(st)) continue;
    visited.add(st);
    const parent = vocab.concepts[st];
    if (!parent) continue;
    for (const ref of parent.properties) {
      if (!seenIds.has(ref.id)) {
        seenIds.add(ref.id);
        result.push({ id: ref.id, detail: vocab.properties[ref.id], from: st });
      }
    }
    result.push(...collectInheritedProperties(vocab, st, seenIds, visited));
  }
  return result;
}

/** A property entry enriched with display info for grouped rendering. */
export interface GroupedPropertyEntry {
  id: string;
  detail: Property | undefined;
  from: string | null;
}

/** A display group: a category label plus the properties in it. */
export interface DisplayGroup {
  category: string;
  label: string;
  properties: GroupedPropertyEntry[];
}

/**
 * Build display groups for a concept that has property_groups.
 * Returns an array of groups, each with a translated label and
 * enriched property entries (including inherited-from attribution).
 */
export function buildDisplayGroups(
  vocab: VocabularyData,
  conceptId: string,
  groups: PropertyGroup[],
  locale: Locale,
): DisplayGroup[] {
  const ownIds = new Set(
    (vocab.concepts[conceptId]?.properties ?? []).map((ref) => ref.id),
  );

  // Build a map of inherited property ID -> source concept ID
  const inheritedMap: Record<string, string> = {};
  const visited = new Set<string>();
  function walkSupertypes(cid: string) {
    const c = vocab.concepts[cid];
    if (!c) return;
    for (const st of c.supertypes) {
      if (visited.has(st)) continue;
      visited.add(st);
      const parent = vocab.concepts[st];
      if (!parent) continue;
      for (const ref of parent.properties) {
        if (!(ref.id in inheritedMap)) {
          inheritedMap[ref.id] = st;
        }
      }
      walkSupertypes(st);
    }
  }
  walkSupertypes(conceptId);

  const categories = vocab.categories ?? {};

  return groups.map((group) => {
    const catData = categories[group.category];
    const label =
      catData?.label?.[locale] ?? catData?.label?.en ?? group.category;

    const properties: GroupedPropertyEntry[] = group.properties.map((pid) => ({
      id: pid,
      detail: vocab.properties[pid],
      from: ownIds.has(pid) ? null : inheritedMap[pid] ?? null,
    }));

    return { category: group.category, label, properties };
  });
}

/** Flat list of every subtype (direct and indirect) of a concept. */
export function collectAllSubtypes(vocab: VocabularyData, conceptId: string): string[] {
  const result: string[] = [];
  const visited = new Set<string>();
  function walk(id: string) {
    if (visited.has(id)) return;
    visited.add(id);
    const c = vocab.concepts[id];
    if (!c) return;
    for (const st of c.subtypes) {
      result.push(st);
      walk(st);
    }
  }
  walk(conceptId);
  return result;
}
