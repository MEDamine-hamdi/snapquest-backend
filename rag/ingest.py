import json
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from dotenv import load_dotenv
import os

load_dotenv()

def load_challenges_from_jsonl(path: str) -> list[Document]:
    """
    Charge le fichier JSONL et convertit chaque défi en Document LangChain.
    Le 'page_content' est le texte qui sera vectorisé.
    Les 'metadata' stockent les infos structurées pour le filtrage.
    """
    documents = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            inp = json.loads(entry["input"]) if isinstance(entry["input"], str) else entry["input"]
            out = json.loads(entry["output"]) if isinstance(entry["output"], str) else entry["output"]

            # Texte riche pour l'embedding — inclut tout ce qui aide à trouver le bon défi
            content = f"""
Titre: {out['title']}
Description: {out['description']}
Catégorie: {out['category']}
Difficulté: {out['difficulty']}
Durée: {out.get('time_estimate', 'N/A')}
Lieu: {out.get('location_hint', 'Tunisie')}
Étapes: {' | '.join(out.get('steps', []))}
Tags: {', '.join(out.get('tags', []))}
Profil idéal: âge {inp.get('age_range','')}, intérêts {','.join(inp.get('interests',[]))}, {inp.get('location_type','')} {inp.get('weather','')} budget {inp.get('budget','')}
            """.strip()

            doc = Document(
                page_content=content,
                metadata={
                    "title": out["title"],
                    "category": out["category"],
                    "difficulty": out["difficulty"],
                    "xp_reward": out["xp_reward"],
                    "location_hint": out.get("location_hint", ""),
                    "proof_required": out.get("proof_required", ""),
                    "steps": json.dumps(out.get("steps", [])),
                    "time_estimate": out.get("time_estimate", ""),
                    "tip": out.get("tip", ""),
                    "tags": ",".join(out.get("tags", [])),
                    "budget": inp.get("budget", ""),
                    "age_range": inp.get("age_range", ""),
                    "weather": inp.get("weather", ""),
                }
            )
            documents.append(doc)
    return documents

def ingest():
    print("📥 Chargement des défis depuis JSONL...")
    docs = load_challenges_from_jsonl("data/snapquest_challenge.jsonl")
    print(f"✅ {len(docs)} défis chargés")

    print("🧮 Création des embeddings et ingestion dans ChromaDB...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings
    )

    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        vectorstore.add_documents(batch)
        print(f"  ✓ {min(i + batch_size, len(docs))}/{len(docs)} ingérés...")

    print(f"🎉 Ingestion terminée ! {vectorstore._collection.count()} vecteurs stockés.")
    
if __name__ == "__main__":
    ingest()