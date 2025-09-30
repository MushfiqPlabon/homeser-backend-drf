# utils/advanced_data_structures/trie.py
# Trie implementation for prefix-based searches

import logging

logger = logging.getLogger(__name__)


class TrieNode:
    """Node in the Trie data structure."""

    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.is_end_of_word = False
        self.word_data: dict | None = None  # Store additional data about the word


class Trie:
    """Trie implementation for efficient prefix-based searches.
    Useful for autocomplete functionality.
    Simplified implementation to focus on core functionality.
    """

    def __init__(self, cache_key: str = "trie_data"):
        self.root = TrieNode()

    def insert(self, word: str, data: dict | None = None) -> None:
        """Insert a word into the Trie.

        Args:
            word: Word to insert
            data: Optional data to associate with the word

        """
        node = self.root
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.word_data = data

    def search(self, word: str) -> bool:
        """Check if a word exists in the Trie.

        Args:
            word: Word to search for

        Returns:
            bool: True if word exists

        """
        node = self._find_node(word.lower())
        return node is not None and node.is_end_of_word

    def _find_node(self, prefix: str) -> TrieNode | None:
        """Find the node corresponding to the end of the prefix.

        Args:
            prefix: Prefix to search for

        Returns:
            TrieNode: Node at the end of prefix, or None if not found

        """
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def get_words_with_prefix(self, prefix: str, limit: int = 10) -> list[dict]:
        """Get all words that start with the given prefix.

        Args:
            prefix: Prefix to search for
            limit: Maximum number of results to return

        Returns:
            List[Dict]: List of words with their data

        """
        node = self._find_node(prefix.lower())
        if not node:
            return []

        results = []
        self._collect_words(node, prefix.lower(), results, limit)
        return results

    def _collect_words(
        self, node: TrieNode, prefix: str, results: list[dict], limit: int,
    ) -> None:
        """Collect words from a given node.

        Args:
            node: Starting node
            prefix: Current prefix
            results: List to append results to
            limit: Maximum number of results

        """
        if len(results) >= limit:
            return

        if node.is_end_of_word:
            results.append({"word": prefix, "data": node.word_data})

        for char, child_node in node.children.items():
            if len(results) >= limit:
                return
            self._collect_words(child_node, prefix + char, results, limit)

    def update_service_data(self, service_name: str, service_data: dict) -> bool:
        """Update the data associated with a service name in the Trie.

        Args:
            service_name: Name of the service
            service_data: New data to associate with the service

        Returns:
            bool: True if successful, False otherwise

        """
        try:
            # Simply insert/update the service name with new data
            self.insert(service_name, service_data)
            return True
        except Exception as e:
            logger.error(
                f"Error updating service data for '{service_name}' in Trie: {e}",
            )
            return False


# Global instance for service name autocomplete
service_name_trie = Trie("homeser_service_names")
