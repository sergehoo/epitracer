"""Hiérarchie sanitaire de la République de Côte d'Ivoire.

Structure officielle (réforme MSHPCMU/INHP, alignement administratif 2011) :
    National          → 1 entité (Côte d'Ivoire)
    PRES              → 10 Pôles Régionaux d'Excellence Santé
                        (Arrêté n° 00203/MSHPCMU/CAB du 02/05/2023)
    Région Sanitaire  → 33 régions (alignées sur les régions administratives)
    District Sanitaire → 113 districts (alignés en partie sur les départements)
    Commune           → focus : 10 communes d'Abidjan + chefs-lieux districts
    Quartier          → focus : Abidjan (~70) + Bouaké + San-Pédro + Yamoussoukro

Sources de référence :
    - Arrêté n° 00203/MSHPCMU/CAB du 02 mai 2023 (création des PRES)
    - Décret n° 2011-263 portant organisation territoriale CI
    - Plan National de Développement Sanitaire (PNDS)
    - Annuaire des Statistiques Sanitaires (MSHPCMU)
    - Site officiel sante.gouv.ci

Format : structure hiérarchique imbriquée. Chaque nœud a `name` et
optionnellement `children`. Les codes sont auto-générés depuis le nom
(slugify ASCII).

Note : pour les districts/communes non listés explicitement, la commande
de seed crée un district générique par région et permet l'ajout ultérieur
via Django admin ou un patch JSON.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# NIVEAU 1 — NATIONAL
# ---------------------------------------------------------------------------
COUNTRY = {"name": "Côte d'Ivoire", "code": "ci-national"}


# ---------------------------------------------------------------------------
# NIVEAU 2 — PÔLES RÉGIONAUX D'EXCELLENCE SANTÉ (PRES) — 10 pôles
#
# Source officielle : Arrêté n° 00203/MSHPCMU/CAB du 02 mai 2023
# signé par le Ministre Pierre DIMBA. Article 2 — création de 10 PRES
# avec leurs Directions Régionales de la Santé rattachées.
#
# Chaque PRES porte le nom de son Établissement Support (chef-lieu).
# Total : 33 régions sanitaires réparties (3+6+2+3+2+2+4+3+3+5 = 33).
# ---------------------------------------------------------------------------
PRES = [
    {
        "name": "PRES Abengourou", "code": "pres-abengourou",
        "regions": ["Indénié-Djuablin", "Moronou", "Iffou"],
    },
    {
        "name": "PRES Abidjan", "code": "pres-abidjan",
        "regions": ["Abidjan 1 (Centre-Ouest)", "Abidjan 2 (Centre-Est)",
                    "Agnéby-Tiassa", "Grands Ponts", "La Mé", "Sud-Comoé"],
    },
    {
        "name": "PRES Bondoukou", "code": "pres-bondoukou",
        "regions": ["Bounkani", "Gontougo"],
    },
    {
        "name": "PRES Bouaké", "code": "pres-bouake",
        "regions": ["Gbêkê", "Béré", "Hambol"],
    },
    {
        "name": "PRES Daloa", "code": "pres-daloa",
        "regions": ["Haut-Sassandra", "Worodougou"],
    },
    {
        "name": "PRES Korhogo", "code": "pres-korhogo",
        "regions": ["Poro", "Tchologo"],
    },
    {
        "name": "PRES Man", "code": "pres-man",
        "regions": ["Cavally", "Guémon", "Tonkpi", "Bafing"],
    },
    {
        "name": "PRES Odienné", "code": "pres-odienne",
        "regions": ["Bagoué", "Folon", "Kabadougou"],
    },
    {
        "name": "PRES San-Pédro", "code": "pres-san-pedro",
        "regions": ["Gbôklê", "Nawa", "San-Pédro"],
    },
    {
        "name": "PRES Yamoussoukro", "code": "pres-yamoussoukro",
        "regions": ["Bélier", "Marahoué", "N'Zi", "Lôh-Djiboua", "Gôh"],
    },
]


# ---------------------------------------------------------------------------
# NIVEAU 3 — RÉGIONS SANITAIRES (33)
# Alignées sur le découpage administratif des régions de Côte d'Ivoire.
# Pour chaque région : chef-lieu et liste des districts sanitaires connus.
# ---------------------------------------------------------------------------
REGIONS = [
    # PRES Nord
    {"name": "Bagoué", "chef_lieu": "Boundiali",
     "districts": ["Boundiali", "Kouto", "Tengréla"]},
    {"name": "Bounkani", "chef_lieu": "Bouna",
     "districts": ["Bouna", "Doropo", "Nassian", "Téhini"]},
    {"name": "Folon", "chef_lieu": "Minignan",
     "districts": ["Minignan", "Kaniasso"]},
    {"name": "Kabadougou", "chef_lieu": "Odienné",
     "districts": ["Odienné", "Madinani", "Samatiguila", "Séguéla-Kabadougou"]},
    {"name": "Poro", "chef_lieu": "Korhogo",
     "districts": ["Korhogo", "Dikodougou", "M'Bengué", "Sinématiali"]},
    {"name": "Tchologo", "chef_lieu": "Ferkessédougou",
     "districts": ["Ferkessédougou", "Ouangolodougou", "Kong"]},
    {"name": "Worodougou", "chef_lieu": "Séguéla",
     "districts": ["Séguéla", "Kani"]},

    # PRES Sud
    {"name": "Abidjan 1 (Centre-Ouest)", "chef_lieu": "Abidjan",
     "districts": ["Yopougon-Ouest", "Yopougon-Est", "Attécoubé", "Adjamé",
                   "Plateau", "Abobo-Est", "Abobo-Ouest", "Anyama"]},
    {"name": "Abidjan 2 (Centre-Est)", "chef_lieu": "Abidjan",
     "districts": ["Cocody-Est", "Cocody-Bingerville", "Marcory", "Treichville",
                   "Koumassi", "Port-Bouët", "Songon"]},
    {"name": "Agnéby-Tiassa", "chef_lieu": "Agboville",
     "districts": ["Agboville", "Sikensi", "Tiassalé", "Taabo"]},
    {"name": "Grands Ponts", "chef_lieu": "Dabou",
     "districts": ["Dabou", "Jacqueville", "Grand-Lahou"]},
    {"name": "La Mé", "chef_lieu": "Adzopé",
     "districts": ["Adzopé", "Akoupé", "Yakassé-Attobrou", "Alépé"]},
    {"name": "San-Pédro", "chef_lieu": "San-Pédro",
     "districts": ["San-Pédro", "Tabou", "Grand-Béréby"]},
    {"name": "Sud-Comoé", "chef_lieu": "Aboisso",
     "districts": ["Aboisso", "Adiaké", "Grand-Bassam", "Tiapoum"]},

    # PRES Centre
    {"name": "Bélier", "chef_lieu": "Yamoussoukro",
     "districts": ["Yamoussoukro", "Toumodi", "Tiébissou", "Didiévi"]},
    {"name": "Gbêkê", "chef_lieu": "Bouaké",
     "districts": ["Bouaké Nord-Est", "Bouaké Nord-Ouest", "Bouaké Sud",
                   "Béoumi", "Sakassou"]},
    {"name": "Hambol", "chef_lieu": "Katiola",
     "districts": ["Katiola", "Dabakala", "Niakaramandougou"]},
    {"name": "Iffou", "chef_lieu": "Daoukro",
     "districts": ["Daoukro", "Prikro", "M'Bahiakro"]},
    {"name": "Marahoué", "chef_lieu": "Bouaflé",
     "districts": ["Bouaflé", "Sinfra", "Zuénoula"]},
    {"name": "Moronou", "chef_lieu": "Bongouanou",
     "districts": ["Bongouanou", "Arrah", "M'Batto"]},
    {"name": "N'Zi", "chef_lieu": "Dimbokro",
     "districts": ["Dimbokro", "Bocanda", "Kouassi-Kouassikro"]},

    # PRES Est
    {"name": "Gontougo", "chef_lieu": "Bondoukou",
     "districts": ["Bondoukou", "Tanda", "Sandégué", "Koun-Fao",
                   "Transua"]},
    {"name": "Indénié-Djuablin", "chef_lieu": "Abengourou",
     "districts": ["Abengourou", "Agnibilékrou", "Bettié"]},

    # PRES Ouest
    {"name": "Bafing", "chef_lieu": "Touba",
     "districts": ["Touba", "Koro", "Ouaninou"]},
    {"name": "Béré", "chef_lieu": "Mankono",
     "districts": ["Mankono", "Dianra", "Kounahiri"]},
    {"name": "Cavally", "chef_lieu": "Guiglo",
     "districts": ["Guiglo", "Bloléquin", "Taï", "Toulépleu"]},
    {"name": "Gbôklê", "chef_lieu": "Sassandra",
     "districts": ["Sassandra", "Fresco"]},
    {"name": "Gôh", "chef_lieu": "Gagnoa",
     "districts": ["Gagnoa 1", "Gagnoa 2", "Oumé"]},
    {"name": "Guémon", "chef_lieu": "Duékoué",
     "districts": ["Duékoué", "Bangolo", "Kouibly", "Facobly"]},
    {"name": "Haut-Sassandra", "chef_lieu": "Daloa",
     "districts": ["Daloa", "Issia", "Vavoua", "Zoukougbeu"]},
    {"name": "Lôh-Djiboua", "chef_lieu": "Divo",
     "districts": ["Divo", "Lakota", "Guitry"]},
    {"name": "Nawa", "chef_lieu": "Soubré",
     "districts": ["Soubré", "Buyo", "Méagui", "Gueyo"]},
    {"name": "Tonkpi", "chef_lieu": "Man",
     "districts": ["Man", "Biankouma", "Danané", "Sipilou", "Zouan-Hounien"]},
]


# ---------------------------------------------------------------------------
# NIVEAU 5 — COMMUNES (focus sur Abidjan et chefs-lieux)
# Pour Abidjan : les 10 communes officielles du district autonome.
# Pour le reste : on rattache les communes aux districts correspondants.
# ---------------------------------------------------------------------------

# Les 10 communes du District Autonome d'Abidjan
COMMUNES_ABIDJAN = [
    {"name": "Abobo",       "district": "Abobo-Est"},        # rattachée principalement
    {"name": "Adjamé",      "district": "Adjamé"},
    {"name": "Attécoubé",   "district": "Attécoubé"},
    {"name": "Cocody",      "district": "Cocody-Est"},
    {"name": "Koumassi",    "district": "Koumassi"},
    {"name": "Marcory",     "district": "Marcory"},
    {"name": "Plateau",     "district": "Plateau"},
    {"name": "Port-Bouët",  "district": "Port-Bouët"},
    {"name": "Treichville", "district": "Treichville"},
    {"name": "Yopougon",    "district": "Yopougon-Ouest"},
    # Communes périphériques du district autonome
    {"name": "Anyama",      "district": "Anyama"},
    {"name": "Bingerville", "district": "Cocody-Bingerville"},
    {"name": "Songon",      "district": "Songon"},
]

# Chefs-lieux des autres districts importants (communes principales)
COMMUNES_AUTRES = [
    # Centre
    {"name": "Yamoussoukro",      "district": "Yamoussoukro"},
    {"name": "Bouaké",            "district": "Bouaké Nord-Est"},
    {"name": "Toumodi",           "district": "Toumodi"},
    {"name": "Dimbokro",          "district": "Dimbokro"},
    {"name": "Daoukro",           "district": "Daoukro"},
    {"name": "Katiola",           "district": "Katiola"},
    {"name": "Bouaflé",           "district": "Bouaflé"},
    {"name": "Bongouanou",        "district": "Bongouanou"},
    # Sud
    {"name": "Grand-Bassam",      "district": "Grand-Bassam"},
    {"name": "Aboisso",           "district": "Aboisso"},
    {"name": "Adiaké",            "district": "Adiaké"},
    {"name": "Dabou",             "district": "Dabou"},
    {"name": "Grand-Lahou",       "district": "Grand-Lahou"},
    {"name": "Jacqueville",       "district": "Jacqueville"},
    {"name": "Adzopé",            "district": "Adzopé"},
    {"name": "Akoupé",            "district": "Akoupé"},
    {"name": "Agboville",         "district": "Agboville"},
    {"name": "Tiassalé",          "district": "Tiassalé"},
    {"name": "San-Pédro",         "district": "San-Pédro"},
    {"name": "Tabou",             "district": "Tabou"},
    # Nord
    {"name": "Korhogo",           "district": "Korhogo"},
    {"name": "Boundiali",         "district": "Boundiali"},
    {"name": "Ferkessédougou",    "district": "Ferkessédougou"},
    {"name": "Odienné",           "district": "Odienné"},
    {"name": "Bouna",             "district": "Bouna"},
    {"name": "Séguéla",           "district": "Séguéla"},
    {"name": "Tengréla",          "district": "Tengréla"},
    {"name": "Ouangolodougou",    "district": "Ouangolodougou"},
    {"name": "Minignan",          "district": "Minignan"},
    # Est
    {"name": "Bondoukou",         "district": "Bondoukou"},
    {"name": "Abengourou",        "district": "Abengourou"},
    {"name": "Tanda",             "district": "Tanda"},
    {"name": "Agnibilékrou",      "district": "Agnibilékrou"},
    # Ouest
    {"name": "Man",               "district": "Man"},
    {"name": "Daloa",             "district": "Daloa"},
    {"name": "Gagnoa",            "district": "Gagnoa 1"},
    {"name": "Soubré",            "district": "Soubré"},
    {"name": "Divo",              "district": "Divo"},
    {"name": "Guiglo",            "district": "Guiglo"},
    {"name": "Duékoué",           "district": "Duékoué"},
    {"name": "Issia",             "district": "Issia"},
    {"name": "Sassandra",         "district": "Sassandra"},
    {"name": "Touba",             "district": "Touba"},
    {"name": "Danané",            "district": "Danané"},
    {"name": "Bangolo",           "district": "Bangolo"},
    {"name": "Lakota",            "district": "Lakota"},
    {"name": "Buyo",              "district": "Buyo"},
]


# ---------------------------------------------------------------------------
# NIVEAU 6 — QUARTIERS (focus Abidjan + grandes villes)
# Liste indicative des principaux quartiers et zones de résidence connus.
# ---------------------------------------------------------------------------
QUARTIERS = {
    # ---- ABIDJAN ----
    "Abobo": [
        "Abobo Centre", "Abobo Avocatier", "Abobo Akéikoi", "Abobo Anonkoua-Kouté",
        "Abobo Belleville", "Abobo Biabou", "Abobo Sagbé", "Abobo Plaque",
        "Abobo Baoulé", "Abobo Samaké", "Abobo PK18",
    ],
    "Adjamé": [
        "Adjamé 220 Logements", "Adjamé Bracodi", "Adjamé Liberté",
        "Adjamé Williamsville", "Adjamé Mosquée", "Adjamé Pelieuville",
        "Adjamé Saint-Michel", "Adjamé Bromakoté", "Adjamé Cocoteraie",
    ],
    "Attécoubé": [
        "Attécoubé Centre", "Attécoubé Locodjro", "Attécoubé Abobo-Doumé",
        "Attécoubé Banco", "Attécoubé Sébroko", "Attécoubé Mossikro",
        "Attécoubé Boribana", "Attécoubé Agban-Village",
    ],
    "Cocody": [
        "Cocody Riviera 1", "Cocody Riviera 2", "Cocody Riviera 3",
        "Cocody Riviera Bonoumin", "Cocody Riviera Palmeraie",
        "Cocody Riviera Faya", "Cocody Riviera M'Pouto",
        "Cocody Angré", "Cocody Angré 7e Tranche", "Cocody Angré 8e Tranche",
        "Cocody Danga", "Cocody Deux-Plateaux", "Cocody 2-Plateaux Vallons",
        "Cocody II Plateaux Aghien", "Cocody Mermoz", "Cocody Saint-Jean",
        "Cocody Blockhauss", "Cocody Ambassades", "Cocody Cité des Arts",
        "Cocody Abatta", "Cocody Bingerville Centre", "Cocody Akouédo",
        "Cocody Akouai-Agban",
    ],
    "Koumassi": [
        "Koumassi Centre", "Koumassi Sicogi", "Koumassi Soweto",
        "Koumassi Remblais", "Koumassi Prodomo", "Koumassi Grand-Marché",
        "Koumassi Campement", "Koumassi Inchallah",
    ],
    "Marcory": [
        "Marcory Résidentiel", "Marcory Anoumabo", "Marcory Aliodan",
        "Marcory Zone 4", "Marcory Zone 3", "Marcory Biétry",
        "Marcory Konankro", "Marcory Sans-fil", "Marcory Potopoto",
    ],
    "Plateau": [
        "Plateau Centre", "Plateau Cité Administrative", "Plateau Indénié",
        "Plateau Lagune", "Plateau Liberté", "Plateau Mosquée",
    ],
    "Port-Bouët": [
        "Port-Bouët Centre", "Port-Bouët Vridi", "Port-Bouët Vridi Cité",
        "Port-Bouët Adjouffou", "Port-Bouët Abouabou", "Port-Bouët Gonzagueville",
        "Port-Bouët Anani", "Port-Bouët Phare",
    ],
    "Treichville": [
        "Treichville Centre", "Treichville Arras", "Treichville Belleville",
        "Treichville Habitat", "Treichville Sicogi", "Treichville Zone Portuaire",
        "Treichville Avenue 9-16", "Treichville Mairie",
    ],
    "Yopougon": [
        "Yopougon Niangon Nord", "Yopougon Niangon Sud", "Yopougon Niangon-Lokoa",
        "Yopougon Sicogi", "Yopougon Selmer", "Yopougon Académie",
        "Yopougon Wassakara", "Yopougon Ananeraie", "Yopougon Toits-Rouges",
        "Yopougon Sideci", "Yopougon Maroc", "Yopougon Andokoi",
        "Yopougon Banco", "Yopougon Yaoséhi", "Yopougon Gesco",
    ],

    # ---- BOUAKÉ ----
    "Bouaké": [
        "Bouaké Air-France 1", "Bouaké Air-France 2", "Bouaké Air-France 3",
        "Bouaké Commerce", "Bouaké Koko", "Bouaké N'Gattakro",
        "Bouaké Belleville", "Bouaké Houphouët-Ville", "Bouaké Dar-es-Salam",
        "Bouaké Sokoura", "Bouaké Tollakouadiokro", "Bouaké Banco",
        "Bouaké Djézoukouamékro", "Bouaké Nimbo",
    ],

    # ---- SAN-PÉDRO ----
    "San-Pédro": [
        "San-Pédro Cité Bardot", "San-Pédro Sewéké", "San-Pédro Lac",
        "San-Pédro Bardo", "San-Pédro Soleil", "San-Pédro Zone Industrielle",
        "San-Pédro Cité OPT", "San-Pédro Bia",
    ],

    # ---- YAMOUSSOUKRO ----
    "Yamoussoukro": [
        "Yamoussoukro Habitat", "Yamoussoukro Cocoteraie", "Yamoussoukro N'Zuessy",
        "Yamoussoukro Morofé", "Yamoussoukro Dioulabougou", "Yamoussoukro Quartier Millionnaire",
        "Yamoussoukro Yawakro", "Yamoussoukro Kokrenou", "Yamoussoukro 220 Logements",
    ],

    # ---- AUTRES VILLES PRINCIPALES (quartiers représentatifs) ----
    "Korhogo": ["Korhogo Centre", "Korhogo Soba", "Korhogo Koko", "Korhogo Banaforo"],
    "Daloa":   ["Daloa Tazibouo", "Daloa Lobia", "Daloa Garage", "Daloa Soleil"],
    "Man":     ["Man Domoraud", "Man Libreville", "Man Glôplou", "Man Doyaguinè"],
    "Gagnoa":  ["Gagnoa Dioulabougou", "Gagnoa Garage", "Gagnoa Niékré"],
    "Abengourou": ["Abengourou Centre", "Abengourou EECI", "Abengourou Hanou"],
    "Bondoukou": ["Bondoukou Centre", "Bondoukou Hamdallaye", "Bondoukou Donzo"],
}
