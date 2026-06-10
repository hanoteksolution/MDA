from math import ceil

from django.db.models import F, Q, Sum
from rest_framework.response import Response

from core.responses.api_response import success_response


def paginate_queryset(request, queryset, serializer_fn):
    page = max(int(request.query_params.get("page", 1)), 1)
    page_size = min(int(request.query_params.get("page_size", 20)), 100)
    total = queryset.count()
    total_pages = max(ceil(total / page_size), 1) if total else 1
    offset = (page - 1) * page_size
    items = queryset[offset : offset + page_size]
    return success_response(
        data={
            "results": serializer_fn(items),
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    )


def apply_search(queryset, search, *fields):
    if not search:
        return queryset
    q = Q()
    for field in fields:
        q |= Q(**{f"{field}__icontains": search})
    return queryset.filter(q)
