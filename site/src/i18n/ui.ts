import type { Locale } from './languages';

/**
 * UI string dictionary. English is the source of truth. Missing keys in
 * French or Spanish fall back to English via the `t()` function.
 *
 * Long prose pages (homepage, about) use locale-specific Astro content
 * components. This dictionary is for chrome, navigation, and reusable UI labels.
 */
const en = {
  // Navigation and chrome
  'nav.concepts': 'Concepts',
  'nav.properties': 'Properties',
  'nav.vocabularies': 'Vocabularies',
  'nav.about': 'About',
  'nav.menu': 'Menu',
  'nav.search': 'Search',
  'nav.skip_to_content': 'Skip to main content',
  'nav.back_to_top': 'Back to top',

  // Language switcher
  'lang.switch_to': 'Switch language to {language}',
  'lang.current': 'Current language: {language}',
  'lang.menu_label': 'Language',

  // Search UI
  'search.placeholder': 'Search concepts, properties...',
  'search.min_chars': 'Type at least 2 characters to search',
  'search.no_results': 'No results for',
  'search.browse_hint': 'Browse: Concepts, Properties, Vocabularies',
  'search.results_status': '{count} result(s) found',
  'search.no_results_status': 'No results found',
  'search.aria_label': 'Search AidOps',
  'search.close': 'Close search',

  // Footer
  'footer.tagline': 'Common definitions for humanitarian field data.',
  'footer.explore': 'Explore',
  'footer.project': 'Project',
  'footer.about': 'About',
  'footer.source_github': 'Source on GitHub',
  'footer.reference_model_cc': 'Reference model:',
  'footer.code_apache': 'Code:',
  'footer.built_with': 'Built with',
  'footer.publicschema': 'Built on PublicSchema',

  // Breadcrumbs and shared labels
  'breadcrumb.home': 'Home',
  'common.concepts': 'Concepts',
  'common.properties': 'Properties',
  'common.vocabularies': 'Vocabularies',

  // Concepts index
  'concepts.page_title': 'Concepts',
  'concepts.page_subtitle': 'Structured profiles and entities for humanitarian field data.',
  'concepts.table.concept': 'Concept',
  'concepts.table.definition': 'Definition',
  'concepts.table.maturity': 'Maturity',

  // Properties index
  'properties.page_title': 'Properties',
  'properties.page_subtitle': 'Reusable attributes shared across concepts.',
  'properties.table.property': 'Property',
  'properties.table.type': 'Type',
  'properties.table.used_by': 'Used by',
  'properties.table.definition': 'Definition',

  // Vocabularies index
  'vocab.page_title': 'Vocabularies',
  'vocab.page_subtitle': 'Controlled value sets, referencing international standards where they exist.',
  'vocab.table.vocabulary': 'Vocabulary',
  'vocab.table.values': 'Values',
  'vocab.table.standard': 'Standard',
  'vocab.table.definition': 'Definition',

  // Vocabulary detail
  'vocab_detail.standard_reference': 'Standard reference',
  'vocab_detail.aligned_standards': 'Aligned standards',
  'vocab_detail.values': 'Values',
  'vocab_detail.external_values_note_prefix': 'This vocabulary is defined by an external standard',
  'vocab_detail.external_values_note_suffix': 'The full list of values is available in the downloads above',
  'vocab_detail.official_standard_page': 'official standard page',
  'vocab_detail.table.code': 'Code',
  'vocab_detail.table.label': 'Label',
  'vocab_detail.table.standard_code': 'Standard code',
  'vocab_detail.table.definition': 'Definition',
  'vocab_detail.no_mapping': 'no equivalent',
  'vocab_detail.references': 'Other references',

  // Concept detail
  'concept_detail.supertypes': 'Supertypes',
  'concept_detail.subtypes': 'Subtypes',
  'concept_detail.properties': 'Properties',
  'concept_detail.no_properties': 'No properties defined yet.',
  'concept_detail.evidence': 'Aligned standards',
  'concept_detail.table.property': 'Property',
  'concept_detail.table.type': 'Type',
  'concept_detail.table.definition': 'Definition',
  'concept_detail.inherited_from': 'from',
  'concept_detail.includes': 'includes',
  'concept_detail.aligned_standards': 'Aligned standards',
  'concept_detail.table.standard': 'Standard',
  'concept_detail.table.equivalent': 'Equivalent',
  'concept_detail.table.match': 'Match',
  'concept_detail.abstract_badge': 'abstract',
  'concept_detail.abstract_title': 'Abstract supertype: exists to group shared properties; instances are recorded as one of its subtypes',

  // Property detail
  'property_detail.details': 'Details',
  'property_detail.type': 'Type',
  'property_detail.cardinality': 'Cardinality',
  'property_detail.vocabulary': 'Vocabulary',
  'property_detail.references': 'References',
  'property_detail.used_by': 'Used by',
  'property_detail.no_uses': 'Not used by any concept yet.',
  'property_detail.age_band.infant_0_1': 'infant 0-1',
  'property_detail.age_band.infant_0_1.range': '0-23 months',
  'property_detail.age_band.child_2_4': 'child 2-4',
  'property_detail.age_band.child_2_4.range': '2-4 years (24-59 months)',
  'property_detail.age_band.child_5_17': 'child 5-17',
  'property_detail.age_band.child_5_17.range': '5-17 years',
  'property_detail.age_band.adolescent': 'adolescent',
  'property_detail.age_band.adolescent.range': '10-19 years (WHO)',
  'property_detail.age_band.adult': 'adult',
  'property_detail.age_band.adult.range': '18+ years',

  // Shared download labels
  'download.jsonld': 'JSON-LD',
  'download.json_schema': 'JSON Schema',
  'download.csv': 'CSV',
  'download.definition_xlsx': 'Definition (Excel)',
  'download.template_xlsx': 'Template (Excel)',

  // Homepage
  'home.browse_schema': 'Browse the schema',
  'home.core_concepts': 'Concepts',
  'home.vocabularies': 'Vocabularies',
  'home.plus_more': '+{count} more',

  // 404
  '404.page_title': 'Page not found',
  '404.message': 'The page you\u2019re looking for doesn\u2019t exist or has been moved.',
  '404.go_home': 'go back to the homepage',
  '404.or_browse': 'or browse',

  // Translation banner
  'banner.not_translated': 'This page is not yet available in your language. The content below is in English.',
  'banner.dismiss': 'Dismiss',

  // Feedback
  'feedback.section_aria': 'Report an issue with this section',
  'feedback.page_link': 'See a problem on this page? Report it on GitHub.',
  'feedback.orientation_title': 'Help improve this page',
  'feedback.orientation_github': 'If you have a GitHub account, click the feedback icon next to any section heading to report a specific issue.',
  'feedback.banner_draft': 'This definition is still taking shape. Your input helps us get it right.',
  'feedback.banner_candidate': 'Nearly final. We are welcoming a last round of feedback before locking this in.',
  'feedback.banner_comment': 'Comment on this page',
  'feedback.banner_github': 'Open a GitHub issue',
  'feedback.banner_trigger_aria': 'Open comments sidebar',

  // References
  'references.referenced_by': 'Referenced by this concept',
  'references.referenced_by_vocab': 'Referenced by this vocabulary',
  'references.see_all': 'See full reference catalogue',
};

