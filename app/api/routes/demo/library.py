"""Library management demo routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.middleware.serialization import JSONEncoder
from app.core.class_store import get_class_store
from app.utils.demo_context import get_demo_user_context

library_router = APIRouter(prefix="/demo/library", tags=["Library Demo"])


@library_router.get("/", response_class=HTMLResponse)
async def library_page(request: Request) -> HTMLResponse:
    """Library management page.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        HTML response with library page

    """
    user = await get_demo_user_context(request)
    return request.app.state.templates.TemplateResponse(
        "demo/library/library.html",
        {"request": request, "title": "Library Management", "user": user},
    )


@library_router.get("/books", response_class=JSONResponse)
async def list_books_api(request: Request) -> JSONResponse:
    """List all books API endpoint.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        JSON response with list of books

    """
    try:
        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        books = await library_manager.list_books()
        # Serialize datetime objects before creating JSONResponse
        serialized_books = JSONEncoder.serialize(books)
        return JSONResponse(content={"books": serialized_books})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list books: {str(e)}",
        ) from e


@library_router.post("/books", response_class=JSONResponse)
async def add_book_api(request: Request) -> JSONResponse:
    """Add new book API endpoint.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        JSON response with created book ID

    """
    try:
        user = await get_demo_user_context(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        body = await request.json()
        book_data = {
            "title": body.get("title", ""),
            "author": body.get("author", ""),
            "isbn": body.get("isbn", ""),
        }

        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        book_id = await library_manager.add_book(book_data)

        return JSONResponse(content={"book_id": book_id, "message": "Book added"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add book: {str(e)}",
        ) from e


@library_router.get("/books/{book_id}", response_class=JSONResponse)
async def get_book_api(book_id: str, request: Request) -> JSONResponse:
    """Get book details API endpoint.

    Args:
    ----
        book_id: Book ID
        request: FastAPI request object

    Returns:
    -------
        JSON response with book details

    """
    try:
        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        book = await library_manager.get_book(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )

        # Serialize datetime objects before creating JSONResponse
        serialized_book = JSONEncoder.serialize(book)
        return JSONResponse(content={"book": serialized_book})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get book: {str(e)}",
        ) from e


@library_router.post("/books/{book_id}/checkout", response_class=JSONResponse)
async def checkout_book_api(book_id: str, request: Request) -> JSONResponse:
    """Check out book API endpoint.

    Args:
    ----
        book_id: Book ID
        request: FastAPI request object

    Returns:
    -------
        JSON response with checkout result

    """
    try:
        user = await get_demo_user_context(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_id = user.get("id")
        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        checkout_id = await library_manager.checkout_book(book_id, user_id)

        return JSONResponse(
            content={"checkout_id": checkout_id, "message": "Book checked out"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to checkout book: {str(e)}",
        ) from e


@library_router.post("/books/{book_id}/return", response_class=JSONResponse)
async def return_book_api(book_id: str, request: Request) -> JSONResponse:
    """Return book API endpoint.

    Args:
    ----
        book_id: Book ID
        request: FastAPI request object

    Returns:
    -------
        JSON response with return result

    """
    try:
        user = await get_demo_user_context(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user_id = user.get("id")
        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        await library_manager.return_book(book_id, user_id)

        return JSONResponse(content={"message": "Book returned"})
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to return book: {str(e)}",
        ) from e


@library_router.get("/users/{user_id}/books", response_class=JSONResponse)
async def get_user_books_api(user_id: str, request: Request) -> JSONResponse:
    """Get user's borrowed books API endpoint.

    Args:
    ----
        user_id: User ID
        request: FastAPI request object

    Returns:
    -------
        JSON response with user's borrowed books

    """
    try:
        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        books = await library_manager.get_user_borrowed_books(user_id)

        # Serialize datetime objects before creating JSONResponse
        serialized_books = JSONEncoder.serialize(books)
        return JSONResponse(content={"books": serialized_books})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user books: {str(e)}",
        ) from e


@library_router.get("/search", response_class=JSONResponse)
async def search_books_api(request: Request) -> JSONResponse:
    """Search books API endpoint.

    Args:
    ----
        request: FastAPI request object

    Returns:
    -------
        JSON response with search results

    """
    try:
        query = request.query_params.get("q", "")
        if not query:
            return JSONResponse(content={"books": []})

        class_store = get_class_store()
        library_manager = class_store.get("library_manager")
        books = await library_manager.search_books(query)

        # Serialize datetime objects before creating JSONResponse
        serialized_books = JSONEncoder.serialize(books)
        return JSONResponse(content={"books": serialized_books})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search books: {str(e)}",
        ) from e
