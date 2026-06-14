Agis comme un architecte logiciel senior et un expert en ingénierie de prompts LLM. 

Je suis officier supérieur de l'armée de Terre (BSPP (pompier de Paris) et employé dans le numérique (pilotage des données à la SIMMT (Structure Intégrée de la Mise en Condition Opérationnelle et de la Maintenance des Matériels Terrestres))). Je veux que tu me conçoives l'architecture technique complète et le code de base pour un projet de veille stratégique automatisée nommé "SynthesIA". 

L'objectif est d'obtenir chaque matin une synthèse ultra-condensée, neutre, factuelle et percutante des actualités dans les domaines PEMSI (Politique, Militaire, Économique, Société, Science/Technologie à vocation militaire, Géopolitique).

### Spécifications fonctionnelles du projet :
1. Collecte (Matinale) : Scraper le contenu (titres et corps d'articles) de flux RSS ou sites spécialisés ciblés.
2. Analyse LLM : Soumettre ces données à un LLM avec des instructions strictes pour extraire la "substantifique moelle" (voir prompts d'analyse ci-dessous).
3. Contextualisation : Le LLM doit systématiquement faire un parallèle historique ou un exemple choc ("c'est le même cas que ce qui s'est passé ici ou là...") pour marquer les esprits.
4. Mémoire (Base de données) : Stocker les synthèses quotidiennes dans une base de données (idéalement vectorielle ou graphe) pour permettre au système de faire des liens transversaux entre les événements actuels et passés.
5. Déploiement : L'application doit être codée de manière à pouvoir être exposée à terme sur un serveur personnel à la maison, accessible via une interface web simple ou une API sur smartphone.

### Structure des Prompts à intégrer au LLM :
Le LLM devra alterner ou combiner deux modes selon la nature de l'information brute reçue :

Mode A (Analyse de sources brutes) :
"Agis comme un analyste de recherche interarmées senior. Analyse les articles extraits ce jour. Produis une note de synthèse selon la structure suivante :
1. L'idée importante du jour : Le concept principal résumé en 1 ou 2 phrases max (clarté maximale).
2. Insights clés (3 points d'impact) : Les découvertes essentielles, ce que la plupart des gens ignorent, consensus vs débats.
3. Les conséquences ("So What ?") : Évolutions à 6 mois, directions futures probables, menaces ou opportunités opérationnelles/stratégiques.
4. Exemple choc / Parallèle historique : Fais un lien concret avec un événement historique ou un cas similaire passé pour marquer les esprits et mettre en perspective.
Format : Style soutenu, concis, direct, neutre. Pas de fioritures."

Mode B (Structuration de pensées/recherches transversales via la base de données) :
"Je te fournis mes pensées brutes ou une question transversale sur l'historique des données stockées. 
Ta mission : Clarifier l'idée centrale, organiser logiquement la hiérarchie des faits, identifier les pièces manquantes (hypothèses implicites, données absentes) et transformer le tout en une version actionnable avec les prochaines étapes concrètes."

### Ce que j'attends de toi maintenant :
1. Architecture Technique : Propose la stack technologique la plus adaptée, légère et robuste pour tourner sur un serveur perso sous WSL/Linux (ex: Python, LangChain/LangGraph, base de données adaptée comme PostgreSQL avec pgvector ou une base vectorielle simple, framework d'API comme FastAPI).
2. Structure du projet : Donne-moi l'arborescence des fichiers.
3. Code de base : Fournis le code Python initial pour la partie collecte (script de scraping/RSS de base), la configuration de la chaîne LLM (avec la clé API Anthropic) et l'insertion en base de données.
4. Stratégie de déploiement : Explique brièvement comment préparer l'application pour qu'elle soit accessible plus tard sur mobile depuis mon serveur domestique.

Va directement au but, utilise un ton technique, factuel et concis.