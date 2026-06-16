import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'stories_data.dart';
import 'story_viewer.dart';

class StoriesScreen extends StatelessWidget {
  const StoriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Apprendre la santé')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Text(
              'Mini-cours santé en 4 minutes — quiz inclus à la fin pour valider vos connaissances.',
              style: TextStyle(color: AppColors.slate500, fontSize: 13),
            ),
          ),
          for (final story in kHealthStories) ...[
            _StoryCard(story: story),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _StoryCard extends StatelessWidget {
  const _StoryCard({required this.story});
  final HealthStory story;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => StoryViewer(story: story),
              fullscreenDialog: true,
            ),
          );
        },
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: story.gradient,
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: story.color.withValues(alpha: 0.3),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.22),
                  shape: BoxShape.circle,
                ),
                child: Icon(story.icon, color: Colors.white, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      story.title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      story.subtitle,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.menu_book,
                            color: Colors.white70, size: 14),
                        const SizedBox(width: 4),
                        Text(
                          '${story.slides.length} chapitres',
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Icon(Icons.quiz_outlined,
                            color: Colors.white70, size: 14),
                        const SizedBox(width: 4),
                        Text(
                          '${story.quizQuestions.length} questions',
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios,
                  color: Colors.white, size: 18),
            ],
          ),
        ),
      ),
    );
  }
}
