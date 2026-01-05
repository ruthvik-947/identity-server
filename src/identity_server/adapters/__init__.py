from .local_files import LocalFilesAdapter
from .git_repos import GitReposAdapter
from .rss import RSSAdapter
from .custom import CustomAdapter

__all__ = ["LocalFilesAdapter", "GitReposAdapter", "RSSAdapter", "CustomAdapter"]
