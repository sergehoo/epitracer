/// Renderer dynamique d'un FormField selon son [FieldKind].
///
/// Phase 8B — supporte text/number/email/phone/date/boolean/select/radio/
/// multiselect/checkbox/country/signature/image/geolocation.
/// Le `qr_scan` et `datetime` sont gérés en best-effort (TODO Phase 8B+).
library;

import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';
import 'package:signature/signature.dart' as sig;

import '../../../core/theme/app_colors.dart';
import 'runner_models.dart';

typedef AnswerSetter = void Function(dynamic value);

class FieldRenderer extends StatelessWidget {
  const FieldRenderer({
    super.key,
    required this.field,
    required this.value,
    required this.error,
    required this.onChanged,
    required this.required,
  });

  final FormFieldSchema field;
  final dynamic value;
  final String? error;
  final AnswerSetter onChanged;
  final bool required;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Label(label: field.label, required: required),
          if (field.helpText.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              field.helpText,
              style: const TextStyle(
                color: AppColors.slate500,
                fontSize: 11,
              ),
            ),
          ],
          const SizedBox(height: 8),
          _control(context),
          if (error != null) ...[
            const SizedBox(height: 6),
            Text(
              error!,
              style: const TextStyle(
                color: AppColors.statusDanger,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _control(BuildContext context) {
    switch (field.kind) {
      case FieldKind.textarea:
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: field.placeholder,
          onChanged: onChanged,
          minLines: 3,
          maxLines: 5,
        );
      case FieldKind.number:
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: field.placeholder,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.,\-]')),
          ],
          onChanged: (v) =>
              onChanged(double.tryParse((v ?? '').replaceAll(',', '.'))),
        );
      case FieldKind.integer:
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: field.placeholder,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          onChanged: (v) => onChanged(int.tryParse(v ?? '')),
        );
      case FieldKind.phone:
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: field.placeholder.isEmpty ? '+225 …' : field.placeholder,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9\+\s\-]')),
          ],
          onChanged: onChanged,
        );
      case FieldKind.email:
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: field.placeholder,
          keyboardType: TextInputType.emailAddress,
          onChanged: onChanged,
        );
      case FieldKind.date:
        return _DateControl(
          value: value?.toString(),
          onChanged: onChanged,
          withTime: false,
        );
      case FieldKind.datetime:
        return _DateControl(
          value: value?.toString(),
          onChanged: onChanged,
          withTime: true,
        );
      case FieldKind.boolean:
        return _BoolControl(
          // `value` peut être null (pas de réponse encore), true ou false.
          // On passe la valeur brute pour distinguer "non répondu" de "Non".
          value: value is bool ? value : null,
          onChanged: onChanged,
        );
      case FieldKind.yesNoUnknown:
        return _RadioControl(
          options: const [
            FormOption(value: 'yes', label: 'Oui'),
            FormOption(value: 'no', label: 'Non'),
            FormOption(value: 'unknown', label: 'Ne sait pas'),
          ],
          value: value?.toString(),
          onChanged: onChanged,
        );
      case FieldKind.radio:
        return _RadioControl(
          options: field.options,
          value: value?.toString(),
          onChanged: onChanged,
        );
      case FieldKind.select:
        return _DropdownControl(
          options: field.options,
          value: value?.toString(),
          placeholder: field.placeholder,
          onChanged: onChanged,
        );
      case FieldKind.multiselect:
      case FieldKind.checkbox:
        return _MultiSelectControl(
          options: field.options,
          values: (value is List)
              ? List<String>.from(value.map((e) => e.toString()))
              : <String>[],
          onChanged: onChanged,
        );
      case FieldKind.country:
        return _CountryControl(
          value: value?.toString(),
          onChanged: onChanged,
        );
      case FieldKind.signature:
        return _SignatureControl(
          value: value?.toString(),
          onChanged: onChanged,
        );
      case FieldKind.image:
      case FieldKind.file:
        return _FileControl(
          value: value?.toString(),
          onChanged: onChanged,
          isImage: field.kind == FieldKind.image,
        );
      case FieldKind.geolocation:
        return _GeolocationControl(
          value: value is Map ? Map<String, dynamic>.from(value) : null,
          onChanged: onChanged,
        );
      case FieldKind.qrScan:
        // TODO Phase 8B+ — intégrer mobile_scanner avec popup modal.
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: 'Coller le code QR ici',
          onChanged: onChanged,
        );
      case FieldKind.text:
      case FieldKind.unknown:
        return _TextControl(
          value: value?.toString() ?? '',
          placeholder: field.placeholder,
          onChanged: onChanged,
        );
    }
  }
}

