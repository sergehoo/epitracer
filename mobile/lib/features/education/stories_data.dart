import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_gradients.dart';

/// Une story = une suite de "slides" éducatives + un quiz lié.
class HealthStory {
  const HealthStory({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.gradient,
    required this.color,
    required this.slides,
    required this.quizQuestions,
  });

  final String id;
  final String title;
  final String subtitle;
  final IconData icon;
  final Gradient gradient;
  final Color color;
  final List<StorySlide> slides;
  final List<QuizQuestion> quizQuestions;
}

class StorySlide {
  const StorySlide({required this.title, required this.body, this.icon});
  final String title;
  final String body;
  final IconData? icon;
}

class QuizQuestion {
  const QuizQuestion({
    required this.question,
    required this.options,
    required this.correctIndex,
    this.explanation,
  });

  final String question;
  final List<String> options;
  final int correctIndex;
  final String? explanation;
}

const List<HealthStory> kHealthStories = [
  HealthStory(
    id: 'ebola',
    title: 'Ebola',
    subtitle: 'Reconnaître et prévenir',
    icon: Icons.coronavirus_outlined,
    color: AppColors.statusDanger,
    gradient: AppGradients.critical,
    slides: [
      StorySlide(
        title: 'Qu\'est-ce qu\'Ebola ?',
        body:
            'Maladie virale grave, transmise par contact direct avec les fluides corporels d\'une personne infectée (sang, sueur, salive, vomissures).',
        icon: Icons.science_outlined,
      ),
      StorySlide(
        title: 'Symptômes clés',
        body:
            'Fièvre soudaine, fatigue intense, douleurs musculaires, maux de tête, mal de gorge. Plus tard : vomissements, diarrhée, saignements inexpliqués.',
        icon: Icons.thermostat,
      ),
      StorySlide(
        title: 'Comment se protéger ?',
        body:
            '• Évitez tout contact avec une personne malade\n• Lavez-vous les mains au savon\n• Ne touchez pas les animaux sauvages (chauves-souris, primates)\n• Consultez immédiatement en cas de symptôme',
        icon: Icons.shield_outlined,
      ),
      StorySlide(
        title: 'Que faire si je suis exposé ?',
        body:
            'Appelez immédiatement le 143 (numéro vert INHP) ou présentez-vous au CHR le plus proche. Plus le diagnostic est précoce, meilleures sont les chances de guérison.',
        icon: Icons.phone_in_talk,
      ),
    ],
    quizQuestions: [
      QuizQuestion(
        question: 'Comment Ebola se transmet-il principalement ?',
        options: [
          'Par voie aérienne',
          'Par contact avec fluides corporels infectés',
          'Par piqûre de moustique',
          'Par l\'eau du robinet',
        ],
        correctIndex: 1,
        explanation:
            'Ebola se transmet par contact direct avec sang, sueur, salive ou vomissures d\'une personne infectée.',
      ),
      QuizQuestion(
        question: 'Quel est le numéro d\'urgence INHP en Côte d\'Ivoire ?',
        options: ['112', '15', '143', '185'],
        correctIndex: 2,
      ),
      QuizQuestion(
        question:
            'Combien de temps dure la période d\'incubation d\'Ebola ?',
        options: ['1 à 2 jours', '2 à 21 jours', '1 à 3 mois', 'Plusieurs années'],
        correctIndex: 1,
        explanation:
            'C\'est pourquoi le suivi sanitaire dure 21 jours après une exposition possible.',
      ),
    ],
  ),
  HealthStory(
    id: 'paludisme',
    title: 'Paludisme',
    subtitle: 'Première cause de mortalité en CI',
    icon: Icons.bug_report_outlined,
    color: AppColors.ciOrange,
    gradient: AppGradients.warmOrange,
    slides: [
      StorySlide(
        title: 'Le paludisme en Côte d\'Ivoire',
        body:
            'Première cause de consultation médicale, particulièrement chez les enfants de moins de 5 ans et les femmes enceintes.',
        icon: Icons.warning_amber_rounded,
      ),
      StorySlide(
        title: 'Comment l\'attrape-t-on ?',
        body:
            'Par piqûre d\'un moustique femelle Anopheles infecté. Le moustique pique surtout entre le crépuscule et l\'aube.',
        icon: Icons.bug_report,
      ),
      StorySlide(
        title: 'Symptômes',
        body:
            'Fièvre forte, frissons, sueurs, maux de tête intenses, courbatures, parfois nausées et vomissements. Apparaît 7 à 30 jours après la piqûre.',
        icon: Icons.thermostat,
      ),
      StorySlide(
        title: 'Prévention',
        body:
            '• Dormez sous moustiquaire imprégnée\n• Utilisez répulsif anti-moustique\n• Portez manches longues le soir\n• Éliminez les eaux stagnantes\n• Consultez vite en cas de fièvre',
        icon: Icons.shield_outlined,
      ),
    ],
    quizQuestions: [
      QuizQuestion(
        question: 'Le paludisme se transmet par :',
        options: [
          'L\'eau contaminée',
          'La piqûre d\'un moustique Anopheles',
          'Une poignée de main',
          'L\'air ambiant',
        ],
        correctIndex: 1,
      ),
      QuizQuestion(
        question: 'Quelle est la meilleure protection nocturne ?',
        options: [
          'Ventilateur',
          'Moustiquaire imprégnée',
          'Climatiseur',
          'Bougies parfumées',
        ],
        correctIndex: 1,
      ),
      QuizQuestion(
        question: 'En cas de fièvre forte après une piqûre, je dois :',
        options: [
          'Attendre que ça passe',
          'Prendre du paracétamol seulement',
          'Consulter rapidement un centre de santé',
          'Boire beaucoup d\'eau',
        ],
        correctIndex: 2,
        explanation:
            'Le paludisme peut tuer en moins de 48h. Toute fièvre doit être prise au sérieux.',
      ),
    ],
  ),
  HealthStory(
    id: 'covid',
    title: 'COVID-19',
    subtitle: 'Restez vigilant',
    icon: Icons.masks_outlined,
    color: AppColors.ciDark,
    gradient: AppGradients.nightDark,
    slides: [
      StorySlide(
        title: 'Le virus est-il toujours là ?',
        body:
            'Oui — le SARS-CoV-2 circule toujours et continue d\'évoluer. La vigilance reste de mise, surtout pour les personnes vulnérables.',
        icon: Icons.coronavirus,
      ),
      StorySlide(
        title: 'Comment se protéger ?',
        body:
            '• Vaccination à jour (rappel annuel recommandé)\n• Lavage des mains régulier\n• Port du masque dans les lieux bondés\n• Aération des espaces clos',
        icon: Icons.shield_outlined,
      ),
      StorySlide(
        title: 'Si j\'ai des symptômes ?',
        body:
            'Toux, fièvre, perte d\'odorat ou de goût : faites-vous tester et isolez-vous le temps des résultats. Consultez en cas d\'aggravation.',
        icon: Icons.medical_information,
      ),
    ],
    quizQuestions: [
      QuizQuestion(
        question: 'Quel geste reste efficace contre le COVID-19 ?',
        options: [
          'Boire chaud',
          'Lavage des mains au savon',
          'Antibiotiques',
          'Se priver de sommeil',
        ],
        correctIndex: 1,
      ),
      QuizQuestion(
        question: 'La vaccination COVID-19 nécessite :',
        options: [
          'Une seule dose à vie',
          'Un rappel régulier selon recommandations',
          'Aucune dose',
          'Uniquement chez les enfants',
        ],
        correctIndex: 1,
      ),
    ],
  ),
  HealthStory(
    id: 'fievre-jaune',
    title: 'Fièvre jaune',
    subtitle: 'Vaccin obligatoire en CI',
    icon: Icons.vaccines_outlined,
    color: AppColors.ciGreen,
    gradient: AppGradients.healthyGreen,
    slides: [
      StorySlide(
        title: 'Pourquoi le vaccin est-il obligatoire ?',
        body:
            'La Côte d\'Ivoire est en zone endémique. Le certificat international de vaccination est exigé à l\'entrée du pays pour les voyageurs internationaux.',
        icon: Icons.flight_land,
      ),
      StorySlide(
        title: 'Où se faire vacciner ?',
        body:
            'À l\'Institut National d\'Hygiène Publique (INHP) à Treichville, ou dans les centres agréés. Le vaccin est efficace à vie après une seule dose.',
        icon: Icons.local_hospital,
      ),
      StorySlide(
        title: 'Symptômes à surveiller',
        body:
            'Fièvre soudaine, douleurs musculaires, maux de tête, nausées. Forme grave : jaunisse, saignements. Consultez immédiatement.',
        icon: Icons.warning_amber_rounded,
      ),
    ],
    quizQuestions: [
      QuizQuestion(
        question:
            'Le vaccin contre la fièvre jaune protège pendant :',
        options: ['1 an', '5 ans', '10 ans', 'À vie'],
        correctIndex: 3,
        explanation:
            'Depuis 2016, l\'OMS reconnaît une protection à vie après une seule dose.',
      ),
      QuizQuestion(
        question: 'Où peut-on se faire vacciner officiellement à Abidjan ?',
        options: [
          'Centre commercial',
          'INHP Treichville',
          'Marché',
          'Pharmacie',
        ],
        correctIndex: 1,
      ),
    ],
  ),
  HealthStory(
    id: 'mpox',
    title: 'MPOX (Variole du singe)',
    subtitle: 'Connaître les signes',
    icon: Icons.healing,
    color: AppColors.statusWarn,
    gradient: AppGradients.warmOrange,
    slides: [
      StorySlide(
        title: 'Qu\'est-ce que la MPOX ?',
        body:
            'Maladie virale (orthopoxvirus) provoquant fièvre et éruption cutanée caractéristique. La transmission se fait par contact étroit ou avec un objet contaminé.',
      ),
      StorySlide(
        title: 'Signes typiques',
        body:
            '• Fièvre, fatigue, maux de tête\n• Ganglions enflés\n• Éruption cutanée évoluant en vésicules puis croûtes\n• Apparition 5 à 21 jours après contact',
        icon: Icons.warning_amber_rounded,
      ),
      StorySlide(
        title: 'Protection',
        body:
            'Évitez le contact avec personnes symptomatiques et leurs objets personnels (linge, ustensiles). Consultez immédiatement en cas d\'éruption suspecte.',
        icon: Icons.shield_outlined,
      ),
    ],
    quizQuestions: [
      QuizQuestion(
        question: 'La MPOX se transmet principalement par :',
        options: [
          'Air ambiant',
          'Contact étroit avec personne infectée',
          'Eau de boisson',
          'Piqûre de moustique',
        ],
        correctIndex: 1,
      ),
      QuizQuestion(
        question: 'Période d\'incubation typique :',
        options: ['1 à 2 jours', '5 à 21 jours', '2 à 3 mois', 'Plusieurs années'],
        correctIndex: 1,
      ),
    ],
  ),
];
