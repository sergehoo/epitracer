import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Bottom navigation premium avec indicateur animé (dot + pill background).
class AppBottomNav extends StatelessWidget {
  const AppBottomNav({
    super.key,
    required this.currentIndex,
    required this.items,
    required this.onTap,
  });

  final int currentIndex;
  final List<AppBottomNavItem> items;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : Colors.white,
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 24,
            offset: const Offset(0, 8),
            spreadRadius: -4,
          ),
        ],
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.slate100,
          width: 1,
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            for (int i = 0; i < items.length; i++)
              _NavTile(
                item: items[i],
                selected: i == currentIndex,
                onTap: () => onTap(i),
              ),
          ],
        ),
      ),
    );
  }
}

class AppBottomNavItem {
  const AppBottomNavItem({
    required this.icon,
    required this.label,
    this.activeIcon,
    this.badge,
  });

  final IconData icon;
  final IconData? activeIcon;
  final String label;
  final int? badge;
}

class _NavTile extends StatelessWidget {
  const _NavTile({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final AppBottomNavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOutCubic,
          padding: EdgeInsets.symmetric(
            horizontal: selected ? 16 : 12,
            vertical: 10,
          ),
          decoration: BoxDecoration(
            color: selected
                ? AppColors.ciOrange.withValues(alpha: 0.12)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(24),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    child: Icon(
                      selected ? (item.activeIcon ?? item.icon) : item.icon,
                      key: ValueKey(selected),
                      color: selected
                          ? AppColors.ciOrange
                          : AppColors.slate500,
                      size: 22,
                    ),
                  ),
                  if ((item.badge ?? 0) > 0)
                    Positioned(
                      top: -4,
                      right: -6,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 5, vertical: 1),
                        decoration: const BoxDecoration(
                          color: AppColors.ciOrange,
                          shape: BoxShape.circle,
                        ),
                        constraints:
                            const BoxConstraints(minWidth: 14, minHeight: 14),
                        child: Text(
                          (item.badge ?? 0) > 9 ? '9+' : '${item.badge}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 8,
                            fontWeight: FontWeight.w700,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                ],
              ),
              AnimatedSize(
                duration: const Duration(milliseconds: 280),
                curve: Curves.easeOutCubic,
                child: selected
                    ? Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: Text(
                          item.label,
                          style: const TextStyle(
                            color: AppColors.ciOrange,
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                          ),
                        ),
                      )
                    : const SizedBox.shrink(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
