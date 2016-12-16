# -*- coding: utf-8 -*-

from multiprocessing import Process, Queue
import cookielib
import htmlentitydefs
import mechanize
import random
import re
import socket
import time
import urllib2

''' Variáveis globais '''

socket.setdefaulttimeout(45)

#cria um navegador, um browser de código.
browser = mechanize.Browser()
# Ajusta algumas opções do navegador.
browser.set_handle_equiv(True)
browser.set_handle_gzip(False)
browser.set_handle_redirect(True)
browser.set_handle_referer(True)
browser.set_handle_robots(False)

cj = cookielib.LWPCookieJar()
browser.set_cookiejar(cj)

browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
# Configura o user-agent, para o servidor, o navegador é Firefox.
browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11;\ U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615\Fedora/3.0.1-1.fc9 Firefox/8')]

'''-----------------> A ORDEM das expressões regulares DEVE ser mantida! <-----------------'''
regularExpression = [{'er':'<div\s*style\=\"text\-align\:\s*justify\;\">','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'<!--.*?-->','sub':'', 'param':re.IGNORECASE + re.DOTALL},
#                     {'er':'<a.*?>[A]</a>','sub':'', 'param':re.IGNORECASE},
#                     {'er':'<STRONG></*A.*?></*STRONG>','sub':'', 'param':re.IGNORECASE},
                     {'er':'<script.*?</script>','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'<div.*?(id=\"mancheteTopo\").*?>.*?(</div>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<div.*?>)','sub':'<div>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<div>(\s)*<h[0-9]+>Tags</h[0-9]+>(\s)*.*)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(</p>(\s)*<p>(\s)*<strong>(\s)*Leia(\s)*tamb.+?m\:<a.*?>(\s)*<br(\s)*/>.*?</a>(\s)*</strong>(\s)*</p>(\s)*)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<span.*?>)','sub':'<span>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<img .*?>)','sub':'<img/>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<span>(\s)*<img/>(\s)*<a.*?>(\s)*<img/>.*?</a>(\s)*<br(\s)*/>(\s)*</span>(\s)*)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<link.*?>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},

                     {'er':'(<li.*?>)','sub':'<li>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<p .*?>)','sub':'<p>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'</li>(\s)*</ul>','sub':'</li></ul>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<div>(\s)*<img/>(\s)*</div>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<object .*?</object>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<input .*?>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<param .*?>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<embed .*?>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<div>(\s)*</div>(\s)*<br />(\s)*<div>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<ul .*?>)','sub':'<ul>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<td.*?>)','sub':'<td>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<hr .*?>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'</a>(\s)*<ul><li>','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'</li></ul></div>','sub':'</ul>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'<ul>.*?(</ul>)|(</li>(\s)*</ul>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'<div>(\s)*<span>(\s)*<b>.*?(</b>).*?(</span>)(\s)*<br>.*?(</div>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<li>(([0-9][0-9].*?)|(\s)*)<a>.*?</a>(\s)*</li>(\s)*)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<ul>.*?<li>.*?<span.*?</span>(\s)*</li>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<li>(\s)*<p>.*?</p>(\s)*</li>)','sub':'', 'param':re.IGNORECASE},
                     {'er':'(<li>(\s)*(<p.*?</p>)*<span>.*?(</span>)(\s)*(<span.*?(</span>))*(\s)*(<p>)*(\s)*<a.*?</a>(\s)*(</p>)*(\s)*</li>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     
                     {'er':'</a></p><p>.*?</p><p.*?>.*?</p><p><a.*?>.*','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     #As expressões abaixo foram removidas em carater de teste. Podem ser necessárias para alguns tipos de páginas.
#                     {'er':'<td.*?>(\s)*<a.*?>.*?</a>(\s)*</td>','sub':'', 'param':re.IGNORECASE + re.DOTALL},
#                     {'er':'<div>(\s)*<a.*?><img.*?></a>','sub':'<p>', 'param':re.IGNORECASE + re.DOTALL},
#                     {'er':'(<div>(\s)*<a.*?</a>(\s)*</div>)+','sub':'<p>', 'param':re.IGNORECASE},
#                     {'er':'<li>(\s)*(<ul>)*(\s)*<li>(\s)*<div>.*?</li>(\s)*</ul>(\s)*</li>','sub':'', 'param':re.IGNORECASE + re.DOTALL},

                     {'er':'<div>(\s)*<ul>(\s)*<li>(\s)*<img.*?</li>.*?</ul>.*?<div.*?</div>.*?</p>.*?</div>','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'<li>(\s)*<p>(\s)*<a.*?><img.*?/></a>(\s)*</p>(\s)*<p>(.|(\n))*?</li>','sub':'', 'param':re.IGNORECASE},
                     {'er':'(<div>(\s)*<p>(\s)*<a.*?</a>(\s)*</p>(\s)*<span>(\s)*\d\d\:.*?</span>(\s)*</div>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<img.*?>(\s)*<a.*?</a>(\s)*</font>(\s)*<table(.|(\n))*?</tr>(\s)*</table>)','sub':'', 'param':re.IGNORECASE},
#                     {'er':'(<table.*?>(\s)*<tr>(\s)*<td.*?[<a.*?</a>](\s)*</td>(\s)*</tr>.*?</table>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},#Versão que estava antes da de baixo
                     {'er':'(<table.*?>(\s)*<tr>(\s)*<td.*?!(<p>)[<a.*?</a>](\s)*</td>(\s)*</tr>.*?</table>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'<span>[0-9][0-9]\:[0-9][0-9] \- </span><span>.*?</span></a>','sub':'', 'param':re.IGNORECASE},
                     {'er':'(<dt.*?</dt>)','sub':'', 'param':re.IGNORECASE},#(<span>(\s)*<strong.*?</strong>(\s)*<a(.|(\n))*?</a>(\s)*</span>)|
                     {'er':'(<tr>(\s)*<td>(\s)*<span>.*?</td>(\s)*</tr>)(!~)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<ul>(\s)*<li>)(\s)*(<a.*?(<span.*?</span>)(\s)*</a>)(\s)*(<a.*?</a>)(\s)*(<span.*?</span>)(\s)*(</li>(\s)*</ul>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'((<ul>)(\s)*(<li>)!<.*?</ul>)|((<li>)!<.*?((<a.*?(</a>))|(</li>)))','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<abbr.*?</abbr>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'((<div>)|(</div>))*((<br />)|(<p>))((</div>)|(<div>))*','sub':'<p>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<div>)+','sub':'<div>', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<span(.*?)>)','sub':'<span>', 'param':re.IGNORECASE},
                     {'er':'(<span>)+|(<span>(\s)*<span>)','sub':'<span>', 'param':re.IGNORECASE},
                     {'er':'(</span>)+|(</span>(\s)*</span>)','sub':'</span>', 'param':re.IGNORECASE},
                     {'er':'(</span>(<br />|<p>|(\s)*)<span>)|(<div>(\s)*<p>)|(</p>(\s)*<p>)|(</div>(\s)*<div>(\s)*</div>(\s)*<div>)|(<div>(\s)*</div>)|(<div>(\&nbsp\;)</div>(\s)*<div>)','sub':'<p>', 'param':re.IGNORECASE},
                     {'er':'(<p>)+|(<P>)+|(<i>)+','sub':'<p>', 'param':re.IGNORECASE},
                     {'er':'((</P>)+|(</i>)+)','sub':'</p>', 'param':re.IGNORECASE},
                     {'er':'(<p(.*?)>)|(<[/]*B>)|(</p>(\s)*<p>)|(<p>(\s)*</p>)|(<br/>)','sub':'<p>', 'param':re.IGNORECASE},
                     {'er':'<p><span.*?><a.*?><img.*?></a>(\s)*</span>(\s)*<strong>.*?</strong>.*?</p>','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<ol.*?</ol>)|(<dd.*?</dd>)|((<a.*?>)|(</div>(\s)*<div>)+)|(<option.*?</option>)|(<link(.*?)(</link)*>)|(<g\:plusone.*?</g\:plusone>)|(<marquee.*?(</marquee)*>)|(<!--caderno-->.*)|(<!--(\s)*RSS(\s)*-->.*?(<!--(.*?)-->))|(<!--.*?-->)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<xml.*?</xml>)|(<cite(.*?)</cite>)|(<fieldset.*?</fieldset>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<form[>]*.*?(</form)*>)|(<meta(.*?)(</meta)*>)|(<label[>]*.*?(</label)*>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'((<span>Tags:</span>).*)|(<div>((\s)*)</div>)|(<b[>]*.*?</b><br />)','sub':'<p>', 'param':re.IGNORECASE},
                     {'er':'(</div>((\s)*)<div>)|(<style[>]*(.*?)</style>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<img(.*?)>)|(<fb:like[>]*(.*?)</fb:like>)|(<textarea[>]*(.*?)</textarea>)|(<noscript[>]*(.*?)</noscript>)|(<object[>]*(.*?)</object>)|(<iframe[>]*(.*?)</iframe>)|(<address[>]*(.*?)</address>)','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'((<div>)+)|(<div>((\s)*<div>)*)|((<div>(\n)*)+)','sub':'<div>', 'param':re.IGNORECASE},
                     {'er':'(<br>)+|(((</p>)|<br />)(\s)*<div>)','sub':'<br />', 'param':re.IGNORECASE},
                     {'er':'((<br />)+)|(<br />(\s)*<br />)','sub':'<br />', 'param':re.IGNORECASE},
                     {'er':'((</p>)|(<br />))(\s)*(<div(.*?)(</div)*>)','sub':'<br />', 'param':re.IGNORECASE},
                     {'er':'(</p>(\s)*<div>)','sub':'</p>', 'param':re.IGNORECASE},
                     {'er':'(</a>)+','sub':'\n', 'param':re.IGNORECASE},
                     {'er':'(<p>.*?<FONT.*?</FONT>(\s)*</p>)~','sub':'', 'param':re.IGNORECASE + re.DOTALL},
                     {'er':'(<div>(\s)*</a>)|(<div>(\s)*<span>)|(</span>(<br />)*(\s)*</div>)','sub':'', 'param':re.IGNORECASE},
                     {'er':'(\n( )*)+','sub':'\n', 'param':re.IGNORECASE},
                     {'er':'(</span><span>)','sub':'<p>', 'param':re.IGNORECASE},
                     ]
        
def er(er = {}, temp_html = '', return_func = ''):
    '''
        Aplica uma expressão regular a um texto e atribui o resultado a uma variável por referência.
        @param er: Expressão regular.
        @param temp_html: Texto a ser aplicada à expressão regular.
        @param return_func: Variável que armazena o resultado da expressão regular.
    '''
    
    ER = re.compile(er['er'], re.IGNORECASE + re.DOTALL)
    return_func.put(ER.sub(er['sub'], temp_html))
        
def terminate(p = None, tempoEspera = 10):
    '''
        Verifica se um processo ainda está vivo e espera um tempo para que o mesmo seja terminado.
        Usado para expressões regulares que, possivelmente, entraram em ciclo.
        @param p: Processo a ser verificado.
        @param tempoEspera: Timeout para que o processo seja terminado. 
    '''
    
    if p.is_alive():
        time.sleep(tempoEspera)
    p.terminate()
    p.join()
            

def get_html(url, file_html = None):
    '''
        Faz o download do HTML referente a uma URL.
        
        @url: URL a ser extraido o HTML
        @file_html: Arquivo em que deve ser gravado o HTML proveniente da URL passada.
                    Caso seja nulo, o arquivo não é gravado.
        @return: O HTML referente à URL informada como parâmetro.
    '''
    
    try:
        link_expandido = mechanize.urlopen(url, timeout=45.0).geturl()#Expande a url antes de ser tratada e, caso seja uma propaganda, a url da notícia é retornado
        browser.open(link_expandido, timeout=45.0)# Acesso à url
        html = browser.response().read().replace('\r', '\n').replace('DIV', 'div') #Padroniza as quebras de linha e divs
    except:
        try:
            #Caso ocorra algum erro com o Mechanize
            html = urllib2.urlopen(url).read()
        except:
            browser.close()
            return 'TIMEOUT'#Página não pode ser carregada - Espera-se que esta parte não seja executada!
    
    
    #Salva o HTML em um arquivo especificado como parâmetro
    if file_html != None:
        arq = open(file_html, "w")
        print >> arq, html
        arq.close()
        
    browser.close()
    
    return html
    
def extraiTexto(url = '', extrairTitulo = False, file_html = None):
    '''
        Método principal de extração do título e texto de uma notícia em uma página HTML.
        
        @url: URL do HTML a ser investigado.
        @extrairTitulo: Boolean para extração ou não do título da notícia, default:False.
        @file_html: Arquivo que deve ser gravado o HTML referente à url.
                    Caso seja uma string vazia, o arquivo não será gravado, mas as informações serão extraídas normalmente.
        @return: {'text':'', 'title':''} - Dicionário com título e texto da notícia.
    '''
    
    opcoes = [] #Armazena todas as opções de texto da notícia
    url = url.replace(' ', '%20') #Substitui os espaços em branco existentes nos links
    textoNoticia = ''
    tituloNoticia = ''
    
    html = get_html(url, file_html)#Coleta o HTML da página para processamento e/ou gravar em arquivo
    if html == 'TIMEOUT':
        return {'text': 'TIMEOUT', 'title': 'TIMEOUT'}#Página não pode ser carregada - Espera-se que esta parte não seja executada!
    
    if extrairTitulo == True: #Obtém o título da notícia
        title = ''
        try:
            ER_title = re.compile('(<title(.*?)>(.|(\n))*?</title>)', re.U)
            ER = re.compile('(<.*?>)',re.IGNORECASE)
            ER1 = re.compile('^(\s)*|(\s)*$',re.IGNORECASE)
            tituloNoticia = ER1.sub('', ER.sub('', ER_title.search(html).group().replace('\n', ' ').replace('&quot;','"')))
            
            try:
                title = unicode(tituloNoticia,'utf-8')
            except:
                title = unicode(tituloNoticia,'iso-8859-1')
        except:
            tituloNoticia = ''
            
        tituloNoticia = _limpaTexto(_unescape(title))
    
    '''
        Início da extração do texto principal da página HTML
        Remove blocos indesejáveis
    '''
    
    html = html.replace('<IMG','<img').replace('</SPAN>','</span>').replace('<BR />','<br />').replace('<BR/>','<br/>')
    for regex in regularExpression:
        return_func = Queue()
        process = Process(target=er, args=(regex,html,return_func,))
        process.start()
        html = return_func.get()
        time.sleep(random.uniform(0.1, 1.0))#Espera para terminar
        if process.is_alive():
            terminate(process, 10)#timeout para a execução da expressão regular
            
    divs = html.split('<div>')#Divide a página HTML pelas DIVs
    bloco = ''
    
    for div in divs: #Laço que adiciona à lista de opcoes somente as divs com conjuntos de caracteres que podem ser o texto da notícia
        try:
            bloco = unicode(div,'utf-8')
        except:
            try:
                bloco = unicode(div,'iso8859-1')
            except:
                bloco = unicode(div,'iso8859-15')
        bloco = _limpaTexto(_unescape(bloco))
        opcoes.append(bloco)
                
    maiorTamanho = 0 #Tamanho do maior texto
    indice = 0 #posição da lista que contém o texto de maior tamanho
    i = 0 #Iterador
    
    for texto in opcoes:
        tamanho = len(texto)
        if tamanho > maiorTamanho:
            maiorTamanho = tamanho
            indice = i
        i += 1
    
    
    if len(opcoes) > 0:
        ER = re.compile('(<).*[>]*',re.IGNORECASE) #Retira o restante das tags html
        linhasTexto = ER.sub('', opcoes[indice]).split('\n') #Quebra utilizada para formatar as linhas
        
        ER = re.compile('(^(\s)*)',re.IGNORECASE)
        ER1 = re.compile('((width=)|(height=)|(scrolling=)|(marginheight=)).*',re.IGNORECASE)
        
        for linha in linhasTexto:
            linha = ER1.sub('', linha)
            if len(linha) > 5: #Elimina linhas desnecessárias
                textoNoticia += ER.sub('', linha) + "\n"
    
    return {'text': unicode(textoNoticia), 'title': unicode(tituloNoticia)}

def _limpaTexto(texto): 
    '''    
        Tenta remover os lixos e preserva o texto da notícia.
        
        @texto: Possível texto da notícia a ser tratado.
        @return: Texto da notícia.
    '''
    
    ER = re.compile('(>por(\s)*)',re.IGNORECASE)
    texto = ER.sub('>', texto)
    
    try:        
        texto = eval(repr(texto).replace('\\u201c','\"').replace('\\u201d','\"').replace('\\x91','\"').replace('\\x96', '-').replace('\\x97', '-').replace('\\x80','-').replace('\\x07','').replace('\\x92','\"').replace('\\x93','\"').replace('\\x94','\"').replace('\\x13','').replace('\\x14','').replace('\\x15','').replace('\\xa0','').replace('\\xab','').replace('\\xbb','').replace('\uf0f0','').replace('\\u2022','').replace('\\u0013','').replace('\\u0014','').replace('\\u2013','-').replace('\\x0b','').replace('\\x12','').replace('\\x0b','').replace('\\x0c','').replace('\xc2','').replace('\xba','').replace('\\r',' ').replace('\\t',' ').replace('\\n',' '))
    except:
        texto = eval(str(repr(texto)).replace('\\x91','').replace('\\x96', '').replace('\\x97', '-').replace('\\x80','').replace('\\x07','').replace('\\x92','').replace('\\x93','').replace('\\x94','').replace('\\x13','').replace('\\x14','').replace('\\x15','').replace('\\xa0','').replace('\\xab','').replace('\\xbb','').replace('\uf0f0','').replace('\\u2022','').replace('\\u0013','').replace('\\u0014','').replace('\\u2013','-').replace('\\r',' ').replace('\\t',' ').replace('\\n',' '))    
    
    texto = texto.replace('</p>', '<p>').replace('<br />', '<p>').replace('<br/>', '<p>')
    ER = re.compile('(<p>)+',re.IGNORECASE)
    texto = ER.sub('<p>', texto)    
    
    texto = texto.replace('There are no translations available.', '').replace('Assine a Folha', '').replace(' \* ',' ').replace('Continue lendo', '').replace('comissao', '').replace('saiba mais', '').replace('imprimir', '')
    texto = texto.replace(' X www.gerdau.com.br', '').replace('TOTAL DE', '').replace('Comente', '').replace('Publicidade', '').replace('PUBLICIDADE', '').replace('Leia mais:', '').replace('Enviar Imprimir', '')
    texto = texto.replace('Imprimir', '').replace('E-mail', '').replace('Postado por', '').replace('compartilhar:', '').replace('Textos relacionados:', '').replace('No comments', '').replace('Veja a lista completa','')
    texto = texto.replace('Leia Mais', '').replace('Tamanho do texto','').replace('tamanho do texto','').replace('Tamanho da fonte','').replace('A+ a-', '').replace('Saiba mais','').replace('Todos os direitos reservados','')
    texto = texto.replace('Informacoes sobre o album', '').replace('Tamanho da letra','').replace('Compartilhe','').replace('Comunicar erro','').replace('Comece a twitar por SMS de onde estiver!','').replace('Siga o Yahoo!','')
    texto = texto.replace('e no Facebook', '').replace('Ampliar imagem','').replace('Gostou?','').replace('Autor:','').replace('// + veja todas as galerias','').replace('CLIQUE AQUI E VEJA MAIS FOTOS!','').replace('&quot;','"')
    texto = texto.replace('Pior Melhor', '').replace('ir para o topo','').replace('Adicionar como favoritos','').replace('Fotos\n','').replace('Links de parceiros:', '').replace('para comentar.', '').replace('comente', '').replace('veja todas', '').replace('| Sair', '').replace('Mais Acessadas','')
    texto = texto.replace('Compartilhar', '').replace('por e-mail', '').replace('Tamanho da Letra:', '').replace('Normal', '').replace('Grande', '').replace('Ampliar Imagem', '').replace('Ampliar Imagem', '').replace('ATIVIDADES DE AMIGOS','')
    texto = texto.replace('anter.', '').replace('View Comments','').replace('Tamanho da Letra','').replace('[-]Texto[+]','').replace('Fazer login','').replace('com Abril ID','').replace('clique aqui','').replace('enviar Texto:','').replace('A+','').replace('A-','').replace('- Buscar -','').replace('- Atualizado em','').replace('maior| menor','').replace('Buscar na Web','').replace('o estado mirante am mirante fm','').replace('BlogThis\! no Twitter no Facebook no Orkut','')
    texto = texto.replace('<p>', '\n').replace('Enviar\n','').replace('enviar mensagem','').replace('Foto:','').replace('a a a','').replace('Anuncie aqui','')
    
    ER = re.compile('(<h[0-9].*?</h[0-9]>)',re.IGNORECASE)
    texto = ER.sub('', texto)
    ER = re.compile('(<(.*?)>)',re.IGNORECASE)
    texto = ER.sub(' ', texto)
    ER = re.compile('( )+',re.IGNORECASE)
    texto = ER.sub(' ', texto)
    
    #Substituição feita para que não atrapalhe o treinamento do NER (parte desenvolvida pelo Vinícius)
    ER = re.compile('\[',re.IGNORECASE)
    texto = ER.sub('(', texto)
    ER = re.compile('\]',re.IGNORECASE)
    texto = ER.sub(')', texto)

    ER = re.compile('((\s)+\.+ )',re.IGNORECASE + re.DOTALL)
    texto = ER.sub('. ', texto)
    
    ER = re.compile('', re.IGNORECASE + re.DOTALL)
    texto = ER.sub('', texto)
    
    ER = re.compile('((\s)*\)\)>(\s)*http\:.*)|(SE..ES(\s)*ARQUIVO(\s)*TAMANHO(\s)*DO(\s)*TEXTO(\s)*)|(Confira(\s)*.(\s)*t.picos(\s)*relacionados)|(Envie(\s)*por(\s)*mail(\s)*Partilhe.*?mail(\s)*share(\s)*Estatisticas\:(\s)*)|(\.CONTATO(\s)*\(1\).*)|((\s)*voltar(\s)*?$)|(consulte\s*tamb.m\s*os\s*atrasos\s*de\s*outros.*)',re.IGNORECASE + re.DOTALL)
    texto = ER.sub('', texto)
    
    ER = re.compile('(DESTAQUES DA HOME.*)|(\+(\s)*CANAIS.*)|(\+(\s)*ESPORTES.*)|(\+(\s)*Lidas .*?ndice.*)|(\+(\s)*Comentadas.*)|(\+(\s)*Enviadas .*?ndice.*)|(Comentar esta reportagem.*)|(esta p.*?gina)|(Mais lidos do m.s)|(Mais comentados da semana)|(Categorizado em\: \|)|(Tags \| isy)|(Tags \|)|(Arquivado em \:.*?Responder(\s)*$)|(TERMO DE AUTORIZA.*?DO USO E DE PUBLICA.*?TEXTOS E IMAGENS.*)|(Digite as palavras ao lado para enviar sua mat.ria)|(Seu voto foi efetuado com sucesso)|(atualizar imagem)|(Maior(\s)*\|(\s)*Menor.*?delicious.*?MySpace(\s)*Google(\s)*digg)|((\s)*nenhum.*?este(\s)*post(\s)*seja(\s)*o(\s)*primeiro(\s)*a(\s)*)|(Votos\:(\s)+)|(P.gina(\s)*[0-9]+(\s)*de.*)|((\s)*\S+Leia mais(\s)*)|((\s)*ler mais)|(O que voc. encontra neste blog.*)|(Not.cias(\s)*Relacionadas.*)|(S.ries(\s)*S.ries(\s)*Jornalismo(\s)*Jornalismo(\s)*Variedades(\s)*Variedades(\s)*Esportes(\s)*Esportes.*?Sucessos(\s)*)|(Leia(\s)*mais(\s)*)|(Clique(\s)*De volta ao topo(\s)*$)|(Voc. precisa estar logado para.*?clique em registrar.*?Envie sua sugest.*)|((\s)+Fechar(\s)+)',re.IGNORECASE + re.DOTALL)
    texto = ER.sub('', texto)
    ER = re.compile('(\+(\s)*Not.*?cia.*)|(\+(\s)*Blog.*)|(Visite a p.*gin.*com no Facebook)|(Tweet(\s)*)|(\(\- \) Texto \(\+ \))|(Avalia..o\:(\s)*([0-9]+(\.)*[0-9]*(\s)*of(\s)*[0-9]+(\.)*[0-9]*(\s)*(\.)*))|(Fotos\:(\s)*Divulga..o)|(Voc.(\s)*est.(\s)*em\:.*?Link(\s)*>.*)|(BUSCA(\s)*NO(\s)*BLOG)',re.IGNORECASE)
    texto = ER.sub(' ', texto)
    
    ER = re.compile('(Usu.rio cadastrado\:)|(M.dio :)|(veja tamb.m)|(Permalink\:)|(Autor(\s)*\:)|(Nome\:)|(Fonte(\s)*\:)|(Esqueci minha senha)|(Ainda n.o sou cadastrado)|(N.o avaliado ainda\.)|(Seja o primeiro quem avaliou este item\!)|(Clique na barra de avalia..o para avaliar este item\.)|(Voc. Comentarista.*)|(Esta mat.*?ria tem:.*)|(> TAGS\:.*)|(OUTRAS NOT.*?CIAS.*)|(Sess.es\:.*)|(Previs.*?o do Tempo)|(escrever coment.*?rio)|(Coment.*?rios para esta not.*?cia.)|(Não perca tempo e seja o primeiro a comentar esta notícia\.)|(M.ximo.*?caracteres)|(Para.*?das(\s)*mat.rias(\s)*publicadas.*?A(\s)*TARDE(\s)*preencha.*?abaixo(\s)*e(\s)*clique(\s)*em)|([0-9]+(\s)visualiza..es)|(mostrar(\s)*informa..es)|((\s)*\.*(\s)*\"*J.(\s)*curtiu(\s)*o(\s)*Di.rio(\s)*do(\s)*ABC.*?Facebook.*)|((\s)*Enviar para um amigo(\s)*)|(essa not.cia Twitter E\-Mail Orkut Facebook essa not.cia\:)|(\s)*(Para(\s)*not.cias(\s)*do(\s)*Na(\s)*Mira.*)|(Posted(\s)*in(\s)*Dia(\s)*e(\s)*Noite.*?TrackBack.*)|(\s*Diminuir\s*fonte\s*Aumentar\s*fonte\s*)|(anterior\s*pr.xima\s*anterior\s*pr.xima)|(Anterior\s*1\s*2.*?Pr.xima.*)',re.IGNORECASE + re.DOTALL)
    texto = ER.sub('', texto)
    
    ER = re.compile('(Seu coment.*?rio foi enviado e aguarda aprova.*)|(\|(\s)*Fale conosco.*)|(value\=\".*)|(Reda..o O POVO Online.*)|(Links .*?teis aos usu.*?rios.*)|(\>\>Acesse o site de Cota..o do RuralBR.*)|(Foto\:.*?\/ Agencia RBS)|(Curta o Administradores no Facebook.*?siga os nossos posts no .*)|(Siga.*?Twitter.*)|(Assine a newsletter semanal.*)|(Acompanhe as not.*?cias de.*?Twitter.*)|(Leia.*)~|(Leia tamb.m\:.*)|(\[.*?\])|(Se voc. encontrou algum erro nesta not.cia, por favor preencha o formul.rio abaixo e clique em enviar\. Este formul.rio destina-se somente . comunica..o de erros\.)|(Avalia.*?o\:(\s)*[0-9]\.[0-9](\s)*of(\s)*[0-9]\.(\s)*\.)|(Descubra o Yahoo.*?Explore not.cias. v.deos e muito mais com base naquilo.*?Publique sua pr.pria.*?primeiro Entrar no Facebook)((\s)*Corrigir(\s)*Email\:(\s)*Mensagem>)|((\s)*(\-)*(\s)*Links(\s)*patrocinados(\s)*)|(Leia mais essa not.cia esta.*?Esqueceu a senha.*)|(Feed(\s)*para.*?post.*?TrackBack.*)|(InfoMoney\s*preza\s*a\s*qualidade\s*da\s*informa.*)|(Homebroker\s*InfoMoney\s*novo\!.*)',re.IGNORECASE + re.DOTALL)
    texto = ER.sub('', texto)
    
    ER = re.compile('(Descubra not.cias, v.deos e muito mais.*)|(imprima esta not.*?cia)|(Senha\:(\s)*Not.cias(\s)*voltar(\s)*compartilhe)|(Clique para ver todas as p.ginas desta edi..o\.)|(\|envie para um amigo)|(\| topo da p.*?gina)|(D.*?vidas Frequentes)|(Grupo RBS)|(Follow \@.*)|((\(\d\))* Envie seu coment.*?rio)||(1(\s)*2.*?Pr.xima.*)',re.IGNORECASE)
    texto = ER.sub('', texto)
    ER = re.compile('(Vers.*?o para impress.*?o)|(proximo anterior)|(Mat.ria)~|(Comentar(\s)*(\:)*)|(Not.cias no Twitter)|(Mais not.cias no(\s)*Twitter(\s)*da(\s)*Abelhinha)|((\s)*\*(\s)*)|(t.picos(\:)*(\s)*)|(.ltimas Not.cias)|(Com informa.*?es do Link(\.)*)',re.IGNORECASE)
    texto = ER.sub('', texto)
    ER = re.compile('(Leia mais not.cias de.*)|((\:)*(\s)*P.gina Inicial(\s)*(\:)*)|(Indicar Not.cia)|(Envie para um amigo)|(Reportar erro)|(COMENT.*?RIOS.*\(.*?\))|(HYPERLINK(\s)*\".*?\")',re.IGNORECASE)
    texto = ER.sub('', texto)
    ER = re.compile('(Voltar.*?\|)|(Pr.ximo post.*)|(Post anterior)|((\d)*\.(\d)*.(\d)*(\s)*\-(\s)*(\d)*\:(\d)*)|(\|.*?\+)|(Conte.*?do\:)|((\d)*(\s)*coment.rios)|(\| esta(\s)*)|(veja mais not.cias)|(Ver todas as not.cias desta editoria)|(Termos de uso.*?modera.*?o)',re.IGNORECASE)
    texto = ER.sub('', texto)
    ER = re.compile('(Espa.o dos leitores)|((\d)*(\s)*Coment.rio\(*s*\)*)|(Participe not.cia)|(Importante(\s)*)|(Todos os postados no.*)|(Edi.*?o Impressa)|(pr.*?x\.)|(Ainda n.*?o existem\. Seja o.*)|(Collapse.*)|(All rights reserved(\.)*)|(---.*)|(N.*?o perca tempo e seja o primeiro.*?esta not.*?cia.)|((\s)*\|(\s)*[0-9]+)',re.IGNORECASE)
    texto = ER.sub('', texto)
    ER = re.compile('(Este.*?pode ser publicado.*?redistribu.do.*?citando a fonte\.)|(Fale conosco s RSS.*?Diminuir letra)|(es Paz Sem Voz.*?Medo V.*?deos Blogs Cinema Guia Obitu.*?rio Charges Rascunho Delivery Clube do Assinante Assinaturas Classificados OK)|((\|(\s)*\|))|(Corrigir.*?Mudar tamanho)|(([0-9])+ voto\(s\))|(sem votos ainda)|(Copie o c.digo e cole em sua p.gina pessoal\:)|(Celular(\s)*Tudo na hora pelo celular(\s)*acesse\:)|(m\.tudonahora\.com\.br)|(Envie uma Mensagem de texto com as letras TNH para o n.*)|(Receba diariamente as  no seu celular, direto da reda.*)|(Foto\: Divulga..o)|(Pr.xima.*?ltima(\s)*..)|(Veja todas as not.cias desta editoria\.)|(\(Foto\:.*?\))|(Related posts\:)|(Relacionadas(\s)*$)|(J. viu a nova ferramenta Cota..es Bovespa\? Dados e not.cias, tudo junto e super amig.vel\!(\s)*(Tags\:)*)|(Conhe.a a p.gina de EXAME no Facebook(\s)*(Tags\:)*)|((\s)*Anterior((\s)*\d)*Pr.xima)|((\s)*\((\s)*$)|(Voltar(\s)*Assinar(\s)*Feed(\s)*Links(\s)*Patrocinados(\s)*Anuncie(\s)*aqui(\s)*\-(\s)*Veja(\s)*todos(\s)*os(\s)*an.ncios(\s)*)|(Assessoria(\s)*$)|(BlogThis\! no Twitter no Facebook no Orkut)',re.IGNORECASE)
    texto = ER.sub('', texto)
    
    ER = re.compile('(\s)+,',re.IGNORECASE)
    texto = ER.sub(',', texto)
    
    ER = re.compile('(^(\s)+)|((\s)+$)',re.IGNORECASE)
    texto = ER.sub('', texto)
    
    texto = texto.replace('\\n\\n\\n','\n').replace('\\n\\n','\n').replace(' \\n','\n').replace('.:','.')
    
    return texto

def _unescape(texto):
    '''
        Limpa o texto do HTML com caracteres especiais.
        
        @texto: Texto antes de qualquer tratamento.
        @return: Texto da notícia padronizado.
    '''
    def fixup(m):
        texto = m.group(0)
        if texto[:2] == "&#":
            #Referência do caracter
            try:
                if texto[:3] == "&#x":
                    return unichr(int(texto[3:-1], 16))
                else:
                    return unichr(int(texto[2:-1]))
            except ValueError:
                pass
        else:
            #Entidade nomeada
            try:
                texto = unichr(htmlentitydefs.name2codepoint[texto[1:-1]])
            except KeyError:
                pass
        return texto #O texto sai como chegou
    return re.sub("&#?\w+;", fixup, texto)#Texto convertido
