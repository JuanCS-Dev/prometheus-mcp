"""
Modal Hybrid Deployment for Juan-Dev-Code.

Hackathon Day 30 - Modal Innovation Award ($2,500)

ARQUITETURA HÍBRIDA ($280 budget):
├── $50  → Gradio UI serverless (CPU) - ~700 horas
├── $150 → Embeddings/RAG com GPU (T4) - indexar codebase
└── $80  → Llama 3.1 8B fallback (T4) - quando Gemini cai

Deploy: modal deploy modal_app.py
Dev: modal serve modal_app.py

Author: JuanCS Dev
Date: 2025-11-27
"""

import modal
import os

# =============================================================================
# MODAL APP
# =============================================================================

app = modal.App("juan-dev-code-hackathon")

# =============================================================================
# VOLUMES (Cache persistente)
# =============================================================================

# Cache para modelos HuggingFace (embeddings + Llama)
hf_cache = modal.Volume.from_name("juan-dev-hf-cache", create_if_missing=True)

# Cache para índice RAG
rag_index = modal.Volume.from_name("juan-dev-rag-index", create_if_missing=True)

# =============================================================================
# IMAGES
# =============================================================================

# Image para Gradio UI (leve, CPU)
gradio_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "gradio>=5.0.0,<6.0.0",
        "google-generativeai>=0.8.0",
        "httpx>=0.27.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
        "pandas>=2.0.0",
    )
    .add_local_dir("gradio_ui", "/root/gradio_ui")
    .add_local_dir("jdev_tui", "/root/jdev_tui")
    .add_local_dir("jdev_cli", "/root/jdev_cli")
)

# Image para Embeddings/RAG (GPU otimizada)
embeddings_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "sentence-transformers>=2.2.0",
        "faiss-cpu>=1.7.0",  # Índice vetorial
        "numpy>=1.24.0",
        "torch>=2.0.0",
    )
)

# Image para Llama 3.1 com vLLM (GPU)
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.11")
    .pip_install(
        "vllm>=0.4.0",
        "huggingface-hub>=0.20.0",
        "torch>=2.0.0",
    )
    .env({"HF_HOME": "/root/.cache/huggingface"})
)

# =============================================================================
# SECRETS
# =============================================================================

gemini_secret = modal.Secret.from_name("gemini-api-key")

# =============================================================================
# 1. GRADIO UI (CPU Serverless) - $50 budget
# =============================================================================