type Dict = typeof en;

export const ui: Record<Locale, Partial<Dict>> = {
  en,
  fr: {
    // Navigation and chrome
    'nav.concepts': 'Concepts',
    'nav.properties': 'Propriétés',
    'nav.vocabularies': 'Vocabulaires',
    'nav.about': 'À propos',
    'nav.menu': 'Menu',
    'nav.search': 'Rechercher',
    'nav.skip_to_content': 'Aller au contenu principal',
    'nav.back_to_top': 'Retour en haut',

    // Language switcher
    'lang.switch_to': 'Passer en {language}',
    'lang.current': 'Langue actuelle : {language}',
    'lang.menu_label': 'Langue',

    // Search UI
    'search.placeholder': 'Rechercher des concepts, des propriétés...',
    'search.min_chars': 'Saisissez au moins 2 caractères pour rechercher',
    'search.no_results': 'Aucun résultat pour',
    'search.browse_hint': 'Parcourir : Concepts, Propriétés, Vocabulaires',
    'search.results_status': '{count} résultat(s) trouvé(s)',
    'search.no_results_status': 'Aucun résultat trouvé',
    'search.aria_label': 'Rechercher sur AidOps',
    'search.close': 'Fermer la recherche',

    // Footer
    'footer.tagline': 'Définitions communes pour les données humanitaires de terrain.',
    'footer.explore': 'Explorer',
    'footer.project': 'Projet',
    'footer.about': 'À propos',
    'footer.source_github': 'Source sur GitHub',
    'footer.reference_model_cc': 'Modèle de référence :',
    'footer.code_apache': 'Code :',
    'footer.built_with': 'Réalisé avec',
    'footer.publicschema': 'Fondé sur PublicSchema',

    // Breadcrumbs and shared labels
    'breadcrumb.home': 'Accueil',
    'common.concepts': 'Concepts',
    'common.properties': 'Propriétés',
    'common.vocabularies': 'Vocabulaires',

    // Concepts index
    'concepts.page_title': 'Concepts',
    'concepts.page_subtitle': 'Profils structurés et entités pour les données humanitaires de terrain.',
    'concepts.table.concept': 'Concept',
    'concepts.table.definition': 'Définition',
    'concepts.table.maturity': 'Maturité',

    // Properties index
    'properties.page_title': 'Propriétés',
    'properties.page_subtitle': 'Attributs réutilisables partagés entre les concepts.',
    'properties.table.property': 'Propriété',
    'properties.table.type': 'Type',
    'properties.table.used_by': 'Utilisée par',
    'properties.table.definition': 'Définition',

    // Vocabularies index
    'vocab.page_title': 'Vocabulaires',
    'vocab.page_subtitle': 'Ensembles de valeurs contrôlées, faisant référence aux normes internationales lorsqu\'elles existent.',
    'vocab.table.vocabulary': 'Vocabulaire',
    'vocab.table.values': 'Valeurs',
    'vocab.table.standard': 'Norme',
    'vocab.table.definition': 'Définition',

    // Vocabulary detail
    'vocab_detail.standard_reference': 'Référence normative',
    'vocab_detail.aligned_standards': 'Normes alignées',
    'vocab_detail.values': 'Valeurs',
    'vocab_detail.external_values_note_prefix': 'Ce vocabulaire est défini par une norme externe',
    'vocab_detail.external_values_note_suffix': 'La liste complète des valeurs est accessible via les liens de téléchargement ci-dessus',
    'vocab_detail.official_standard_page': 'page officielle de la norme',
    'vocab_detail.table.code': 'Code',
    'vocab_detail.table.label': 'Libellé',
    'vocab_detail.table.standard_code': 'Code normalisé',
    'vocab_detail.table.definition': 'Définition',
    'vocab_detail.no_mapping': 'aucun équivalent',
    'vocab_detail.references': 'Autres références',

    // Concept detail
    'concept_detail.supertypes': 'Super-types',
    'concept_detail.subtypes': 'Sous-types',
    'concept_detail.properties': 'Propriétés',
    'concept_detail.no_properties': 'Aucune propriété définie pour l\'instant.',
    'concept_detail.evidence': 'Normes alignées',
    'concept_detail.table.property': 'Propriété',
    'concept_detail.table.type': 'Type',
    'concept_detail.table.definition': 'Définition',
    'concept_detail.inherited_from': 'de',
    'concept_detail.includes': 'comprend',
    'concept_detail.aligned_standards': 'Normes alignées',
    'concept_detail.table.standard': 'Norme',
    'concept_detail.table.equivalent': 'Équivalent',
    'concept_detail.table.match': 'Correspondance',
    'concept_detail.abstract_badge': 'abstrait',
    'concept_detail.abstract_title': 'Supertype abstrait : regroupe des propriétés partagées ; les instances sont enregistrées sous l\'un de ses sous-types.',

    // Property detail
    'property_detail.details': 'Détails',
    'property_detail.type': 'Type',
    'property_detail.cardinality': 'Cardinalité',
    'property_detail.vocabulary': 'Vocabulaire',
    'property_detail.references': 'Références',
    'property_detail.used_by': 'Utilisée par',
    'property_detail.no_uses': 'Pas encore utilisée par aucun concept.',
    'property_detail.age_band.infant_0_1': 'nourrisson 0-1',
    'property_detail.age_band.infant_0_1.range': '0-23 mois',
    'property_detail.age_band.child_2_4': 'enfant 2-4',
    'property_detail.age_band.child_2_4.range': '2-4 ans (24-59 mois)',
    'property_detail.age_band.child_5_17': 'enfant 5-17',
    'property_detail.age_band.child_5_17.range': '5-17 ans',
    'property_detail.age_band.adolescent': 'adolescent',
    'property_detail.age_band.adolescent.range': '10-19 ans (OMS)',
    'property_detail.age_band.adult': 'adulte',
    'property_detail.age_band.adult.range': '18 ans et plus',

    // Shared download labels
    'download.jsonld': 'JSON-LD',
    'download.json_schema': 'JSON Schema',
    'download.csv': 'CSV',
    'download.definition_xlsx': 'Définition (Excel)',
    'download.template_xlsx': 'Modèle (Excel)',

    // Homepage
    'home.browse_schema': 'Explorer le schéma',
    'home.core_concepts': 'Concepts',
    'home.vocabularies': 'Vocabulaires',
    'home.plus_more': '+{count} de plus',

    // 404
    '404.page_title': 'Page introuvable',
    '404.message': 'La page que vous recherchez n\'existe pas ou a été déplacée.',
    '404.go_home': 'revenir à la page d\'accueil',
    '404.or_browse': 'ou parcourir',

    // Translation banner
    'banner.not_translated': 'Cette page n\'est pas encore disponible dans votre langue. Le contenu ci-dessous est en anglais.',
    'banner.dismiss': 'Fermer',

    // Feedback
    'feedback.section_aria': 'Signaler un problème dans cette section',
    'feedback.page_link': 'Vous voyez un problème sur cette page ? Signalez-le sur GitHub.',
    'feedback.orientation_title': 'Aidez-nous à améliorer cette page',
    'feedback.orientation_github': 'Si vous avez un compte GitHub, cliquez sur l\'icône à côté de chaque titre de section pour signaler un problème précis.',
    'feedback.banner_draft': 'Cette définition est encore en construction. Vos retours nous aident à la préciser.',
    'feedback.banner_candidate': 'Presque finalisée. Nous recueillons un dernier tour de retours avant de la figer.',
    'feedback.banner_comment': 'Commenter cette page',
    'feedback.banner_github': 'Ouvrir un ticket GitHub',
    'feedback.banner_trigger_aria': 'Ouvrir le panneau de commentaires',

    // References
    'references.referenced_by': 'Référencé par ce concept',
    'references.referenced_by_vocab': 'Référencé par ce vocabulaire',
    'references.see_all': 'Voir le catalogue complet des références',
  },
  es: {
    // Navigation and chrome
    'nav.concepts': 'Conceptos',
    'nav.properties': 'Propiedades',
    'nav.vocabularies': 'Vocabularios',
    'nav.about': 'Acerca de',
    'nav.menu': 'Menú',
    'nav.search': 'Buscar',
    'nav.skip_to_content': 'Ir al contenido principal',
    'nav.back_to_top': 'Volver arriba',

    // Language switcher
    'lang.switch_to': 'Cambiar idioma a {language}',
    'lang.current': 'Idioma actual: {language}',
    'lang.menu_label': 'Idioma',

    // Search UI
    'search.placeholder': 'Buscar conceptos, propiedades...',
    'search.min_chars': 'Escriba al menos 2 caracteres para buscar',
    'search.no_results': 'Ningún resultado para',
    'search.browse_hint': 'Explorar: Conceptos, Propiedades, Vocabularios',
    'search.results_status': '{count} resultado(s) encontrado(s)',
    'search.no_results_status': 'No se encontraron resultados',
    'search.aria_label': 'Buscar en AidOps',
    'search.close': 'Cerrar búsqueda',

    // Footer
    'footer.tagline': 'Definiciones comunes para datos humanitarios de campo.',
    'footer.explore': 'Explorar',
    'footer.project': 'Proyecto',
    'footer.about': 'Acerca de',
    'footer.source_github': 'Repositorio en GitHub',
    'footer.reference_model_cc': 'Modelo de referencia:',
    'footer.code_apache': 'Código:',
    'footer.built_with': 'Desarrollado con',
    'footer.publicschema': 'Construido sobre PublicSchema',

    // Breadcrumbs and shared labels
    'breadcrumb.home': 'Inicio',
    'common.concepts': 'Conceptos',
    'common.properties': 'Propiedades',
    'common.vocabularies': 'Vocabularios',

    // Concepts index
    'concepts.page_title': 'Conceptos',
    'concepts.page_subtitle': 'Perfiles estructurados y entidades para datos humanitarios de campo.',
    'concepts.table.concept': 'Concepto',
    'concepts.table.definition': 'Definición',
    'concepts.table.maturity': 'Madurez',

    // Properties index
    'properties.page_title': 'Propiedades',
    'properties.page_subtitle': 'Atributos reutilizables compartidos entre conceptos.',
    'properties.table.property': 'Propiedad',
    'properties.table.type': 'Tipo',
    'properties.table.used_by': 'Utilizada por',
    'properties.table.definition': 'Definición',

    // Vocabularies index
    'vocab.page_title': 'Vocabularios',
    'vocab.page_subtitle': 'Conjuntos de valores controlados, con referencia a normas internacionales cuando existen.',
    'vocab.table.vocabulary': 'Vocabulario',
    'vocab.table.values': 'Valores',
    'vocab.table.standard': 'Norma',
    'vocab.table.definition': 'Definición',

    // Vocabulary detail
    'vocab_detail.standard_reference': 'Referencia normativa',
    'vocab_detail.aligned_standards': 'Normas alineadas',
    'vocab_detail.values': 'Valores',
    'vocab_detail.external_values_note_prefix': 'Este vocabulario está definido por una norma externa',
    'vocab_detail.external_values_note_suffix': 'La lista completa de valores está disponible en la sección de descargas',
    'vocab_detail.official_standard_page': 'página oficial de la norma',
    'vocab_detail.table.code': 'Código',
    'vocab_detail.table.label': 'Etiqueta',
    'vocab_detail.table.standard_code': 'Código normalizado',
    'vocab_detail.table.definition': 'Definición',
    'vocab_detail.no_mapping': 'sin equivalente',
    'vocab_detail.references': 'Otras referencias',

    // Concept detail
    'concept_detail.supertypes': 'Supertipos',
    'concept_detail.subtypes': 'Subtipos',
    'concept_detail.properties': 'Propiedades',
    'concept_detail.no_properties': 'No hay propiedades definidas aún.',
    'concept_detail.evidence': 'Normas alineadas',
    'concept_detail.table.property': 'Propiedad',
    'concept_detail.table.type': 'Tipo',
    'concept_detail.table.definition': 'Definición',
    'concept_detail.inherited_from': 'de',
    'concept_detail.includes': 'incluye',
    'concept_detail.aligned_standards': 'Normas alineadas',
    'concept_detail.table.standard': 'Norma',
    'concept_detail.table.equivalent': 'Equivalente',
    'concept_detail.table.match': 'Correspondencia',
    'concept_detail.abstract_badge': 'abstracto',
    'concept_detail.abstract_title': 'Supertipo abstracto: existe para agrupar propiedades compartidas; las instancias se registran como uno de sus subtipos',

    // Property detail
    'property_detail.details': 'Detalles',
    'property_detail.type': 'Tipo',
    'property_detail.cardinality': 'Cardinalidad',
    'property_detail.vocabulary': 'Vocabulario',
    'property_detail.references': 'Referencias',
    'property_detail.used_by': 'Utilizada por',
    'property_detail.no_uses': 'Aún no utilizada por ningún concepto.',
    'property_detail.age_band.infant_0_1': 'lactante 0-1',
    'property_detail.age_band.infant_0_1.range': '0-23 meses',
    'property_detail.age_band.child_2_4': 'niño 2-4',
    'property_detail.age_band.child_2_4.range': '2-4 años (24-59 meses)',
    'property_detail.age_band.child_5_17': 'niño 5-17',
    'property_detail.age_band.child_5_17.range': '5-17 años',
    'property_detail.age_band.adolescent': 'adolescente',
    'property_detail.age_band.adolescent.range': '10-19 años (OMS)',
    'property_detail.age_band.adult': 'adulto',
    'property_detail.age_band.adult.range': '18 años o más',

    // Shared download labels
    'download.jsonld': 'JSON-LD',
    'download.json_schema': 'JSON Schema',
    'download.csv': 'CSV',
    'download.definition_xlsx': 'Definición (Excel)',
    'download.template_xlsx': 'Plantilla (Excel)',

    // Homepage
    'home.browse_schema': 'Explorar el esquema',
    'home.core_concepts': 'Conceptos',
    'home.vocabularies': 'Vocabularios',
    'home.plus_more': '+{count} más',

    // 404
    '404.page_title': 'Página no encontrada',
    '404.message': 'La página que busca no existe o ha sido movida.',
    '404.go_home': 'volver a la página de inicio',
    '404.or_browse': 'o explorar',

    // Translation banner
    'banner.not_translated': 'Esta página aún no está disponible en español. El contenido a continuación está en inglés.',
    'banner.dismiss': 'Cerrar',

    // Feedback
    'feedback.section_aria': 'Reportar un problema en esta sección',
    'feedback.page_link': '¿Ve un problema en esta página? Repórtelo en GitHub.',
    'feedback.orientation_title': 'Ayude a mejorar esta página',
    'feedback.orientation_github': 'Si tiene una cuenta de GitHub, haga clic en el icono junto a cada encabezado de sección para reportar un problema específico.',
    'feedback.banner_draft': 'Esta definición aún está tomando forma. Sus aportes nos ayudan a precisarla.',
    'feedback.banner_candidate': 'Casi final. Estamos abiertos a una última ronda de retroalimentación antes de fijarla.',
    'feedback.banner_comment': 'Comentar esta página',
    'feedback.banner_github': 'Abrir un ticket en GitHub',
    'feedback.banner_trigger_aria': 'Abrir el panel de comentarios',

    // References
    'references.referenced_by': 'Referenciado por este concepto',
    'references.referenced_by_vocab': 'Referenciado por este vocabulario',
    'references.see_all': 'Ver el catálogo completo de referencias',
  },
};
