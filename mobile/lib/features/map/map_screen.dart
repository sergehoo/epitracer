import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/models/health_facility.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/widgets/glass_card.dart';
import '../../shared/widgets/offline_banner.dart';
import 'facilities_repository.dart';

class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  final _mapCtrl = MapController();
  final Set<FacilityType> _activeTypes = {...FacilityType.values};
  LatLng? _myLocation;
  HealthFacility? _selected;

  // Centre par défaut : Côte d'Ivoire (Yamoussoukro ~ centre géo)
  static const _defaultCenter = LatLng(7.55, -5.55);
  static const _defaultZoom = 6.5;

  @override
  void initState() {
    super.initState();
    _tryGetLocation();
  }

  Future<void> _tryGetLocation() async {
    try {
      // 1. Vérifie que le service de localisation est actif
      final enabled = await Geolocator.isLocationServiceEnabled();
      if (!enabled) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
                'Activez la localisation dans les paramètres système.'),
          ),
        );
        return;
      }

      // 2. Demande la permission (Android + iOS)
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.deniedForever) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                const Text('Permission refusée définitivement.'),
            action: SnackBarAction(
              label: 'Réglages',
              onPressed: () => Geolocator.openAppSettings(),
            ),
          ),
        );
        return;
      }
      if (perm == LocationPermission.denied) return;

      // 3. Récupère la position (timeout 10s)
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 10),
        ),
      );
      if (!mounted) return;
      setState(() => _myLocation = LatLng(pos.latitude, pos.longitude));
      _mapCtrl.move(_myLocation!, 12);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Géolocalisation indisponible : $e')),
      );
    }
  }

  Color _markerColor(FacilityType type) {
    switch (type) {
      case FacilityType.chu:
        return AppColors.statusDanger;
      case FacilityType.hospital:
        return AppColors.ciOrange;
      case FacilityType.dispensary:
        return AppColors.ciGreen;
      case FacilityType.pharmacy:
        return AppColors.statusInfo;
      case FacilityType.vaccinationCenter:
        return AppColors.inhpBlue;
      case FacilityType.clinic:
        return AppColors.statusOk;
    }
  }

  IconData _markerIcon(FacilityType type) {
    switch (type) {
      case FacilityType.chu:
        return Icons.local_hospital;
      case FacilityType.hospital:
        return Icons.medical_services;
      case FacilityType.dispensary:
        return Icons.healing;
      case FacilityType.pharmacy:
        return Icons.local_pharmacy;
      case FacilityType.vaccinationCenter:
        return Icons.vaccines;
      case FacilityType.clinic:
        return Icons.health_and_safety;
    }
  }

  HealthFacility? _nearest(List<HealthFacility> all) {
    if (_myLocation == null || all.isEmpty) return null;
    final dist = Distance();
    HealthFacility? best;
    double bestKm = double.infinity;
    for (final f in all) {
      final km = dist.as(LengthUnit.Kilometer, _myLocation!, LatLng(f.lat, f.lng));
      if (km < bestKm) {
        bestKm = km;
        best = f;
      }
    }
    return best;
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(facilitiesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Centres de santé'),
        actions: [
          IconButton(
            icon: const Icon(Icons.my_location),
            tooltip: 'Ma position',
            onPressed: _tryGetLocation,
          ),
        ],
      ),
      body: Stack(
        children: [
          async.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => const Center(child: Text('Erreur de chargement')),
            data: (all) {
              final filtered =
                  all.where((f) => _activeTypes.contains(f.type)).toList();
              final markers = filtered.map((f) {
                return Marker(
                  point: LatLng(f.lat, f.lng),
                  width: 44,
                  height: 44,
                  child: GestureDetector(
                    onTap: () => setState(() => _selected = f),
                    child: Container(
                      decoration: BoxDecoration(
                        color: _markerColor(f.type),
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 3),
                        boxShadow: [
                          BoxShadow(
                            color: _markerColor(f.type).withValues(alpha: 0.5),
                            blurRadius: 8,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                      child: Icon(_markerIcon(f.type),
                          color: Colors.white, size: 22),
                    ),
                  ),
                );
              }).toList();

              if (_myLocation != null) {
                markers.add(Marker(
                  point: _myLocation!,
                  width: 22,
                  height: 22,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.blue,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 3),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.blue.withValues(alpha: 0.5),
                          blurRadius: 10,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                  ),
                ));
              }

              return FlutterMap(
                mapController: _mapCtrl,
                options: const MapOptions(
                  initialCenter: _defaultCenter,
                  initialZoom: _defaultZoom,
                  minZoom: 5,
                  maxZoom: 18,
                ),
                children: [
                  TileLayer(
                    urlTemplate:
                        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.veillesanitaire.monpasssanitaire',
                  ),
                  MarkerLayer(markers: markers),
                ],
              );
            },
          ),

          // Bandeau offline en haut
          const Align(
            alignment: Alignment.topCenter,
            child: OfflineBanner(),
          ),

          // Filtres en bas
          Positioned(
            left: 12,
            right: 12,
            bottom: 12,
            child: Column(
              children: [
                if (_selected != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _FacilityCard(
                      facility: _selected!,
                      onClose: () => setState(() => _selected = null),
                      onNavigate: () => _openInMaps(_selected!),
                      onCall: () => _call(_selected!.phone),
                    ),
                  ),
                if (_selected == null && _myLocation != null)
                  async.maybeWhen(
                    data: (all) {
                      final nearest = _nearest(all
                          .where((f) => _activeTypes.contains(f.type))
                          .toList());
                      if (nearest == null) return const SizedBox.shrink();
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _NearestPill(
                          facility: nearest,
                          onTap: () {
                            setState(() => _selected = nearest);
                            _mapCtrl.move(LatLng(nearest.lat, nearest.lng), 14);
                          },
                        ),
                      );
                    },
                    orElse: () => const SizedBox.shrink(),
                  ),
                _FiltersBar(
                  active: _activeTypes,
                  onToggle: (t) {
                    setState(() {
                      if (_activeTypes.contains(t)) {
                        _activeTypes.remove(t);
                      } else {
                        _activeTypes.add(t);
                      }
                    });
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openInMaps(HealthFacility f) async {
    final uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lng}');
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _call(String? phone) async {
    if (phone == null || phone.isEmpty) return;
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }
}

class _NearestPill extends StatelessWidget {
  const _NearestPill({required this.facility, required this.onTap});
  final HealthFacility facility;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(28),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: AppColors.ciOrange,
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: AppColors.ciOrange.withValues(alpha: 0.35),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.near_me, color: Colors.white, size: 18),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  'Le plus proche : ${facility.name}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FiltersBar extends StatelessWidget {
  const _FiltersBar({required this.active, required this.onToggle});
  final Set<FacilityType> active;
  final ValueChanged<FacilityType> onToggle;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: FacilityType.values.map((t) {
            final on = active.contains(t);
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: FilterChip(
                label: Text(t.label),
                selected: on,
                onSelected: (_) => onToggle(t),
                selectedColor: AppColors.ciOrange.withValues(alpha: 0.2),
                checkmarkColor: AppColors.ciOrange,
                labelStyle: TextStyle(
                  color: on ? AppColors.ciOrange : AppColors.slate700,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

class _FacilityCard extends StatelessWidget {
  const _FacilityCard({
    required this.facility,
    required this.onClose,
    required this.onNavigate,
    required this.onCall,
  });

  final HealthFacility facility;
  final VoidCallback onClose;
  final VoidCallback onNavigate;
  final VoidCallback onCall;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.ciOrange.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.local_hospital,
                    color: AppColors.ciOrange, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(facility.name,
                        style: const TextStyle(
                            fontWeight: FontWeight.w800, fontSize: 15)),
                    Text(
                      '${facility.type.label} · ${facility.city}',
                      style: const TextStyle(
                          color: AppColors.slate500, fontSize: 12),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: onClose,
              ),
            ],
          ),
          if (facility.address != null) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.place_outlined,
                    color: AppColors.slate500, size: 14),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    facility.address!,
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
              ],
            ),
          ],
          if (facility.openHours != null) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.schedule,
                    color: AppColors.slate500, size: 14),
                const SizedBox(width: 6),
                Text(facility.openHours!,
                    style: const TextStyle(fontSize: 12)),
                if (facility.hasEmergency) ...[
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.statusDanger.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'Urgences',
                      style: TextStyle(
                        color: AppColors.statusDanger,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
          if (facility.specialties.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: facility.specialties
                  .map((s) => Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.ciGreen.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          s,
                          style: const TextStyle(
                            color: AppColors.ciGreen,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ))
                  .toList(),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              if (facility.phone != null && facility.phone!.isNotEmpty)
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onCall,
                    icon: const Icon(Icons.phone, size: 16),
                    label: const Text('Appeler'),
                  ),
                ),
              if (facility.phone != null) const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: onNavigate,
                  icon: const Icon(Icons.directions, size: 16),
                  label: const Text('Itinéraire'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
