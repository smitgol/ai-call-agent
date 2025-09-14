import json
import hashlib
from typing import List, Dict, Optional, Tuple
from redisvl.extensions.llmcache import SemanticCache



#redisClient = SemanticCache(
#    redis_url="redis://default:bZf9Vrqi1f3yOyxsJwsVXHRUXLTHo3Lm@redis-14549.c11.us-east-1-3.ec2.redns.redis-cloud.com:14549",
#    distance_threshold=0.5,
#    name="llm_cache")

redisClient = None


class SemanticCacheRedis:        

    def _hash_context(self, context: List[Dict[str, str]]) -> str:
        """Create consistent hash for conversation context"""
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()

    async def get_cache_entry(self, context: List[Dict[str, str]], query: str):
        """
        Hybrid cache lookup with exact match fallback and semantic search
        Returns tuple of (response, score) if found
        """
       # _formatted_input = self._format_input(context, query)
        # Check for exact match in cache
        #response
        exact_match = redisClient.check(json.dumps(context))
        if exact_match:
            print("exact_match", exact_match[0]['response'])
            #return {"response":exact_match[0]['response'], "tool_func":exact_match[0].metadata["tool_func"]}
            return None
        return None

    async def set_cache_entry(self, context: List[Dict[str, str]], response: str, tool_func = ""):
        """Store entry with both exact match and semantic cache"""
        query = context[-1]["content"]
        context.remove({"role": "user", "content": query})
        #_formatted_input = self._format_input(context, query)
        redisClient.store(json.dumps(context), response, metadata={"tool_func": tool_func})

    def _format_input(self, context: List[Dict[str, str]], query: str) -> str:
        """Format context and query for embedding generation"""
        context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context])
        return f"Context:\n{context_text}\n\nQuery: {query}"
    

'''    
import json
import os
from typing import List, Dict, Optional, Any
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class LLMCacheLocal:
    def __init__(self, cache_path: str = "llm_cache"):
        self.cache_path = cache_path
        self.dimension = 384  # Same dimension works for multilingual model
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        
        # Initialize data structures
        self.exact_cache = {}     # Exact match cache
        self.query_list = []      # Stores metadata with embeddings
        self.index = faiss.IndexFlatIP(self.dimension)  # FAISS index
        
        # Create cache directory with proper permissions
        os.makedirs(self.cache_path, exist_ok=True)
        
        # Load existing cache with UTF-8 encoding
        self.load_cache()

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate and normalize text embedding for Hindi text"""
        embedding = self.model.encode(text, convert_to_tensor=True).cpu().numpy()
        return embedding / np.linalg.norm(embedding)

    def _format_query(self, context: List[Dict[str, str]], query: str) -> str:
        """Format context and query preserving Hindi characters"""
        context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context])
        return f"संदर्भ:\n{context_text}\n\nप्रश्न: {query}"

    def add_cache(self, context: List[Dict[str, str]], query: str, response: str, tool_func: str) -> None:
        """Add Hindi text entry to cache"""
        formatted_query = self._format_query(context, query)
        
        # Add to exact cache
        self.exact_cache[formatted_query] = {
            "response": response,
            "tool_func": tool_func
        }
        
        # Generate and store embedding
        embedding = self._get_embedding(formatted_query)
        self.query_list.append({
            "query": formatted_query,
            "embedding": embedding.tolist()
        })
        
        # Add to FAISS index
        self.index.add(np.array([embedding]))

    def get_cache(self, context: List[Dict[str, str]], query: str) -> Optional[Dict[str, Any]]:
        """Check cache for Hindi queries"""
        formatted_query = self._format_query(context, query)
        
        # First check exact match
        if formatted_query in self.exact_cache:
            return self.exact_cache[formatted_query]
        
        # Then check semantic similarity
        if len(self.query_list) > 0:
            query_embedding = self._get_embedding(formatted_query)
            distances, indices = self.index.search(np.array([query_embedding]), 1)
            
            if distances[0][0] > 0.92:  # Slightly lower threshold for Hindi
                matched_query = self.query_list[indices[0][0]]["query"]
                return self.exact_cache.get(matched_query)
        return None

    def save_cache(self) -> None:
        """Save cache with UTF-8 encoding"""
        cache_data = {
            "exact_cache": self.exact_cache,
            "query_list": self.query_list
        }
        
        with open(os.path.join(self.cache_path, "cache.json"), "w", encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)  # Preserve Hindi characters
        
        faiss.write_index(self.index, os.path.join(self.cache_path, "index.faiss"))

    def load_cache(self) -> None:
        """Load cache with UTF-8 encoding"""
        try:
            with open(os.path.join(self.cache_path, "cache.json"), "r", encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.exact_cache = cache_data["exact_cache"]
            self.query_list = cache_data["query_list"]
            
            # Convert embeddings back to numpy arrays
            for item in self.query_list:
                item["embedding"] = np.array(item["embedding"], dtype=np.float32)
            
            # Rebuild FAISS index
            if len(self.query_list) > 0:
                embeddings = np.array([item["embedding"] for item in self.query_list])
                self.index.add(embeddings)
            
            print(f"कैश लोड किया गया: {len(self.exact_cache)} प्रविष्टियाँ")
        
        except FileNotFoundError:
            print("कोई मौजूदा कैश नहीं मिला, नई शुरुआत कर रहे हैं")

    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.exact_cache.clear()
        self.query_list.clear()
        self.index.reset()
        self.save_cache()
'''