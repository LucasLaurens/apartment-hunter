from ...domain.entities import SearchFilter
from ...domain.ports import ListingRepositoryPort


class ManageFilters:
    def __init__(self, repository: ListingRepositoryPort):
        self._repository = repository

    async def save(self, search_filter: SearchFilter) -> None:
        await self._repository.save_filter(search_filter)

    async def list_all(self) -> list[SearchFilter]:
        return await self._repository.load_filters()

    async def delete(self, filter_id: str) -> None:
        await self._repository.delete_filter(filter_id)
