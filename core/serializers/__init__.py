from django.conf.locale import fr

from .produto import ProdutoSerializer
from .categoria import CategoriaSerializer
from .buscaImagem import BuscaImagemSerializer  
from .imagemProduto import ImagemProdutoSerializer
from .favorito import FavoritoSerializer
from .pedido import PedidoSerializer   
from .itemPedido import ItemPedidoSerializer   
from .venda import VendaSerializer
from .seguidor import SeguidorSerializer
from .historicoPesquisa import HistoricoPesquisaSerializer
from .notificacao import NotificacaoSerializer
from .sessaoLogin import SessaoLoginSerializer
from .user import UserRegistrationSerializer, UserSerializer