@app.function(
    image=gradio_image,
    secrets=[gemini_secret],
    cpu=1.0,
    memory=2048,
    timeout=600,
    min_containers=0,  # Scale to zero quando não usado
    scaledown_window=300,  # 5 min antes de desligar
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    """Gradio UI serverless - escala automática."""
    import sys
    sys.path.insert(0, "/root")

    from fastapi import FastAPI
    from gradio.routes import mount_gradio_app
    from gradio_ui.app import create_ui

    fastapi_app = FastAPI(title="Juan-Dev-Code")

    @fastapi_app.get("/health")
    async def health():
        return {"status": "healthy", "service": "gradio-ui"}

    demo, theme, css = create_ui()
    demo.queue(max_size=10, default_concurrency_limit=5)

    return mount_gradio_app(app=fastapi_app, blocks=demo, path="/")


# =============================================================================
# 2. EMBEDDINGS/RAG (GPU T4) - $150 budget
# =============================================================================

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims, rápido

@app.cls(
    image=embeddings_image,
    gpu="T4",
    timeout=300,
    volumes={"/root/.cache/huggingface": hf_cache, "/data/rag": rag_index},
)
class EmbeddingsService:
    """Serviço de embeddings para RAG."""

    @modal.enter()
    def load_model(self):
        """Carrega modelo de embeddings no startup."""
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.model.to("cuda")
        print(f"✅ Embeddings model loaded: {EMBEDDING_MODEL}")

    @modal.method()
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings para lista de textos."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @modal.method()
    def embed_single(self, text: str) -> list[float]:
        """Gera embedding para um texto."""
        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()

    @modal.method()
    def index_codebase(self, files: list[dict]) -> dict:
        """
        Indexa arquivos de código para RAG.

        Args:
            files: [{"path": "...", "content": "..."}]

        Returns:
            {"indexed": N, "index_path": "..."}
        """
        import faiss
        import numpy as np
        import json

        texts = [f["content"][:2000] for f in files]  # Trunca para embedding
        paths = [f["path"] for f in files]

        # Gera embeddings
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

        # Cria índice FAISS
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)  # Inner product (cosine com normalização)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        # Salva índice e metadata
        faiss.write_index(index, "/data/rag/codebase.index")
        with open("/data/rag/metadata.json", "w") as f:
            json.dump({"paths": paths, "model": EMBEDDING_MODEL}, f)

        rag_index.commit()

        return {"indexed": len(files), "index_path": "/data/rag/codebase.index"}

    @modal.method()
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Busca semântica no índice.

        Args:
            query: Texto de busca
            top_k: Número de resultados

        Returns:
            [{"path": "...", "score": 0.95}, ...]
        """
        import faiss
        import numpy as np
        import json

        # Carrega índice
        index = faiss.read_index("/data/rag/codebase.index")
        with open("/data/rag/metadata.json") as f:
            metadata = json.load(f)

        # Embed query
        query_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)

        # Busca
        scores, indices = index.search(query_emb, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(metadata["paths"]):
                results.append({
                    "path": metadata["paths"][idx],
                    "score": float(score),
                })

        return results


# =============================================================================
# 3. LLAMA 3.1 8B FALLBACK (GPU T4) - $80 budget
# =============================================================================

LLAMA_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

@app.cls(
    image=vllm_image,
    gpu="T4",
    timeout=300,
    volumes={"/root/.cache/huggingface": hf_cache},
    secrets=[modal.Secret.from_name("huggingface-token")],
)
class LlamaFallback:
    """Llama 3.1 8B como fallback quando Gemini falha."""

    @modal.enter()
    def load_model(self):
        """Carrega Llama com vLLM."""
        from vllm import LLM, SamplingParams

        self.llm = LLM(
            model=LLAMA_MODEL,
            tensor_parallel_size=1,
            gpu_memory_utilization=0.9,
            max_model_len=4096,
            trust_remote_code=True,
        )
        self.sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048,
        )
        print(f"✅ Llama model loaded: {LLAMA_MODEL}")

    @modal.method()
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Gera resposta com Llama.

        Args:
            prompt: Prompt do usuário
            system_prompt: Instruções de sistema

        Returns:
            Texto gerado
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Formata para Llama 3.1 chat template
        formatted = self._format_chat(messages)

        outputs = self.llm.generate([formatted], self.sampling_params)
        return outputs[0].outputs[0].text

    def _format_chat(self, messages: list[dict]) -> str:
        """Formata mensagens para Llama 3.1 chat template."""
        formatted = "<|begin_of_text|>"
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return formatted

    @modal.method()
    def health_check(self) -> dict:
        """Verifica se o modelo está carregado."""
        return {
            "status": "healthy",
            "model": LLAMA_MODEL,
            "gpu": "T4",
        }


# =============================================================================
# 4. UNIFIED API (Orquestra Gemini + Llama fallback)
# =============================================================================

@app.function(
    image=gradio_image,
    secrets=[gemini_secret],
    timeout=120,
)
async def smart_generate(prompt: str, system_prompt: str = "", use_rag: bool = False) -> dict:
    """
    API unificada que usa Gemini com fallback para Llama.

    Args:
        prompt: Prompt do usuário
        system_prompt: Instruções de sistema
        use_rag: Se True, busca contexto no índice RAG primeiro

    Returns:
        {"response": "...", "provider": "gemini|llama", "rag_context": [...]}
    """
    import sys
    sys.path.insert(0, "/root")

    result = {
        "response": "",
        "provider": "gemini",
        "rag_context": [],
    }

    # 1. RAG: Busca contexto relevante
    if use_rag:
        try:
            embeddings_svc = EmbeddingsService()
            rag_results = embeddings_svc.search.remote(prompt, top_k=3)
            result["rag_context"] = rag_results

            # Adiciona contexto ao prompt
            if rag_results:
                context = "\n".join([f"- {r['path']} (score: {r['score']:.2f})" for r in rag_results])
                prompt = f"Relevant files:\n{context}\n\nUser question: {prompt}"
        except Exception as e:
            print(f"RAG search failed: {e}")

    # 2. Tenta Gemini primeiro
    try:
        from jdev_tui.core.llm_client import GeminiClient

        client = GeminiClient()
        response = await client.generate(prompt, system_prompt)
        result["response"] = response
        result["provider"] = "gemini"
        return result

    except Exception as gemini_error:
        print(f"Gemini failed: {gemini_error}")

    # 3. Fallback para Llama
    try:
        llama = LlamaFallback()
        response = llama.generate.remote(prompt, system_prompt)
        result["response"] = response
        result["provider"] = "llama-fallback"
        return result

    except Exception as llama_error:
        print(f"Llama fallback failed: {llama_error}")
        result["response"] = f"Both Gemini and Llama failed. Gemini: {gemini_error}, Llama: {llama_error}"
        result["provider"] = "error"
        return result


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

@app.local_entrypoint()
def main():
    """CLI para testar os serviços."""
    print("🚀 Juan-Dev-Code Modal Hybrid")
    print("=" * 50)
    print()
    print("Serviços disponíveis:")
    print("  1. Gradio UI      → modal serve modal_app.py")
    print("  2. Embeddings/RAG → EmbeddingsService.embed_texts.remote([...])")
    print("  3. Llama Fallback → LlamaFallback.generate.remote('...')")
    print("  4. Smart Generate → smart_generate.remote('...', use_rag=True)")
    print()
    print("Deploy:")
    print("  modal deploy modal_app.py")
    print()
    print("Custos estimados ($280 budget):")
    print("  - Gradio UI (CPU):  ~$0.07/h → 700h com $50")
    print("  - Embeddings (T4):  ~$0.59/h → 250h com $150")
    print("  - Llama (T4):       ~$0.59/h → 135h com $80")
    print()
