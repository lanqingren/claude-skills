"""
web复合搜索 - 智能多引擎聚合搜索工具
"""

from .search import CompositeSearch, SearchResult, ENGINES, ROUTING_RULES

__version__ = "1.1.0"
__all__ = ["CompositeSearch", "SearchResult", "ENGINES", "ROUTING_RULES"]
