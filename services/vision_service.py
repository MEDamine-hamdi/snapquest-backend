import hashlib
import json
import base64
import os
from dotenv import load_dotenv
from groq import Groq
from database import supabase

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


async def verify_challenge_photo(photo_base64: str, proof_required: str, challenge_title: str, category: str):
    # 1. Check for duplicate photos
    photo_hash = hashlib.md5(photo_base64.encode()).hexdigest()
    existing = supabase.table("photo_hashes").select("id").eq("hash", photo_hash).execute()
    if existing.data:
        return {
            "validated": False,
            "score": 0,
            "message": "Cette photo a déjà été utilisée !"
        }

    # 2. Analyse Groq Vision
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{photo_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": f"""Tu es un système de validation de défis photo.

Défi : {challenge_title} (catégorie: {category})
Preuve requise : {proof_required}

Règles :
- Vérifie si la photo correspond à la preuve requise.
- Détecte si c'est un screenshot, une image Google ou affichée sur écran.
- Donne un score sur 100.
- Réponds UNIQUEMENT en JSON valide, rien d'autre, pas de markdown.

Format :
{{
  "validated": true,
  "score": 85,
  "message": "Bonne photo !"
}}"""
                    }
                ]
            }
        ],
        max_tokens=300
    )

    result_text = response.choices[0].message.content.strip()

    # 3. Save hash
    supabase.table("photo_hashes").insert({"hash": photo_hash}).execute()

    try:
        clean = result_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"validated": False, "score": 0, "message": "Erreur d'analyse, réessaie."}