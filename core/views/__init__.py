from django.conf.locale import fr

from .user import UserRegistrationView, UserViewSet, UserEmailCheckView
from .produto import ProdutoViewSet
from .categoria import CategoriaViewSet
from .buscaImagem import BuscaImagemViewSet 
from .imagemProduto import ImagemProdutoViewSet 
from .favorito import FavoritoViewSet 
from .pedido import PedidoViewSet
from .itemPedido import ItemPedidoViewSet
from .venda import VendaViewSet
from .seguidor import SeguidorViewSet
from .historicoPesquisa import HistoricoPesquisaViewSet
from .notificacao import NotificacaoViewSet
from .scanner import ScannerViewSet
from .carrinho import CarrinhoView
