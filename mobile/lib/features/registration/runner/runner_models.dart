/// Modèles Dart pour le moteur de rendu DynamicForm (Phase 8B).
///
/// Reflète le serializer backend `DynamicFormSerializer` :
///   form.sections[*].fields_list[*].options[*]
library;

/// Type de champ — miroir exact de `apps.forms.models.FieldType`.
enum FieldKind {
  text,
  textarea,
  number,
  integer,
  phone,
  email,
  date,
  datetime,
  boolean,
  select,
  multiselect,
  radio,
  checkbox,
  geolocation,
  qrScan,
  image,
  file,
  signature,
  country,
  yesNoUnknown,
  unknown;

  static FieldKind fromBackend(String raw) {
    switch (raw) {
      case 'text':
        return FieldKind.text;
      case 'textarea':
        return FieldKind.textarea;
      case 'number':
        return FieldKind.number;
      case 'integer':
        return FieldKind.integer;
      case 'phone':
        return FieldKind.phone;
      case 'email':
        return FieldKind.email;
      case 'date':
        return FieldKind.date;
      case 'datetime':
        return FieldKind.datetime;
      case 'boolean':
        return FieldKind.boolean;
      case 'select':
        return FieldKind.select;
      case 'multiselect':
        return FieldKind.multiselect;
      case 'radio':
        return FieldKind.radio;
      case 'checkbox':
        return FieldKind.checkbox;
      case 'geolocation':
        return FieldKind.geolocation;
      case 'qr_scan':
        return FieldKind.qrScan;
      case 'image':
        return FieldKind.image;
      case 'file':
        return FieldKind.file;
      case 'signature':
        return FieldKind.signature;
      case 'country':
        return FieldKind.country;
      case 'yes_no_unknown':
        return FieldKind.yesNoUnknown;
      default:
        return FieldKind.unknown;
    }
  }
}

class FormOption {
  const FormOption({
    required this.value,
    required this.label,
    this.order = 0,
  });

  final String value;
  final String label;
  final int order;

  factory FormOption.fromJson(Map<String, dynamic> j) => FormOption(
        value: (j['value'] ?? '').toString(),
        label: (j['label'] ?? '').toString(),
        order: (j['order'] as num?)?.toInt() ?? 0,
      );
}

class FormCondition {
  const FormCondition({
    required this.dependsOn,
    required this.operator,
    required this.expectedValue,
    required this.action,
  });

  final int dependsOn;
  final String operator;
  final String expectedValue;
  final String action; // show / hide / require

  factory FormCondition.fromJson(Map<String, dynamic> j) => FormCondition(
        dependsOn: (j['depends_on'] as num?)?.toInt() ?? 0,
        operator: (j['operator'] ?? 'eq').toString(),
        expectedValue: (j['expected_value'] ?? '').toString(),
        action: (j['action'] ?? 'show').toString(),
      );
}

class FormFieldSchema {
  const FormFieldSchema({
    required this.id,
    required this.code,
    required this.label,
    required this.kind,
    required this.isRequired,
    required this.order,
    required this.options,
    required this.conditions,
    this.helpText = '',
    this.placeholder = '',
    this.minValue,
    this.maxValue,
    this.minLength,
    this.maxLength,
    this.regex = '',
    this.defaultValue = '',
  });

  final int id;
  final String code;
  final String label;
  final FieldKind kind;
  final bool isRequired;
  final int order;
  final List<FormOption> options;
  final List<FormCondition> conditions;
  final String helpText;
  final String placeholder;
  final double? minValue;
  final double? maxValue;
  final int? minLength;
  final int? maxLength;
  final String regex;
  final String defaultValue;

