import { loadVocabulary } from './vocabulary';
import { defaultLocale, type Locale } from '../i18n/languages';

export interface SearchDocument {
  id: string;
  type: string;
  title: string;
  body: string;
  path: string;
  meta: string;
  keywords: string;
}

function truncate(text: string, maxLength: number): string {
  const trimmed = text.trim().replace(/\n/g, ' ');
  if (trimmed.length <= maxLength) return trimmed;
  return trimmed.slice(0, maxLength).trimEnd() + '...';
}

/**
 * Pick a multilingual string for the given locale, falling back to English.
 */
function pick(value: { en?: string; fr?: string; es?: string } | undefined, locale: Locale): string {
  if (!value) return '';
  return value[locale] ?? value[defaultLocale] ?? '';
}

/**
 * Build the searchable document list in the requested locale.
 */
export function buildSearchIndex(locale: Locale = defaultLocale): SearchDocument[] {
  const vocab = loadVocabulary();
  const documents: SearchDocument[] = [];

  for (const concept of Object.values(vocab.concepts)) {
    const label = pick(concept.label, locale) || concept.id;
    documents.push({
      id: `concept:${concept.id}`,
      type: 'concept',
      title: label,
      body: truncate(pick(concept.definition, locale), 200),
      path: concept.path,
      meta: concept.domain ? `Domain: ${concept.domain}` : '',
      keywords: [concept.id, ...concept.properties.map((p) => p.id)].join(' '),
    });
  }

  for (const prop of Object.values(vocab.properties)) {
    const usedByList = prop.used_by || [];
    documents.push({
      id: `property:${prop.id}`,
      type: 'property',
      title: prop.id,
      body: truncate(pick(prop.definition, locale), 200),
      path: prop.path,
      meta: usedByList.length > 0 ? `Used by: ${usedByList.join(', ')}` : '',
      keywords: usedByList.join(' '),
    });
  }

  for (const v of Object.values(vocab.vocabularies)) {
    const label = pick(v.label, locale) || v.id;
    const valueLabels: string[] = [];
    if (!v.external_values) {
      for (const val of v.values) {
        const valLabel = pick(val.label, locale);
        if (valLabel) valueLabels.push(valLabel);
      }
    }
    const valueCount = v.values.length;
    documents.push({
      id: `vocab:${v.id}`,
      type: 'vocabulary',
      title: label,
      body: truncate(pick(v.definition, locale), 200),
      path: `/vocabularies/${v.id}`,
      meta: `${valueCount} values`,
      keywords: [v.id, ...valueLabels].join('\t'),
    });
  }

  return documents;
}