class _Label extends StatelessWidget {
  const _Label({required this.label, required this.required});
  final String label;
  final bool required;
  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        style: const TextStyle(
          color: AppColors.ciDark,
          fontWeight: FontWeight.w700,
          fontSize: 13,
        ),
        children: [
          TextSpan(text: label),
          if (required)
            const TextSpan(
              text: ' *',
              style: TextStyle(color: AppColors.statusDanger),
            ),
        ],
      ),
    );
  }
}

class _TextControl extends StatefulWidget {
  const _TextControl({
    required this.value,
    required this.onChanged,
    this.placeholder = '',
    this.keyboardType,
    this.inputFormatters,
    this.minLines = 1,
    this.maxLines = 1,
  });

  final String value;
  final String placeholder;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final int minLines;
  final int maxLines;
  final ValueChanged<String?> onChanged;

  @override
  State<_TextControl> createState() => _TextControlState();
}

class _TextControlState extends State<_TextControl> {
  late final TextEditingController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: widget.value);
  }

  @override
  void didUpdateWidget(covariant _TextControl old) {
    super.didUpdateWidget(old);
    // Resynchronise si la valeur externe a changé sans que le user tape
    // (load brouillon, reset par parent).
    if (widget.value != _ctrl.text) {
      _ctrl.value = TextEditingValue(
        text: widget.value,
        selection: TextSelection.collapsed(offset: widget.value.length),
      );
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _ctrl,
      keyboardType: widget.keyboardType,
      inputFormatters: widget.inputFormatters,
      minLines: widget.minLines,
      maxLines: widget.maxLines,
      onChanged: widget.onChanged,
      decoration: InputDecoration(
        hintText: widget.placeholder,
        filled: true,
        fillColor: Colors.white,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.slate200),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.ciGreen, width: 1.5),
        ),
      ),
    );
  }
}

class _DateControl extends StatelessWidget {
  const _DateControl({
    required this.value,
    required this.onChanged,
    required this.withTime,
  });
  final String? value;
  final AnswerSetter onChanged;
  final bool withTime;

  @override
  Widget build(BuildContext context) {
    DateTime? parsed;
    if (value != null && value!.isNotEmpty) {
      parsed = DateTime.tryParse(value!);
    }
    final fmt = withTime
        ? DateFormat('dd/MM/yyyy HH:mm')
        : DateFormat('dd/MM/yyyy');
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () async {
        final now = DateTime.now();
        final picked = await showDatePicker(
          context: context,
          initialDate: parsed ?? now,
          firstDate: DateTime(now.year - 1),
          lastDate: DateTime(now.year + 2),
        );
        if (picked == null) return;
        if (!withTime) {
          onChanged(
              DateFormat('yyyy-MM-dd').format(picked));
          return;
        }
        if (!context.mounted) return;
        final time = await showTimePicker(
          context: context,
          initialTime: TimeOfDay.fromDateTime(parsed ?? now),
        );
        if (time == null) return;
        final dt = DateTime(picked.year, picked.month, picked.day,
            time.hour, time.minute);
        onChanged(dt.toIso8601String());
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.slate200),
        ),
        child: Row(
          children: [
            const Icon(Icons.calendar_month_outlined,
                color: AppColors.ciGreen, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                parsed == null ? 'Choisir une date' : fmt.format(parsed),
                style: TextStyle(
                  color: parsed == null
                      ? AppColors.slate500
                      : AppColors.ciDark,
                ),
              ),
            ),
            const Icon(Icons.arrow_drop_down, color: AppColors.slate500),
          ],
        ),
      ),
    );
  }
}

class _BoolControl extends StatelessWidget {
  const _BoolControl({required this.value, required this.onChanged});
  final bool? value;
  final AnswerSetter onChanged;
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _BoolPill(
            label: 'Oui',
            selected: value == true,
            color: AppColors.ciGreen,
            onTap: () => onChanged(true),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _BoolPill(
            label: 'Non',
            selected: value == false,
            color: AppColors.statusDanger,
            onTap: () => onChanged(false),
          ),
        ),
      ],
    );
  }
}

class _BoolPill extends StatelessWidget {
  const _BoolPill({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? color : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? color : AppColors.slate200,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : AppColors.slate700,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _RadioControl extends StatelessWidget {
  const _RadioControl({
    required this.options,
    required this.value,
    required this.onChanged,
  });
  final List<FormOption> options;
  final String? value;
  final AnswerSetter onChanged;
  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final o in options)
          ChoiceChip(
            label: Text(o.label),
            selected: value == o.value,
            onSelected: (_) => onChanged(o.value),
            selectedColor: AppColors.ciGreen,
            backgroundColor: Colors.white,
            side: BorderSide(
              color: value == o.value
                  ? AppColors.ciGreen
                  : AppColors.slate200,
            ),
            labelStyle: TextStyle(
              color: value == o.value
                  ? Colors.white
                  : AppColors.slate700,
              fontWeight: FontWeight.w700,
            ),
          ),
      ],
    );
  }
}

