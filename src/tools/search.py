from ddgs import DDGS

def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    Performs a web search using DuckDuckGo.

    Args:
        query: The search string.
        max_results: Maximum number of results to return.

    Returns:
        List of dictionaries with 'title', 'href', and 'body'.
    """
    results = []
    try:
        with DDGS() as ddgs:
            # DDGS.text() returns an iterator
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)
    except Exception as e:
        print(f"Search API Error: {e}")
        return [{"error": str(e)}]

    return results

if __name__ == "__main__":
    # Simple test
    print("Searching for 'Python Programming'...")
    res = search_web("Python Programming", max_results=2)
    for item in res:
        print(f"- {item.get('title')}: {item.get('href')}")
