from semantic_router import Route
from semantic_router.routers import SemanticRouter
from semantic_router.encoders import HuggingFaceEncoder
import semantic_router

print("Semantic Router Version:", semantic_router.__version__)
print("Location:", semantic_router.__file__)

router = None

# =====================================================
# ENCODER
# =====================================================
try:
    print("Loading HuggingFace encoder...")

    encoder = HuggingFaceEncoder(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    print("Encoder loaded successfully.")

    # =====================================================
    # ROUTES
    # =====================================================
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
            "Search for Nike or Adidas products.",
            "Show me cheapest clothes available.",
            "Find discounted shoes"
        ]
    )

    small_talk = Route(
        name="small_talk",
        utterances=[
            "How are you?",
            "What is your name?",
            "Are you a bot?",
            "Tell me a joke.",
            "What's the weather like today?",
            "What do you do?"
        ]
    )

    # =====================================================
    # ROUTER
    # =====================================================
    router = SemanticRouter(
        encoder=encoder,
        routes=[faq, sql, small_talk]
    )

    print("\nRouter created successfully")
    print("Routes:", [r.name for r in router.routes])

    # =====================================================
    # FIX: BUILD INDEX (IMPORTANT FOR YOUR VERSION)
    # =====================================================
    print("\nBuilding / syncing index...")

    try:
        router.sync(sync_mode="local")   # 🔥 FIX FOR YOUR ERROR
        print("Index synced successfully.")
    except Exception as e:
        print("Sync failed:", e)

except Exception as e:
    print("Initialization failed:", e)
    router = None


# =====================================================
# RESULT WRAPPER
# =====================================================
class RouteResult:
    def __init__(self, name: str, score: float = 1.0):
        self.name = name
        self.score = score


# =====================================================
# ROUTER FUNCTION
# =====================================================
def safe_route(query: str):

    if router is not None:
        try:
            result = router(query)

            print(f"\nQuery: {query}")
            print("Raw result:", result)

            if result and getattr(result, "name", None):
                score = (
                    getattr(result, "similarity_score", None)
                    or getattr(result, "score", None)
                    or 0.0
                )

                return RouteResult(result.name, score)

        except Exception as e:
            print("Router error:", e)

    # =====================================================
    # FALLBACK KEYWORD ROUTING
    # =====================================================
    q = query.lower()

    sql_keywords = [
        "show", "list", "find", "price", "discount",
        "rating", "brand", "nike", "adidas", "puma",
        "shoes", "products"
    ]

    faq_keywords = [
        "return", "refund", "shipment", "shipping",
        "track", "tracking", "order", "payment",
        "checkout", "package"
    ]

    small_talk_keywords = [
        "how are you", "your name", "bot",
        "joke", "weather", "what do you do"
    ]

    if any(k in q for k in sql_keywords):
        return RouteResult("sql", 0.5)

    if any(k in q for k in faq_keywords):
        return RouteResult("faq", 0.5)

    if any(k in q for k in small_talk_keywords):
        return RouteResult("small_talk", 0.5)

    return RouteResult("faq", 0.25)


# =====================================================
# TESTING
# =====================================================
def main():

    test_queries = [
        "What is your return policy?",
        "How do I track my order?",
        "Show me Nike shoes with discount",
        "Shoes under 3000",
        "Puma shoes on sale",
        "What payment methods are accepted?",
        "Tell me a joke.",
        "What is your name?"
    ]

    print("\n" + "=" * 60)
    print("RUNNING TEST QUERIES")
    print("=" * 60)

    for query in test_queries:
        result = safe_route(query)

        print("\n--------------------------------")
        print("Query :", query)
        print("Route :", result.name)
        print("Score :", result.score)


if __name__ == "__main__":
    main()