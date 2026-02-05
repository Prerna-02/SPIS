"""
SPIS Auth Service - Face Recognition (FaceNet)
"""
import base64
import io
import numpy as np
from typing import Optional, List, Tuple
from PIL import Image

# Lazy load to avoid slow startup
_mtcnn = None
_facenet = None


def _load_models():
    """Lazy load FaceNet and MTCNN models."""
    global _mtcnn, _facenet
    if _mtcnn is None:
        try:
            from facenet_pytorch import MTCNN, InceptionResnetV1
            import torch
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            _mtcnn = MTCNN(keep_all=False, device=device)
            _facenet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
            print(f"[OK] FaceNet models loaded on {device}")
        except ImportError as e:
            print(f"[WARN] Face recognition not available: {e}")
            raise RuntimeError("facenet-pytorch not installed")
    return _mtcnn, _facenet


def decode_base64_image(base64_str: str) -> Image.Image:
    """Decode base64 string to PIL Image."""
    # Remove data URL prefix if present
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    
    image_data = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_data))
    return image.convert("RGB")


def extract_embedding(image: Image.Image) -> Optional[np.ndarray]:
    """
    Extract 512-d face embedding from image.
    Returns None if no face detected.
    """
    try:
        mtcnn, facenet = _load_models()
        import torch
        
        # Detect and align face
        face_tensor = mtcnn(image)
        
        if face_tensor is None:
            return None
        
        # Add batch dimension if needed
        if face_tensor.dim() == 3:
            face_tensor = face_tensor.unsqueeze(0)
        
        # Get embedding
        device = next(facenet.parameters()).device
        face_tensor = face_tensor.to(device)
        
        with torch.no_grad():
            embedding = facenet(face_tensor)
        
        return embedding.cpu().numpy().flatten()
    
    except Exception as e:
        print(f"Face extraction error: {e}")
        return None


def extract_embedding_from_base64(base64_str: str) -> Optional[List[float]]:
    """Extract embedding from base64 image string."""
    try:
        image = decode_base64_image(base64_str)
        embedding = extract_embedding(image)
        if embedding is not None:
            return embedding.tolist()
        return None
    except Exception as e:
        print(f"Base64 extraction error: {e}")
        return None


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    embedding1 = np.array(embedding1).flatten()
    embedding2 = np.array(embedding2).flatten()
    
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def verify_face(stored_embedding: List[float], face_image_base64: str, threshold: float = 0.6) -> Tuple[bool, float]:
    """
    Verify face against stored embedding.
    Returns (verified: bool, similarity: float)
    """
    new_embedding = extract_embedding_from_base64(face_image_base64)
    
    if new_embedding is None:
        return False, 0.0
    
    similarity = cosine_similarity(stored_embedding, new_embedding)
    verified = similarity >= threshold
    
    return verified, similarity
