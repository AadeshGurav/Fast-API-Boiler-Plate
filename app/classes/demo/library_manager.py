"""Library management demo showcasing simple library operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core.class_store import get_class_store
from app.services.data.policies import CachePolicy

if TYPE_CHECKING:
    from app.services.data import DataService
    from app.services.logger import Logger
    from config import Config

class_store = get_class_store()


@class_store.register(name="library_manager")
class LibraryManager:
    """Demo class showcasing simple library management operations.

    Demonstrates book management, checkout/return operations, and
    user integration using real services.
    """

    def __init__(
        self: LibraryManager,
        data_service: DataService | None = None,
        logger: Logger | None = None,
        config: Config | None = None,
    ):
        """Initialize LibraryManager with service injection.

        Args:
        ----
            data_service: Data service (auto-injected)
            logger: Logger service (auto-injected)
            config: Config service (auto-injected)

        """
        self.data_service = data_service
        self.logger = logger
        self.config = config
        self.books_collection = "library_books"
        self.checkouts_collection = "library_checkouts"

    async def add_book(self: LibraryManager, book_data: dict[str, Any]) -> str:
        """Add a new book to the library.

        Args:
        ----
            book_data: Book data dictionary with title, author, isbn, etc.

        Returns:
        -------
            Created book ID.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        book_id = book_data.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        book = {
            "id": book_id,
            "title": book_data.get("title", ""),
            "author": book_data.get("author", ""),
            "isbn": book_data.get("isbn", ""),
            "available": True,
            "created_at": now,
            "updated_at": now,
        }

        await self.data_service.set(
            self.books_collection,
            {"id": book_id},
            book,
            policy=CachePolicy.DB_ONLY,
        )

        if self.logger:
            self.logger.info(
                f"Added book to library: {book_id}",
                extra={"book_id": book_id, "title": book.get("title")},
            )

        return book_id

    async def list_books(self: LibraryManager) -> list[dict[str, Any]]:
        """List all books in the library.

        Returns
        -------
            List of book dictionaries.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        books = await self.data_service.find_many(
            self.books_collection, {}, policy=CachePolicy.AUTO
        )

        if self.logger:
            self.logger.debug(
                f"Listed {len(books)} books",
                extra={"book_count": len(books)},
            )

        return books or []

    async def get_book(self: LibraryManager, book_id: str) -> dict[str, Any] | None:
        """Get book by ID.

        Args:
        ----
            book_id: Book ID.

        Returns:
        -------
            Book dictionary or None if not found.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        book = await self.data_service.get(
            self.books_collection, {"id": book_id}, policy=CachePolicy.AUTO
        )

        return book

    async def checkout_book(self: LibraryManager, book_id: str, user_id: str) -> str:
        """Check out a book to a user.

        Args:
        ----
            book_id: Book ID.
            user_id: User ID.

        Returns:
        -------
            Checkout record ID.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        book = await self.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        if not book.get("available", False):
            raise ValueError(f"Book is not available: {book_id}")

        checkout_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        checkout = {
            "id": checkout_id,
            "book_id": book_id,
            "user_id": user_id,
            "checkout_date": now,
            "return_date": None,
            "created_at": now,
        }

        await self.data_service.set(
            self.checkouts_collection,
            {"id": checkout_id},
            checkout,
            policy=CachePolicy.DB_ONLY,
        )

        await self.data_service.set(
            self.books_collection,
            {"id": book_id},
            {"available": False, "updated_at": now},
            policy=CachePolicy.DB_ONLY,
        )

        if self.logger:
            self.logger.info(
                f"Checked out book: {book_id} to user: {user_id}",
                extra={
                    "book_id": book_id,
                    "user_id": user_id,
                    "checkout_id": checkout_id,
                },
            )

        return checkout_id

    async def return_book(self: LibraryManager, book_id: str, user_id: str) -> bool:
        """Return a book from a user.

        Args:
        ----
            book_id: Book ID.
            user_id: User ID.

        Returns:
        -------
            True if successful, False otherwise.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        checkouts = await self.data_service.find_many(
            self.checkouts_collection,
            {"book_id": book_id, "user_id": user_id, "return_date": None},
            policy=CachePolicy.DB_ONLY,
        )

        if not checkouts:
            raise ValueError(f"No active checkout found for book: {book_id}")

        checkout = checkouts[0]
        checkout_id = checkout.get("id")
        now = datetime.now(timezone.utc)

        await self.data_service.set(
            self.checkouts_collection,
            {"id": checkout_id},
            {"return_date": now},
            policy=CachePolicy.DB_ONLY,
        )

        await self.data_service.set(
            self.books_collection,
            {"id": book_id},
            {"available": True, "updated_at": now},
            policy=CachePolicy.DB_ONLY,
        )

        if self.logger:
            self.logger.info(
                f"Returned book: {book_id} from user: {user_id}",
                extra={
                    "book_id": book_id,
                    "user_id": user_id,
                    "checkout_id": checkout_id,
                },
            )

        return True

    async def get_user_borrowed_books(
        self: LibraryManager, user_id: str
    ) -> list[dict[str, Any]]:
        """Get all books borrowed by a user.

        Args:
        ----
            user_id: User ID.

        Returns:
        -------
            List of book dictionaries with checkout information.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        checkouts = await self.data_service.find_many(
            self.checkouts_collection,
            {"user_id": user_id, "return_date": None},
            policy=CachePolicy.DB_ONLY,
        )

        borrowed_books = []
        for checkout in checkouts:
            book_id = checkout.get("book_id")
            book = await self.get_book(book_id)
            if book:
                book["checkout_id"] = checkout.get("id")
                book["checkout_date"] = checkout.get("checkout_date")
                borrowed_books.append(book)

        if self.logger:
            self.logger.debug(
                f"Retrieved {len(borrowed_books)} borrowed books for user: {user_id}",
                extra={"user_id": user_id, "book_count": len(borrowed_books)},
            )

        return borrowed_books

    async def search_books(self: LibraryManager, query: str) -> list[dict[str, Any]]:
        """Search books by title or author.

        Args:
        ----
            query: Search query string.

        Returns:
        -------
            List of matching book dictionaries.

        """
        if not self.data_service:
            raise ValueError("DataService not available")

        all_books = await self.list_books()
        query_lower = query.lower()

        matching_books = [
            book
            for book in all_books
            if query_lower in book.get("title", "").lower()
            or query_lower in book.get("author", "").lower()
        ]

        if self.logger:
            self.logger.debug(
                f"Search for '{query}' found {len(matching_books)} books",
                extra={"query": query, "result_count": len(matching_books)},
            )

        return matching_books
