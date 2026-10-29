# Rapport de détection des anomalies thématiques

## 1. Méthodologie

L'analyse repose sur 16 variables hebdomadaires : la proportion et l'écart à la moyenne mobile sur 4 semaines pour chacun des 8 thèmes étudiés.

Les variables ont été standardisées avec `StandardScaler`.

Le modèle principal utilisé est `IsolationForest`, avec un taux de contamination fixé à 10%.

Les semaines détectées doivent être interprétées comme des périodes thématiquement atypiques et non comme des signaux faibles avérés.

## 2. Semaines détectées par Isolation Forest

| Semaine | Score d'anomalie |
|---|---:|
| 2016-S40 | -0.0530 |
| 2016-S06 | -0.0238 |
| 2016-S41 | -0.0134 |
| 2016-S26 | -0.0005 |

## 3. Variables expliquant les anomalies

### 2016-S40

| Variable | Valeur | z-score |
|---|---:|---:|
| institutions_gouvernement_proportion | 17.71 | +2.77 |
| technologie_medias_proportion | 14.51 | +2.72 |
| economie_proportion | 7.84 | +2.54 |
| economie_ecart | 2.55 | +2.17 |
| sante_environnement_ecart | 1.51 | +2.08 |

### 2016-S06

| Variable | Valeur | z-score |
|---|---:|---:|
| territoires_ecart | 6.53 | +3.19 |
| territoires_proportion | 24.76 | +3.12 |
| sante_environnement_proportion | 4.34 | +2.19 |
| economie_proportion | 7.07 | +1.81 |
| droits_societe_ecart | 2.21 | +1.68 |

### 2016-S41

| Variable | Valeur | z-score |
|---|---:|---:|
| droits_societe_proportion | 10.34 | +3.82 |
| droits_societe_ecart | 4.76 | +3.71 |
| technologie_medias_proportion | 14.81 | +2.92 |
| politique_electorale_proportion | 21.91 | +2.11 |
| sante_environnement_ecart | 1.33 | +1.84 |

### 2016-S26

| Variable | Valeur | z-score |
|---|---:|---:|
| economie_ecart | -2.54 | -2.15 |
| droits_societe_ecart | -2.34 | -1.94 |
| droits_societe_proportion | 3.38 | -1.90 |
| relations_internationales_securite_proportion | 14.68 | +1.78 |
| technologie_medias_ecart | -2.57 | -1.68 |

## 4. Baseline naïve

La baseline considère une semaine comme atypique lorsqu'au moins une variable présente `|z| >= 2`.

Nombre de semaines détectées : **16**

| Semaine | z-score maximal |
|---|---:|
| 2016-S41 | 3.82 |
| 2016-S06 | 3.19 |
| 2016-S25 | 2.78 |
| 2016-S30 | 2.78 |
| 2016-S40 | 2.77 |
| 2016-S42 | 2.69 |
| 2016-S27 | 2.53 |
| 2016-S39 | 2.50 |
| 2016-S38 | 2.36 |
| 2016-S29 | 2.21 |
| 2016-S33 | 2.18 |
| 2016-S26 | 2.15 |
| 2016-S31 | 2.14 |
| 2016-S35 | 2.14 |
| 2016-S37 | 2.06 |
| 2016-S36 | 2.01 |

## 5. Comparaison des méthodes

- Isolation Forest : **4** semaines
- Baseline naïve : **16** semaines
- Anomalies communes : **4** semaines

### Détectées par les deux méthodes

- 2016-S06
- 2016-S26
- 2016-S40
- 2016-S41

### Uniquement par Isolation Forest

Aucune.

### Uniquement par la baseline

- 2016-S25
- 2016-S27
- 2016-S29
- 2016-S30
- 2016-S31
- 2016-S33
- 2016-S35
- 2016-S36
- 2016-S37
- 2016-S38
- 2016-S39
- 2016-S42

## 6. Analyse de robustesse du modèle

Le modèle a été testé avec plusieurs taux de contamination afin de vérifier si certaines semaines restent détectées lorsque ce paramètre varie.

| Semaine | Nombre de détections | Stabilité |
|---|---:|---:|
| 2016-S06 | 4/4 | 100 % |
| 2016-S40 | 4/4 | 100 % |
| 2016-S26 | 3/4 | 75 % |
| 2016-S41 | 3/4 | 75 % |
| 2016-S30 | 2/4 | 50 % |
| 2016-S38 | 2/4 | 50 % |
| 2016-S35 | 1/4 | 25 % |
| 2016-S37 | 1/4 | 25 % |

Les semaines détectées dans plusieurs configurations sont considérées comme plus stables vis-à-vis du choix du paramètre de contamination.

Cette stabilité ne constitue cependant pas une mesure de performance du modèle et ne permet pas de qualifier automatiquement une période comme signal faible.

## 7. Conclusion

La baseline naïve détecte davantage de semaines atypiques qu'Isolation Forest.

Dans cette expérimentation, les anomalies détectées par le modèle principal sont également retrouvées par la baseline.

Isolation Forest fournit cependant une sélection plus restreinte des semaines dont la combinaison des indicateurs thématiques est inhabituelle.

En l'absence de vérité terrain, il n'est pas possible d'affirmer qu'une semaine détectée correspond à un véritable signal faible.

Les résultats doivent donc être interprétés comme des périodes atypiques pouvant orienter une analyse humaine plus approfondie.