class _DropdownControl extends StatelessWidget {
  const _DropdownControl({
    required this.options,
    required this.value,
    required this.onChanged,
    this.placeholder = '',
  });
  final List<FormOption> options;
  final String? value;
  final String placeholder;
  final AnswerSetter onChanged;
  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: options.any((o) => o.value == value) ? value : null,
      hint: Text(placeholder.isEmpty ? 'Sélectionner…' : placeholder),
      decoration: InputDecoration(
        filled: true,
        fillColor: Colors.white,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.slate200),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.ciGreen, width: 1.5),
        ),
      ),
      items: [
        for (final o in options)
          DropdownMenuItem(value: o.value, child: Text(o.label)),
      ],
      onChanged: (v) => onChanged(v),
    );
  }
}

class _MultiSelectControl extends StatelessWidget {
  const _MultiSelectControl({
    required this.options,
    required this.values,
    required this.onChanged,
  });
  final List<FormOption> options;
  final List<String> values;
  final AnswerSetter onChanged;
  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final o in options)
          FilterChip(
            label: Text(o.label),
            selected: values.contains(o.value),
            onSelected: (sel) {
              final next = List<String>.from(values);
              if (sel) {
                if (!next.contains(o.value)) next.add(o.value);
              } else {
                next.remove(o.value);
              }
              onChanged(next);
            },
            selectedColor: AppColors.ciGreen,
            backgroundColor: Colors.white,
            side: BorderSide(
              color: values.contains(o.value)
                  ? AppColors.ciGreen
                  : AppColors.slate200,
            ),
            labelStyle: TextStyle(
              color: values.contains(o.value)
                  ? Colors.white
                  : AppColors.slate700,
              fontWeight: FontWeight.w700,
            ),
          ),
      ],
    );
  }
}

/// Pays — pour l'instant on liste un sous-ensemble courant. À enrichir
/// quand on aura un endpoint /api/v1/geo/countries/ accessible public.
const List<FormOption> _kCountries = [
  FormOption(value: 'CI', label: 'Côte d\'Ivoire'),
  FormOption(value: 'CD', label: 'République démocratique du Congo'),
  FormOption(value: 'CG', label: 'République du Congo'),
  FormOption(value: 'GN', label: 'Guinée'),
  FormOption(value: 'LR', label: 'Libéria'),
  FormOption(value: 'SL', label: 'Sierra Leone'),
  FormOption(value: 'ML', label: 'Mali'),
  FormOption(value: 'BF', label: 'Burkina Faso'),
  FormOption(value: 'GH', label: 'Ghana'),
  FormOption(value: 'SN', label: 'Sénégal'),
  FormOption(value: 'NG', label: 'Nigéria'),
  FormOption(value: 'FR', label: 'France'),
  FormOption(value: 'BE', label: 'Belgique'),
  FormOption(value: 'US', label: 'États-Unis'),
  FormOption(value: 'CA', label: 'Canada'),
  FormOption(value: 'GB', label: 'Royaume-Uni'),
  FormOption(value: 'DE', label: 'Allemagne'),
  FormOption(value: 'ES', label: 'Espagne'),
  FormOption(value: 'CN', label: 'Chine'),
  FormOption(value: 'AE', label: 'Émirats arabes unis'),
  FormOption(value: 'MA', label: 'Maroc'),
  FormOption(value: 'OTHER', label: 'Autre…'),
];

class _CountryControl extends StatelessWidget {
  const _CountryControl({required this.value, required this.onChanged});
  final String? value;
  final AnswerSetter onChanged;
  @override
  Widget build(BuildContext context) {
    return _DropdownControl(
      options: _kCountries,
      value: value,
      onChanged: onChanged,
    );
  }
}

class _SignatureControl extends StatefulWidget {
  const _SignatureControl({required this.value, required this.onChanged});
  final String? value;
  final AnswerSetter onChanged;

  @override
  State<_SignatureControl> createState() => _SignatureControlState();
}

