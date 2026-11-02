from enum import StrEnum


class PublicationSource(StrEnum):
    """Where an `Listing.published_at` value came from.

    SITE — the listing itself advertises this date, so it is the real "parution".
    FIRST_SEEN — the site publishes no date; the value is our first crawl time,
    which only bounds the real publication date from above (it is never older).
    """

    SITE = "site"
    FIRST_SEEN = "first_seen"
