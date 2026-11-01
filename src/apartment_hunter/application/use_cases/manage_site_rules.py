from ...domain.ports import ListingRepositoryPort
from ...domain.value_objects import SiteRules


class ManageSiteRules:
    """Read or change whether crawls follow robots.txt and the sites' terms (ADR-0012).

    The web page and `hunt rules` both come through here; the next crawl reads it.
    """

    def __init__(self, repository: ListingRepositoryPort):
        self._repository = repository

    async def load_site_rules(self) -> SiteRules:
        return await self._repository.load_site_rules()

    async def save_site_rules(self, rules: SiteRules) -> None:
        await self._repository.save_site_rules(rules)