class _SignatureControlState extends State<_SignatureControl> {
  late final sig.SignatureController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = sig.SignatureController(
      penStrokeWidth: 2,
      penColor: AppColors.ciDark,
      exportBackgroundColor: Colors.white,
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final bytes = await _ctrl.toPngBytes();
    if (bytes == null || bytes.isEmpty) return;
    final b64 = base64Encode(bytes);
    widget.onChanged('data:image/png;base64,$b64');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Signature enregistrée.')),
      );
    }
  }

  void _clear() {
    _ctrl.clear();
    widget.onChanged(null);
  }

  @override
  Widget build(BuildContext context) {
    final hasValue =
        widget.value != null && widget.value!.startsWith('data:image');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          height: 180,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: hasValue ? AppColors.ciGreen : AppColors.slate200,
              width: hasValue ? 1.5 : 1,
            ),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: sig.Signature(
              controller: _ctrl,
              backgroundColor: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _clear,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Effacer'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.statusDanger,
                  side: const BorderSide(color: AppColors.statusDanger),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: ElevatedButton.icon(
                onPressed: _save,
                icon: const Icon(Icons.check, size: 16),
                label: const Text('Valider'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.ciGreen,
                  foregroundColor: Colors.white,
                ),
              ),
            ),
          ],
        ),
        if (hasValue) ...[
          const SizedBox(height: 6),
          const Text(
            'Signature capturée.',
            style: TextStyle(color: AppColors.ciGreen, fontSize: 12),
          ),
        ],
      ],
    );
  }
}

class _FileControl extends StatelessWidget {
  const _FileControl({
    required this.value,
    required this.onChanged,
    required this.isImage,
  });
  final String? value;
  final AnswerSetter onChanged;
  final bool isImage;

  Future<void> _pick(BuildContext context) async {
    final res = await FilePicker.platform.pickFiles(
      type: isImage ? FileType.image : FileType.any,
      withData: true,
    );
    if (res == null || res.files.isEmpty) return;
    final file = res.files.single;
    final bytes = file.bytes ??
        (file.path != null ? await File(file.path!).readAsBytes() : null);
    if (bytes == null) return;
    // On encode en base64 (data URL) — l'endpoint backend décode déjà ce
    // format pour la signature ; futur upload binaire à finaliser.
    final mime = isImage ? 'image/png' : 'application/octet-stream';
    final b64 = base64Encode(bytes);
    onChanged('data:$mime;name=${file.name};base64,$b64');
  }

  @override
  Widget build(BuildContext context) {
    final hasFile = (value ?? '').startsWith('data:');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        OutlinedButton.icon(
          onPressed: () => _pick(context),
          icon: Icon(isImage
              ? Icons.image_outlined
              : Icons.attach_file),
          label: Text(hasFile
              ? 'Remplacer le fichier'
              : (isImage ? 'Ajouter une image' : 'Ajouter un fichier')),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 12),
            foregroundColor: AppColors.ciGreen,
            side: const BorderSide(color: AppColors.ciGreen),
          ),
        ),
        if (hasFile) ...[
          const SizedBox(height: 6),
          const Text(
            'Fichier joint.',
            style: TextStyle(color: AppColors.ciGreen, fontSize: 12),
          ),
        ],
      ],
    );
  }
}

class _GeolocationControl extends StatefulWidget {
  const _GeolocationControl({required this.value, required this.onChanged});
  final Map<String, dynamic>? value;
  final AnswerSetter onChanged;

  @override
  State<_GeolocationControl> createState() => _GeolocationControlState();
}

class _GeolocationControlState extends State<_GeolocationControl> {
  bool _loading = false;
  String? _error;

  Future<void> _capture() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        throw 'Permission de localisation refusée.';
      }
      final pos = await Geolocator.getCurrentPosition();
      widget.onChanged({'lat': pos.latitude, 'lng': pos.longitude});
    } catch (e) {
      // PII-safe : on n'inclut PAS la position dans le log/erreur affichée.
      setState(() => _error = 'Impossible de récupérer la position.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.value;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        OutlinedButton.icon(
          onPressed: _loading ? null : _capture,
          icon: const Icon(Icons.my_location),
          label: Text(_loading
              ? 'Recherche…'
              : (v == null ? 'Capturer ma position' : 'Mettre à jour')),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 12),
            foregroundColor: AppColors.ciGreen,
            side: const BorderSide(color: AppColors.ciGreen),
          ),
        ),
        if (v != null) ...[
          const SizedBox(height: 6),
          Text(
            'Lat ${(v['lat'] as num?)?.toStringAsFixed(4) ?? '—'} • '
            'Lng ${(v['lng'] as num?)?.toStringAsFixed(4) ?? '—'}',
            style: const TextStyle(color: AppColors.ciGreen, fontSize: 12),
          ),
        ],
        if (_error != null) ...[
          const SizedBox(height: 6),
          Text(
            _error!,
            style: const TextStyle(color: AppColors.statusDanger, fontSize: 12),
          ),
        ],
      ],
    );
  }
}
