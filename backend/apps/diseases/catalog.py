"""Catalogue des maladies du portail public, partagé par la migration et le seed.

Les fonctions prennent les classes de modèles en paramètre pour fonctionner
avec les modèles historiques d'une migration. Règles :
- les maladies absentes sont créées INACTIVES (aucune surveillance déclenchée) ;
- le contenu public n'est qu'un BROUILLON : rien n'est publié ici, la
  publication reste un acte d'un administrateur habilité ;
- seuls les champs vides sont complétés : rien de ce qui a été saisi n'est écrasé.

Contenu rédigé d'après les fiches OMS ; il doit être relu et validé par
l'INHP / le MSHPCMU avant publication.
"""

from __future__ import annotations

# Maladies à créer si absentes (paramètres techniques ; is_active=False).
NEW_DISEASES: dict[str, dict] = {
    "DENGUE": {
        "name": "Dengue",
        "short_name": "Dengue",
        "icd11_code": "1D20",
        "severity": "moderate",
        "color": "#e11d48",
        "incubation_min_days": 4,
        "incubation_max_days": 10,
        "surveillance_days": 14,
        "quarantine_days": 0,
        "transmission_modes": ["vector"],
        "requires_quarantine": False,
        "requires_pass": False,
    },
    "MENINGITIS": {
        "name": "Méningite à méningocoque",
        "short_name": "Méningite",
        "icd11_code": "1D01",
        "severity": "high",
        "color": "#9333ea",
        "incubation_min_days": 2,
        "incubation_max_days": 10,
        "surveillance_days": 10,
        "quarantine_days": 0,
        "transmission_modes": ["droplet"],
        "requires_quarantine": False,
        "requires_pass": False,
    },
    "MEASLES": {
        "name": "Rougeole",
        "short_name": "Rougeole",
        "icd11_code": "1F03",
        "severity": "high",
        "color": "#be185d",
        "incubation_min_days": 7,
        "incubation_max_days": 21,
        "surveillance_days": 21,
        "quarantine_days": 0,
        "transmission_modes": ["airborne", "droplet"],
        "requires_quarantine": False,
        "requires_pass": False,
    },
}

