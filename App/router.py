from semantic_router import Route
from semantic_router import Route
from semantic_router.routers import SemanticRouter

# Try to import and initialize the HuggingFace encoder and router.
# If any import or runtime error occurs (missing torch/transformers, DLLs,
# etc.), fall back to leaving `router` as None so `safe_route` can use a
# keyword-based fallback.
try:
    from semantic_router.encoders import HuggingFaceEncoder

    # -----------------------
    # ENCODER (load once)
    # -----------------------
    encoder = HuggingFaceEncoder(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # -----------------------
    # ROUTES
    # -----------------------
    faq = Route(
        name="faq",
        utterances=[
            "How do I track my shipment?",
            "Where is my package right now?",
            "Can you help me check my order status?",
            "What is your return policy for damaged items?",
            "How long does a refund take to process?",
            "What payment methods do you accept at checkout?",
            "I received a defective product, what should I do?"
        ]
    )

    sql = Route(
        name="sql",
        utterances=[
            "Show me all products under a specific price range.",
            "List all items with a high discount percentage.",
            "Find me shoes with ratings above a certain score.",
            "All product which has a high discount and top ratings.",
            "Search for specific brands like Nike or Adidas with filters.",
            "Show me the cheapest clothes available."
        ]
    )

    # -----------------------
    # Initialize router
    # -----------------------
    router = SemanticRouter(
        encoder=encoder,
        routes=[faq, sql],
        auto_sync="local"
    )
except Exception:
    # If initialization fails, ensure `router` exists but is None.
    router = None



# -----------------------
# Test / Safe routing
# -----------------------
class RouteResult:
    def __init__(self, name: str, score: float = 1.0):
        self.name = name
        self.score = score


def main():
    test_queries = [
        "What is your return policy?",
        "How do I track my order?",
        "Show me Nike shoes with discount",
        "Shoes under 3000",
        "Puma shoes on sale",
        "What payment methods are accepted?"
    ]

    for q in test_queries:
        r = safe_route(q)
        print(f"\nQuery: {q}")
        print(f"Route: {r.name if r else 'None'} (score={getattr(r,'score',None)})")


def safe_route(query: str):
    """Return an object with `.name` and `.score`.

    Tries the semantic `router` first. If that fails (missing ML deps
    or low-confidence), falls back to a simple keyword heuristic.
    """
    try:
        result = router(query)
        if result and getattr(result, "name", None) and getattr(result, "score", 0) > 0.55:
            return result
    except Exception:
        # encoder or model not available; fall through to heuristic
        pass

    # Keyword-based fallback (simple and deterministic)
    q = query.lower()
    sql_keywords = ["select", "where", "from", "show", "list", "order", "price", "discount", "rating", "ratings", "brand", "find", "filter"]
    if any(k in q for k in sql_keywords):
        return RouteResult("sql", score=0.5)

    return RouteResult("faq", score=0.5)


if __name__ == "__main__":
    main()