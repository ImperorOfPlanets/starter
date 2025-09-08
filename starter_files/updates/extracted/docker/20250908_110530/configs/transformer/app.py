import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
import logging

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/transformers/trans.log'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SentenceTransformer Embedding Service")

# Сначала определяем все переменные окружения
MODEL_ID = os.getenv("MODEL_ID", "BAAI/bge-m3")
DEVICE = os.getenv("DEVICE", "auto")
NORMALIZE_EMBEDDINGS = os.getenv("NORMALIZE_EMBEDDINGS", "true").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))

# Затем инициализируем модель
if DEVICE == "auto":
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
elif DEVICE == "cuda" and not torch.cuda.is_available():
    logger.warning("CUDA requested but not available, falling back to CPU")
    DEVICE = "cpu"

try:
    logger.info(f"Loading model {MODEL_ID} on device: {DEVICE}")
    model = SentenceTransformer(MODEL_ID, device=DEVICE)
    if NORMALIZE_EMBEDDINGS:
        logger.info("Normalizing embeddings enabled")
    model.encode(["test sentence"], normalize_embeddings=NORMALIZE_EMBEDDINGS)
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise RuntimeError(f"Model loading failed: {str(e)}")

class EmbeddingRequest(BaseModel):
    texts: List[str]
    batch_size: Optional[int] = None
    normalize_embeddings: Optional[bool] = None

class HealthCheck(BaseModel):
    status: str
    device: str
    model: str
    normalize_embeddings: bool

@app.get("/health", response_model=HealthCheck)
async def health_check():
    return {
        "status": "healthy",
        "device": DEVICE,
        "model": MODEL_ID,
        "normalize_embeddings": NORMALIZE_EMBEDDINGS
    }

@app.post("/embed")
async def embed_texts(request: EmbeddingRequest):
    try:
        batch_size = request.batch_size or BATCH_SIZE
        normalize = request.normalize_embeddings if request.normalize_embeddings is not None else NORMALIZE_EMBEDDINGS
        
        logger.info(f"Processing {len(request.texts)} texts with batch_size={batch_size}")
        
        # Разбиваем на батчи для эффективной обработки
        embeddings = []
        for i in range(0, len(request.texts), batch_size):
            batch = request.texts[i:i + batch_size]
            batch_embeddings = model.encode(
                batch,
                normalize_embeddings=normalize,
                convert_to_tensor=False,
                device=DEVICE
            )
            embeddings.extend(batch_embeddings.tolist())
        
        return {"embeddings": embeddings}
    except Exception as e:
        logger.error(f"Embedding error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))