# Contenu public (brouillon) par code maladie.
PUBLIC_CONTENT: dict[str, dict] = {
    "EBOLA": {
        "slug": "ebola",
        "description": (
            "Maladie virale grave, souvent mortelle, transmise par contact direct avec le sang ou "
            "les liquides biologiques d'une personne malade ou décédée, ou d'un animal infecté. "
            "L'incubation peut durer jusqu'à 21 jours."
        ),
        "transmission_details": (
            "Contact direct avec le sang, les sécrétions ou les liquides biologiques d'une "
            "personne "
            "malade ou décédée, ou avec des objets contaminés ; contact avec des animaux infectés "
            "(chauves-souris frugivores, primates)."
        ),
        "prevention": (
            "Lavez-vous régulièrement les mains à l'eau et au savon ou avec une solution "
            "hydroalcoolique.\n"
            "Évitez tout contact avec le sang et les liquides biologiques d'une personne malade.\n"
            "Ne touchez pas le corps d'une personne décédée d'une maladie inexpliquée.\n"
            "Évitez de manipuler ou de consommer de la viande de brousse."
        ),
        "traveler_recommendations": (
            "Surveillez votre température pendant 21 jours après votre arrivée.\n"
            "En cas de fièvre, de fatigue intense ou de saignements, isolez-vous et appelez le "
            "143 ou le SAMU (185).\n"
            "Signalez votre voyage au personnel de santé lors de toute consultation."
        ),
        "symptoms": [],  # symptômes Ebola déjà gérés par le seed de référence
        "risk_factors": [],
    },
    "MPOX": {
        "slug": "mpox",
        "description": (
            "Infection virale provoquant une éruption cutanée (boutons, vésicules) souvent "
            "accompagnée de fièvre et de ganglions gonflés. Elle guérit le plus souvent en 2 à "
            "4 semaines mais peut être grave chez certaines personnes."
        ),
        "transmission_details": (
            "Contact physique étroit avec une personne infectée (peau à peau, rapports sexuels, "
            "contact avec les lésions), objets contaminés (linge, draps), et plus rarement contact "
            "avec des animaux infectés."
        ),
        "prevention": (
            "Évitez les contacts rapprochés avec une personne présentant des lésions cutanées.\n"
            "Ne partagez pas le linge, les serviettes ou la literie d'une personne malade.\n"
            "Lavez-vous souvent les mains.\n"
            "Renseignez-vous sur la vaccination si vous êtes exposé à un risque élevé."
        ),
        "traveler_recommendations": (
            "En cas d'éruption cutanée inhabituelle, évitez les contacts rapprochés et consultez.\n"
            "Appelez le 143 pour être orienté vers un centre de santé."
        ),
        "symptoms": [
            ("rash", "Éruption cutanée ou lésions"),
            ("fever", "Fièvre"),
            ("swollen_lymph_nodes", "Ganglions gonflés"),
            ("muscle_pain", "Douleurs musculaires ou dorsales"),
        ],
        "risk_factors": [
            (
                "contact_lesions",
                "Contact rapproché avec une personne présentant des lésions cutanées",
            ),
        ],
    },
    "CHOLERA": {
        "slug": "cholera",
        "description": (
            "Infection intestinale aiguë provoquant une diarrhée aqueuse abondante pouvant "
            "entraîner une déshydratation rapide. Elle se soigne efficacement par la réhydratation."
        ),
        "transmission_details": (
            "Consommation d'eau ou d'aliments contaminés par des matières fécales."
        ),
        "prevention": (
            "Buvez de l'eau traitée, bouillie ou en bouteille capsulée.\n"
            "Lavez-vous les mains au savon avant de manger et après être allé aux toilettes.\n"
            "Consommez des aliments bien cuits et servis chauds ; lavez fruits et légumes.\n"
            "Renseignez-vous sur la vaccination orale dans les zones touchées."
        ),
        "traveler_recommendations": (
            "En cas de diarrhée abondante, buvez une solution de réhydratation orale (SRO) et "
            "consultez sans attendre."
        ),
        "symptoms": [
            ("watery_diarrhea", "Diarrhée aqueuse abondante"),
            ("vomiting", "Vomissements"),
            ("dehydration", "Signes de déshydratation (soif intense, fatigue)"),
        ],
        "risk_factors": [
            ("unsafe_water", "Consommation d'eau non traitée dans une zone touchée"),
            ("contact_case", "Contact avec une personne atteinte de choléra"),
        ],
    },
    "YELLOW_FEVER": {
        "slug": "fievre-jaune",
        "description": (
            "Maladie virale transmise par les moustiques, qui peut provoquer une jaunisse et des "
            "hémorragies dans ses formes graves. Un vaccin sûr et efficace protège à vie."
        ),
        "transmission_details": "Piqûre de moustiques infectés (Aedes, Haemagogus).",
        "prevention": (
            "Faites-vous vacciner au moins 10 jours avant le départ.\n"
            "Protégez-vous des piqûres de moustiques (répulsif, vêtements couvrants, moustiquaire)."
        ),
        "traveler_recommendations": (
            "Ayez sur vous votre certificat international de vaccination contre la fièvre jaune.\n"
            "En cas de fièvre, de douleurs ou de jaunissement de la peau, consultez rapidement."
        ),
        "symptoms": [
            ("fever", "Fièvre"),
            ("muscle_pain", "Douleurs musculaires, notamment du dos"),
            ("jaundice", "Jaunissement de la peau ou des yeux"),
        ],
        "risk_factors": [
            (
                "unvaccinated_stay",
                "Séjour en zone de transmission sans être vacciné contre la fièvre jaune",
            ),
        ],
    },
    "DENGUE": {
        "slug": "dengue",
        "description": (
            "Infection virale transmise par les moustiques, provoquant une forte fièvre et des "
            "douleurs. La plupart des cas guérissent, mais une forme sévère peut survenir."
        ),
        "transmission_details": "Piqûre de moustiques Aedes infectés, actifs surtout en journée.",
        "prevention": (
            "Utilisez un répulsif et portez des vêtements couvrants, y compris en journée.\n"
            "Dormez sous moustiquaire.\n"
            "Videz les récipients contenant de l'eau stagnante autour de votre logement."
        ),
        "traveler_recommendations": (
            "En cas de fièvre, consultez et évitez l'aspirine et l'ibuprofène sans avis médical "
            "(préférez le paracétamol).\n"
            "Consultez en urgence en cas de douleurs abdominales intenses, de vomissements "
            "répétés ou de saignements."
        ),
        "symptoms": [
            ("high_fever", "Forte fièvre"),
            ("headache", "Maux de tête intenses, douleur derrière les yeux"),
            ("joint_pain", "Douleurs musculaires et articulaires"),
            ("rash", "Éruption cutanée"),
        ],
        "risk_factors": [
            ("dengue_area_stay", "Séjour dans une zone où la dengue circule activement"),
        ],
    },
    "MENINGITIS": {
        "slug": "meningite",
        "description": (
            "Inflammation des membranes entourant le cerveau, d'origine bactérienne le plus "
            "souvent. C'est une urgence médicale : un traitement rapide sauve des vies."
        ),
        "transmission_details": (
            "Gouttelettes respiratoires et sécrétions de la gorge lors de contacts étroits et "
            "prolongés."
        ),
        "prevention": (
            "Faites-vous vacciner, en particulier avant un séjour en saison sèche dans le nord.\n"
            "Couvrez votre bouche lorsque vous toussez et évitez les espaces confinés surpeuplés."
        ),
        "traveler_recommendations": (
            "Fièvre brutale avec raideur de la nuque ou maux de tête intenses : consultez "
            "immédiatement (SAMU 185)."
        ),
        "symptoms": [
            ("fever", "Fièvre brutale"),
            ("stiff_neck", "Raideur de la nuque"),
            ("headache", "Maux de tête intenses"),
            ("photophobia", "Gêne à la lumière, confusion"),
        ],
        "risk_factors": [
            ("contact_case", "Contact étroit avec une personne atteinte de méningite"),
        ],
    },
    "MEASLES": {
        "slug": "rougeole",
        "description": (
            "Maladie virale très contagieuse, qui peut entraîner des complications graves, "
            "surtout chez les jeunes enfants. La vaccination protège efficacement."
        ),
        "transmission_details": "Voie aérienne : toux, éternuements, contact rapproché.",
        "prevention": (
            "Vérifiez que vous et vos enfants avez reçu deux doses de vaccin contre la rougeole.\n"
            "Évitez le contact avec une personne malade."
        ),
        "traveler_recommendations": (
            "En cas de fièvre avec éruption, limitez les contacts (en particulier avec les "
            "nourrissons) et consultez."
        ),
        "symptoms": [
            ("fever", "Fièvre élevée"),
            ("rash", "Éruption débutant sur le visage"),
            ("cough", "Toux, nez qui coule"),
            ("red_eyes", "Yeux rouges et larmoyants"),
        ],
        "risk_factors": [
            ("contact_case", "Contact avec une personne atteinte de rougeole"),
        ],
    },
    "COVID19": {
        "slug": "covid-19",
        "description": (
            "Infection respiratoire due au virus SARS-CoV-2, le plus souvent bénigne mais "
            "pouvant être grave chez les personnes âgées ou fragiles."
        ),
        "transmission_details": (
            "Voie respiratoire (gouttelettes et aérosols), surtout en lieux clos."
        ),
        "prevention": (
            "Aérez les lieux clos et lavez-vous les mains régulièrement.\n"
            "Portez un masque si vous présentez des symptômes respiratoires."
        ),
        "traveler_recommendations": (
            "En cas de fièvre ou de toux, limitez vos contacts et demandez conseil au 143."
        ),
        "symptoms": [
            ("fever", "Fièvre"),
            ("cough", "Toux"),
            ("loss_of_taste_smell", "Perte du goût ou de l'odorat"),
            ("shortness_of_breath", "Difficultés à respirer"),
        ],
        "risk_factors": [
            ("contact_case", "Contact avec une personne testée positive"),
        ],
    },
    "LASSA": {
        "slug": "fievre-de-lassa",
        "description": (
            "Fièvre hémorragique virale présente en Afrique de l'Ouest, transmise principalement "
            "par les rongeurs. La plupart des infections sont bénignes mais certaines sont graves."
        ),
        "transmission_details": (
            "Contact avec l'urine ou les excréments de rats infectés (aliments, objets), ou avec "
            "les liquides biologiques d'une personne malade."
        ),
        "prevention": (
            "Conservez les aliments dans des récipients fermés, à l'abri des rongeurs.\n"
            "Gardez le logement propre et évitez tout contact avec les rongeurs."
        ),
        "traveler_recommendations": (
            "En cas de fièvre persistante, de faiblesse ou de maux de gorge après un séjour en "
            "zone touchée, consultez et signalez votre voyage."
        ),
        "symptoms": [
            ("fever", "Fièvre progressive"),
            ("sore_throat", "Maux de gorge"),
            ("weakness", "Faiblesse générale"),
        ],
        "risk_factors": [
            ("rodent_contact", "Contact avec des rongeurs ou leurs excréments"),
        ],
    },
}

