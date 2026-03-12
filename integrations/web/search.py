from dataclasses import dataclass

from duckduckgo_search import DDGS


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearcher:
    def search(self, query: str, max_results: int = 5) -> str:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r["title"],
                    url=r["href"],
                    snippet=r["body"],
                ))
        return self._format_results(results)

    def search_news(self, query: str, max_results: int = 5) -> str:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("body", ""),
                ))
        return self._format_results(results)

    def _format_results(self, results: list[SearchResult]) -> str:
        if not results:
            return "Aucun résultat trouvé."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"**{i}. {r.title}**\n   {r.url}\n   {r.snippet}")
        return "\n\n".join(lines)