  factory FormFieldSchema.fromJson(Map<String, dynamic> j) {
    final opts = (j['options'] as List?) ?? const [];
    final conds = (j['conditions'] as List?) ?? const [];
    return FormFieldSchema(
      id: (j['id'] as num?)?.toInt() ?? 0,
      code: (j['code'] ?? '').toString(),
      label: (j['label'] ?? '').toString(),
      kind: FieldKind.fromBackend((j['type'] ?? '').toString()),
      isRequired: j['is_required'] == true,
      order: (j['order'] as num?)?.toInt() ?? 0,
      options: opts
          .whereType<Map<String, dynamic>>()
          .map(FormOption.fromJson)
          .toList()
        ..sort((a, b) => a.order.compareTo(b.order)),
      conditions: conds
          .whereType<Map<String, dynamic>>()
          .map(FormCondition.fromJson)
          .toList(),
      helpText: (j['help_text'] ?? '').toString(),
      placeholder: (j['placeholder'] ?? '').toString(),
      minValue: (j['min_value'] as num?)?.toDouble(),
      maxValue: (j['max_value'] as num?)?.toDouble(),
      minLength: (j['min_length'] as num?)?.toInt(),
      maxLength: (j['max_length'] as num?)?.toInt(),
      regex: (j['regex'] ?? '').toString(),
      defaultValue: (j['default_value'] ?? '').toString(),
    );
  }
}

class FormSectionSchema {
  const FormSectionSchema({
    required this.id,
    required this.code,
    required this.title,
    required this.order,
    required this.fields,
    this.description = '',
  });

  final int id;
  final String code;
  final String title;
  final String description;
  final int order;
  final List<FormFieldSchema> fields;

  factory FormSectionSchema.fromJson(Map<String, dynamic> j) {
    final fields = ((j['fields_list'] as List?) ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(FormFieldSchema.fromJson)
        .toList()
      ..sort((a, b) => a.order.compareTo(b.order));
    return FormSectionSchema(
      id: (j['id'] as num?)?.toInt() ?? 0,
      code: (j['code'] ?? '').toString(),
      title: (j['title'] ?? '').toString(),
      description: (j['description'] ?? '').toString(),
      order: (j['order'] as num?)?.toInt() ?? 0,
      fields: fields,
    );
  }
}

class FormSchema {
  const FormSchema({
    required this.id,
    required this.code,
    required this.title,
    required this.version,
    required this.sections,
    this.description = '',
    this.diseaseCode,
  });

  final int? id;
  final String code;
  final String title;
  final String description;
  final int version;
  final String? diseaseCode;
  final List<FormSectionSchema> sections;

  factory FormSchema.fromJson(Map<String, dynamic> j) {
    final sections = ((j['sections'] as List?) ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(FormSectionSchema.fromJson)
        .toList()
      ..sort((a, b) => a.order.compareTo(b.order));
    return FormSchema(
      id: (j['id'] as num?)?.toInt(),
      code: (j['code'] ?? '').toString(),
      title: (j['title'] ?? '').toString(),
      description: (j['description'] ?? '').toString(),
      version: (j['version'] as num?)?.toInt() ?? 1,
      diseaseCode: j['disease_code']?.toString(),
      sections: sections,
    );
  }
}

/// Résultat de la soumission — utilisé par l'écran succès.
class SubmissionResult {
  const SubmissionResult({
    required this.travelerPublicId,
    required this.travelerName,
    required this.passNumber,
    required this.passUuid,
    required this.qrUrl,
    required this.pdfUrl,
    required this.qrToken,
    required this.message,
  });

  final String travelerPublicId;
  final String travelerName;
  final String passNumber;
  final String passUuid;
  final String? qrUrl;
  final String? pdfUrl;
  final String qrToken;
  final String message;

  factory SubmissionResult.fromJson(Map<String, dynamic> j) {
    final t = (j['traveler'] as Map?) ?? const {};
    final p = (j['pass'] as Map?) ?? const {};
    final i = (j['instructions'] as Map?) ?? const {};
    return SubmissionResult(
      travelerPublicId: (t['public_id'] ?? '').toString(),
      travelerName: (t['full_name'] ?? '').toString(),
      passNumber: (p['pass_number'] ?? '').toString(),
      passUuid: (p['uuid'] ?? '').toString(),
      qrUrl: p['qr_url']?.toString(),
      pdfUrl: p['pdf_url']?.toString(),
      qrToken: (p['qr_token'] ?? '').toString(),
      message: (i['message'] ?? 'Votre pass santé a été délivré.').toString(),
    );
  }
}