_TEXT_FIELDS = (
    "slug",
    "description",
    "transmission_details",
    "prevention",
    "traveler_recommendations",
)


def sync_disease_catalog(disease_model, symptom_model, risk_factor_model) -> dict[str, int]:
    """Crée les maladies manquantes (inactives) et complète le contenu public vide.

    Idempotent ; ne publie rien, n'active rien, n'écrase aucune saisie.
    """
    created = 0
    for code, attrs in NEW_DISEASES.items():
        exists = (
            disease_model.objects.filter(code=code).exists()
            or disease_model.objects.filter(name__iexact=attrs["name"]).exists()
        )
        if not exists:
            disease_model.objects.create(code=code, is_active=False, **attrs)
            created += 1

    completed = 0
    for code, content in PUBLIC_CONTENT.items():
        disease = disease_model.objects.filter(code=code).first()
        if disease is None:
            continue
        if _complete_text(disease_model, disease, content):
            completed += 1
        _complete_lists(symptom_model, risk_factor_model, disease, content)
    return {"created": created, "completed": completed}


def _complete_text(disease_model, disease, content: dict) -> bool:
    """Renseigne les champs texte vides ; le slug n'est posé que s'il est libre."""
    changed = []
    for field in _TEXT_FIELDS:
        value = content[field]
        slug_taken = (
            field == "slug"
            and disease_model.objects.filter(slug=value).exclude(pk=disease.pk).exists()
        )
        if not slug_taken and not getattr(disease, field):
            setattr(disease, field, value)
            changed.append(field)
    if changed:
        disease.save(update_fields=changed)
    return bool(changed)


def _complete_lists(symptom_model, risk_factor_model, disease, content: dict) -> None:
    """Symptômes et questions d'exposition, seulement si la maladie n'en a aucun."""
    if content["symptoms"] and not symptom_model.objects.filter(disease=disease).exists():
        for order, (s_code, label) in enumerate(content["symptoms"]):
            symptom_model.objects.create(disease=disease, code=s_code, label=label, order=order)
    if content["risk_factors"] and not risk_factor_model.objects.filter(disease=disease).exists():
        for rf_code, label in content["risk_factors"]:
            risk_factor_model.objects.create(disease=disease, code=rf_code, label=label)
