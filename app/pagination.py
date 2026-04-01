from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):
    page_size = 10  # tamanho padrão da página
    page_size_query_param = 'page_size'  # permitir mudar via query parameter
    max_page_size = 100  # tamanho máximo da página que pode ser solicitado

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'total_pages': self.page.paginator.num_pages,
            'results': data,
        })
