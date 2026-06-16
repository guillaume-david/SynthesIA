"""Client Anthropic partagé — charge la clé API depuis .env.

La clé vit dans le fichier .env à la racine (git-ignoré), jamais dans le code.
`load_dotenv()` la pousse dans l'environnement ; le SDK la lit tout seul.
"""

from __future__ import annotations

from pathlib import Path

import anthropic

import os
from google import genai
from google.genai import errors

from dotenv import load_dotenv



# Modèles Gemini équivalents
MODELE_TRI = "gemini-2.5-flash"      # Rapide et économique (équivalent Haiku)
MODELE_SYNTHESE = "gemini-2.5-flash"   # le pro me coutait trop cher...

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

def get_client() -> genai.Client:
    """Renvoie un client Gemini prêt à l'emploi."""
    load_dotenv(_ENV_PATH)
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            f"Clé API introuvable. Vérifie GEMINI_API_KEY dans {_ENV_PATH}."
        )
    try:
        return genai.Client()
    except errors.APIError as exc:
        raise RuntimeError(f"Erreur d'initialisation du client Gemini.") from exc
    

'''
# Modèles validés pour le projet (cf. docs/plan-implementation.md).
MODELE_TRI = "claude-haiku-4-5"        # passe 1 : rapide, peu cher, sur titres
MODELE_SYNTHESE = "claude-sonnet-4-6"  # mode A : analyse corrélée fine

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

def get_client() -> anthropic.Anthropic:
    """Renvoie un client Anthropic prêt à l'emploi.

    Lève une erreur claire si la clé est absente, plutôt qu'un échec obscur
    au premier appel réseau.
    """
    load_dotenv(_ENV_PATH)
    try:
        return anthropic.Anthropic()
    except anthropic.AnthropicError as exc:  # clé manquante / mal formée
        raise RuntimeError(
            f"Clé API introuvable. Vérifie ANTHROPIC_API_KEY dans {_ENV_PATH}."
        ) from exc
'''