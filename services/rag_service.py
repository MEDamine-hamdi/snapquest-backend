from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import ChatPromptTemplate
import json, os

# Charger le vector store une seule fois au démarrage
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma(
    persist_directory="../rag/chroma_db",
    embedding_function=embeddings
)
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7, groq_api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """Tu es SnapBot, un guide IA enthousiaste spécialisé dans les activités en Tunisie.
Ton rôle : analyser le profil de l'utilisateur et lui recommander UN défi parfaitement adapté.

RÈGLES :
- Sois chaleureux, motivant, comme un ami qui connaît bien la Tunisie
- Choisis le défi le plus pertinent parmi ceux fournis
- Présente-le de façon engageante en 2-3 phrases
- Mentionne le lieu et ce qui le rend spécial
- Réponds TOUJOURS en JSON avec ce format exact :
{
  "reply": "Texte de réponse pour l'utilisateur",
  "selected_challenge_index": 0
}
"""

async def get_personalized_challenge(
    user_message: str,
    user_profile: dict,
    history: list
) -> dict:
    """
    1. Construit une requête enrichie avec le profil utilisateur
    2. Cherche les 5 défis les plus similaires dans ChromaDB
    3. Envoie le tout à Groq (Llama 3.1 70B) pour sélection + réponse
    4. Retourne la réponse + le défi structuré
    """
    # Requête enrichie pour meilleur matching
    enriched_query = f"""
    {user_message}
    Profil: {user_profile.get('age_range','')}, 
    intérêts: {','.join(user_profile.get('interests',[]))}
    """

    # Retrieval : top 5 défis similaires
    docs = vectorstore.similarity_search(enriched_query, k=5)

    # Construire le contexte pour le LLM
    challenges_context = ""
    challenges_data = []
    for i, doc in enumerate(docs):
        m = doc.metadata
        challenges_context += f"""
DÉFI {i} :
- Titre: {m['title']}
- Lieu: {m['location_hint']}
- Difficulté: {m['difficulty']} | XP: {m['xp_reward']}
- Durée: {m['time_estimate']}
- Description: {doc.page_content[:200]}...
- Étapes: {m['steps'][:100]}
- Preuve requise: {m['proof_required']}
- Conseil: {m['tip']}
        """
        challenges_data.append({
            "title": m["title"],
            "category": m["category"],
            "difficulty": m["difficulty"],
            "xp_reward": m["xp_reward"],
            "location_hint": m["location_hint"],
            "proof_required": m["proof_required"],
            "steps": json.loads(m.get("steps", "[]")),
            "time_estimate": m["time_estimate"],
            "tip": m["tip"]
        })

    # Prompt final au LLM
    user_context = f"""
MESSAGE UTILISATEUR: {user_message}
PROFIL: {json.dumps(user_profile, ensure_ascii=False)}
HISTORIQUE (dernier échange): {json.dumps([{"role": m.role, "content": m.content} for m in history[-2:]], ensure_ascii=False) if history else 'Aucun'}

DÉFIS DISPONIBLES:
{challenges_context}

Choisis le défi le plus adapté et réponds en JSON valide.
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_context}
    ]

    response = await llm.ainvoke(messages)
    result = json.loads(response.content)
    selected_idx = result.get("selected_challenge_index", 0)

    return {
        "reply": result["reply"],
        "challenge": challenges_data[selected_idx]
    }