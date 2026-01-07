from database import get_all_ad_ids

class ID:
    def __init__(self):
        """
        Initializes the ID checker by loading all existing ad IDs
        from the central SQLite database.
        """
        self._ids = get_all_ad_ids()

    def add(self, ad_id: str) -> bool:
        """
        Checks if an ad_id is new. Returns True if the ID is not already
        in our list of known IDs, False otherwise.

        The actual saving is handled by the `handle` function, which
        writes to the database. This class just prevents re-processing.
        """
        if ad_id not in self._ids:
            # The ID is new. Add it to the in-memory list for this session
            # to prevent processing it again in the same run.
            self._ids.append(ad_id)
            return True
        # The ID is already known, so it's not a new ad.
        return False
