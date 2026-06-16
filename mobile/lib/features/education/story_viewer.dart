import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'stories_data.dart';

/// Visionneuse plein écran style Instagram :
/// - tap droite/gauche pour naviguer
/// - barres de progression en haut
/// - à la fin → quiz interactif
class StoryViewer extends StatefulWidget {
  const StoryViewer({super.key, required this.story});
  final HealthStory story;

  @override
  State<StoryViewer> createState() => _StoryViewerState();
}

class _StoryViewerState extends State<StoryViewer>
    with TickerProviderStateMixin {
  late final AnimationController _progress;
  late final PageController _page;
  int _index = 0;

  static const _slideDuration = Duration(seconds: 6);

  @override
  void initState() {
    super.initState();
    _page = PageController();
    _progress = AnimationController(vsync: this, duration: _slideDuration)
      ..addStatusListener((s) {
        if (s == AnimationStatus.completed) _next();
      })
      ..forward();
  }

  @override
  void dispose() {
    _progress.dispose();
    _page.dispose();
    super.dispose();
  }

  void _next() {
    if (_index < widget.story.slides.length - 1) {
      setState(() => _index += 1);
      _page.animateToPage(
        _index,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
      _progress
        ..reset()
        ..forward();
    } else {
      // Fin de la story → on lance le quiz
      _progress.stop();
      _openQuiz();
    }
  }

  void _previous() {
    if (_index > 0) {
      setState(() => _index -= 1);
      _page.animateToPage(
        _index,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
      _progress
        ..reset()
        ..forward();
    }
  }

  Future<void> _openQuiz() async {
    final result = await Navigator.of(context).push<int>(
      MaterialPageRoute(
        builder: (_) => QuizScreen(story: widget.story),
        fullscreenDialog: true,
      ),
    );
    if (!mounted) return;
    if (result != null) {
      Navigator.of(context).pop(result);
    } else {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final slides = widget.story.slides;
    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        onTapUp: (d) {
          final w = MediaQuery.of(context).size.width;
          if (d.localPosition.dx < w / 3) {
            _previous();
          } else {
            _next();
          }
        },
        onLongPressStart: (_) => _progress.stop(),
        onLongPressEnd: (_) => _progress.forward(),
        child: Stack(
          children: [
            Container(
              decoration: BoxDecoration(gradient: widget.story.gradient),
            ),
            PageView.builder(
              controller: _page,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: slides.length,
              itemBuilder: (_, i) => _SlideView(slide: slides[i]),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                child: Column(
                  children: [
                    Row(
                      children: [
                        for (int i = 0; i < slides.length; i++)
                          Expanded(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 2),
                              child: _ProgressBar(
                                value: i < _index
                                    ? 1.0
                                    : i == _index
                                        ? _progress.value
                                        : 0.0,
                                controller: i == _index ? _progress : null,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Icon(widget.story.icon,
                            color: Colors.white, size: 22),
                        const SizedBox(width: 8),
                        Text(
                          widget.story.title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                        const Spacer(),
                        IconButton(
                          icon: const Icon(Icons.close, color: Colors.white),
                          onPressed: () => Navigator.pop(context),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SlideView extends StatelessWidget {
  const _SlideView({required this.slide});
  final StorySlide slide;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 90, 24, 40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (slide.icon != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.22),
                  shape: BoxShape.circle,
                ),
                child: Icon(slide.icon, color: Colors.white, size: 36),
              ),
            const SizedBox(height: 24),
            Text(
              slide.title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.w800,
                height: 1.2,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              slide.body,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.92),
                fontSize: 16,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProgressBar extends StatelessWidget {
  const _ProgressBar({required this.value, this.controller});
  final double value;
  final AnimationController? controller;

  @override
  Widget build(BuildContext context) {
    if (controller != null) {
      return AnimatedBuilder(
        animation: controller!,
        builder: (_, __) => _bar(controller!.value),
      );
    }
    return _bar(value);
  }

  Widget _bar(double v) => Container(
        height: 3,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(2),
        ),
        child: FractionallySizedBox(
          alignment: Alignment.centerLeft,
          widthFactor: v.clamp(0.0, 1.0),
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
      );
}

/// Quiz interactif à la fin d'une story.
class QuizScreen extends StatefulWidget {
  const QuizScreen({super.key, required this.story});
  final HealthStory story;

  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> {
  int _index = 0;
  int _score = 0;
  int? _selected;
  bool _answered = false;

  @override
  Widget build(BuildContext context) {
    final qs = widget.story.quizQuestions;
    if (_index >= qs.length) return _ResultView(score: _score, total: qs.length, story: widget.story);

    final q = qs[_index];
    return Scaffold(
      appBar: AppBar(
        title: Text('Quiz · ${widget.story.title}'),
        backgroundColor: widget.story.color,
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LinearProgressIndicator(
              value: (_index + 1) / qs.length,
              backgroundColor: AppColors.slate200,
              valueColor: AlwaysStoppedAnimation(widget.story.color),
              minHeight: 6,
              borderRadius: BorderRadius.circular(8),
            ),
            const SizedBox(height: 8),
            Text(
              'Question ${_index + 1} / ${qs.length}',
              style: const TextStyle(
                color: AppColors.slate500,
                fontWeight: FontWeight.w600,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              q.question,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                height: 1.3,
              ),
            ),
            const SizedBox(height: 24),
            for (int i = 0; i < q.options.length; i++) ...[
              _OptionTile(
                label: q.options[i],
                selected: _selected == i,
                correct: _answered && i == q.correctIndex,
                wrong: _answered && _selected == i && i != q.correctIndex,
                onTap: _answered
                    ? null
                    : () => setState(() {
                          _selected = i;
                          _answered = true;
                          if (i == q.correctIndex) _score += 1;
                        }),
              ),
              const SizedBox(height: 10),
            ],
            if (_answered && q.explanation != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.statusInfo.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.lightbulb_outline,
                        color: AppColors.statusInfo),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(q.explanation!,
                          style: const TextStyle(fontSize: 13)),
                    ),
                  ],
                ),
              ),
            ],
            const Spacer(),
            if (_answered)
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: widget.story.color,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                onPressed: () {
                  setState(() {
                    _index += 1;
                    _selected = null;
                    _answered = false;
                  });
                },
                child: Text(
                  _index + 1 < qs.length ? 'Question suivante' : 'Voir mon score',
                  style: const TextStyle(color: Colors.white, fontSize: 15),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.label,
    required this.selected,
    required this.correct,
    required this.wrong,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final bool correct;
  final bool wrong;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    Color bg = Colors.white;
    Color border = AppColors.slate200;
    Color textColor = AppColors.slate900;

    if (correct) {
      bg = AppColors.statusOk.withValues(alpha: 0.12);
      border = AppColors.statusOk;
      textColor = AppColors.statusOk;
    } else if (wrong) {
      bg = AppColors.statusDanger.withValues(alpha: 0.12);
      border = AppColors.statusDanger;
      textColor = AppColors.statusDanger;
    } else if (selected) {
      border = AppColors.ciOrange;
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: border, width: 1.5),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: textColor,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
              ),
              if (correct)
                const Icon(Icons.check_circle, color: AppColors.statusOk),
              if (wrong)
                const Icon(Icons.cancel, color: AppColors.statusDanger),
            ],
          ),
        ),
      ),
    );
  }
}

class _ResultView extends StatelessWidget {
  const _ResultView({
    required this.score,
    required this.total,
    required this.story,
  });

  final int score;
  final int total;
  final HealthStory story;

  @override
  Widget build(BuildContext context) {
    final pct = (score / total * 100).round();
    final passed = pct >= 70;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: story.gradient),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.22),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    passed ? Icons.emoji_events : Icons.refresh,
                    color: Colors.white,
                    size: 64,
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  passed ? 'Bravo !' : 'À retravailler',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  '$score / $total bonnes réponses · $pct %',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9),
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 30),
                if (passed) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(story.icon, color: story.color, size: 18),
                        const SizedBox(width: 8),
                        Text(
                          'Badge "${story.title}" débloqué',
                          style: TextStyle(
                            color: story.color,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 40),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.white),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () => Navigator.of(context).pop(score),
                        child: const Text('Retour'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
