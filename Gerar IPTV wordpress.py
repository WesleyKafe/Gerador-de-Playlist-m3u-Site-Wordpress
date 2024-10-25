import requests
import json
import re

# Função para obter o conteúdo de uma URL via requests, seguindo redirecionamentos
def get_content(url):
    try:
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()  # Verifica se ocorreu algum erro durante a requisição
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter conteúdo da URL: {url}")
        print(e)
        return None

# URL da API REST para obter categorias
categories_url = "https://ultratvonline.org/wp-json/wp/v2/categories"

# Função para obter todos os posts de uma categoria
def get_posts(category_id):
    posts = []
    page = 1
    per_page = 10
    more_posts = True

    while more_posts:
        posts_url = f"https://ultratvonline.org/wp-json/wp/v2/posts?categories={category_id}&page={page}&per_page={per_page}"
        posts_response = get_content(posts_url)

        if posts_response is None:
            print(f"Erro ao obter posts da categoria com ID {category_id}")
            break

        try:
            posts_data = json.loads(posts_response)
        except ValueError as e:
            print(f"Erro ao decodificar JSON de posts da categoria com ID {category_id}")
            print(e)
            break

        if not posts_data:
            print(f"Nenhum post encontrado na página {page} da categoria com ID {category_id}")
            break

        posts.extend(posts_data)
        page += 1

        # Verifica se a próxima página existe
        if len(posts_data) < per_page:
            more_posts = False

    return posts

# Função para obter a URL da imagem destacada de um post
def get_featured_image_url(post):
    featured_image_url = None
    if 'thumbnailUrl' in post:
        featured_image_url = post['thumbnailUrl']

    # Se não tiver 'thumbnailUrl', tenta extrair a imagem da postagem diretamente
    if not featured_image_url:
        try:
            content = post.get('content', {}).get('rendered', '')
            match = re.search(r'class=\"size-full wp-image-\d+ aligncenter\" src=\"([^\"]+)\"', content)
            if match:
                featured_image_url = match.group(1)
        except Exception as e:
            print(f"Erro ao obter imagem da postagem {post.get('id')}")
            print(e)

    return featured_image_url

# Função para encontrar links .m3u8 em um texto
def find_m3u8_links(text):
    return re.findall(r'(https://[^"\']*\.m3u8)', text)

# Faz uma solicitação para obter as categorias
categories_response = get_content(categories_url)

if categories_response is None:
    print("Erro ao obter categorias.")
    exit()

try:
    categories = json.loads(categories_response)
except ValueError as e:
    print("Erro ao decodificar JSON de categorias.")
    print(e)
    exit()

# Lista para armazenar os links .m3u8
m3u8_links = []

# Itera sobre cada categoria e obtém os posts
for category in categories:
    category_id = category.get('id')
    category_name = category.get('name')

    if not category_id or not category_name:
        continue

    print(f"Obtendo posts da categoria: {category_name}")

    # Obtém todos os posts da categoria atual
    posts = get_posts(category_id)

    if not posts:
        print(f"Nenhum post encontrado na categoria: {category_name}")
        continue

    # Itera sobre cada post e verifica o conteúdo
    for post in posts:
        post_id = post.get('id')
        post_title = post.get('title', {}).get('rendered')
        post_content = post.get('content', {}).get('rendered')

        if not post_id or not post_title or not post_content:
            continue

        # Obtém a URL da imagem destacada
        tvg_logo = get_featured_image_url(post)

        # Encontra todos os links .m3u8 diretamente nos posts
        direct_m3u8_links = find_m3u8_links(post_content)

        if direct_m3u8_links:
            for m3u8_link in direct_m3u8_links:
                m3u8_links.append((category_name, post_title, m3u8_link, tvg_logo))

        # Encontra todos os links que contêm abc.embedmax.site
        links_to_embedmax = re.findall(r'(https://abc\.embedmax\.site/[^"\']*)', post_content)

        if links_to_embedmax:
            for link in links_to_embedmax:
                # Transforma o link para o formato .m3u8
                m3u8_link = re.sub(r'/embed\.html\?autoplay=0$', '/tracks-v1/index.fmp4.m3u8', link)
                m3u8_links.append((category_name, post_title, m3u8_link, tvg_logo))

# Salva os links .m3u8 em um arquivo .m3u
playlist_filename = 'iptv_playlist.m3u'

with open(playlist_filename, 'w', encoding='utf-8') as file:
    file.write("#EXTM3U\n")

    for idx, (category_name, post_title, m3u8_link, tvg_logo) in enumerate(m3u8_links, start=1):
        file.write(f"#EXTINF:-1 tvg-id=\"{post_title}\" tvg-name=\"{post_title}\" tvg-logo=\"{tvg_logo if tvg_logo else 'None'}\" group-title=\"{category_name}\",{post_title}\n")
        file.write(f"{m3u8_link}\n\n")

print(f"Lista IPTV gerada com sucesso: {playlist_filename}")