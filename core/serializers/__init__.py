from django.conf.locale import fr

from .categoria import CategoriaSerializer
from .buscaImagem import BuscaImagemSerializer  
from .imagemProduto import ImagemProdutoSerializer
from .favorito import FavoritoSerializer
from .pedido import PedidoCreateUpdateSerializer, PedidoListSerializer
from .itemPedido import ItemPedidoCreateUpdateSerializer, ItemPedidoListSerializer   
from .venda import VendaSerializer
from .seguidor import SeguidorSerializer
from .historicoPesquisa import HistoricoPesquisaSerializer
from .notificacao import NotificacaoSerializer
from .sessaoLogin import SessaoLoginSerializer
from .user import UserRegistrationSerializer, UserSerializer
from .reviews import ReviewSerializer, ReviewImageSerializer
from .produto import ProdutoSerializer
from .compra import CompraSerializer, ItemCompraSerializer