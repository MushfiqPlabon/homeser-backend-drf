# Vulture whitelist for legitimate unused variables
# These are required by Python/Django/Channels conventions but not used in implementation


# Context manager protocol (__exit__ method signature)
# Used in api/smart_prefetch.py line 21
def __exit__(self, exc_type, exc_val, exc_tb):
    pass


# Test fixtures
# Used in api/tests_property_based.py line 21
view_class = None
