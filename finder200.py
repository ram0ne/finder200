#!/usr/bin/env python3
"""
Finder200 — OSINT Username & Name Tool
---------------------------------------
Criado por: Luciano Ramone

Verifica a existência de um nome de usuário em diversas plataformas
online (checagem por URL de perfil) e/ou busca pelo nome completo de
uma pessoa em redes sociais (via dorking em motor de busca).

Uso:
    python3 finder200.py <username> [--timeout 5] [--threads 20] [--json saida.json]
    python3 finder200.py -n "Luciano Ramone"
    python3 finder200.py "luc.ramone" -n "Luciano Ramone"

Aviso legal:
Use apenas para fins legítimos (pesquisa de reputação, verificação da
própria presença online, investigações autorizadas, etc). Respeite os
Termos de Serviço de cada plataforma/motor de busca e a legislação
aplicável (ex.: LGPD ao lidar com dados de terceiros).
"""

import argparse
import concurrent.futures
import html
import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

import requests

# ----------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

@dataclass
class Site:
    name: str
    url_template: str                 # use {} para o username
    method: str = "GET"
    # Se not_found_text estiver presente na resposta, consideramos NÃO ENCONTRADO
    # mesmo que o status seja 200 (comum em SPAs que sempre retornam 200).
    not_found_text: Optional[str] = None
    # Códigos de status que indicam "não encontrado" (além do óbvio 404)
    not_found_status: tuple = (404,)
    # Alguns sites bloqueiam bots e retornam 403 mesmo quando o perfil existe;
    # nesses casos marcamos como "desconhecido" em vez de "não encontrado".
    ambiguous_status: tuple = ()
    headers: dict = field(default_factory=dict)


# Lista de plataformas. Pode (e deve) ser expandida conforme necessidade.
SITES = [
    Site("GitHub", "https://github.com/{}"),
    Site("GitLab", "https://gitlab.com/{}"),
    Site("Reddit", "https://www.reddit.com/user/{}/about.json",
         not_found_text='"error": 404'),
    Site("Instagram", "https://www.instagram.com/{}/",
         not_found_text="Sorry, this page"),
    Site("Twitter/X", "https://x.com/{}",
         ambiguous_status=(403,)),
    Site("TikTok", "https://www.tiktok.com/@{}",
         not_found_text="Couldn't find this account"),
    Site("Facebook", "https://www.facebook.com/{}",
         ambiguous_status=(403,)),
    Site("YouTube", "https://www.youtube.com/@{}"),
    Site("Twitch", "https://www.twitch.tv/{}",
         not_found_text="Sorry. Unless you've got a time machine"),
    Site("ArtStation", "https://www.artstation.com/{}"),
    Site("Hashnode", "https://hashnode.com/@{}"),
    Site("DeviantArt", "https://www.deviantart.com/{}",
         not_found_text="isn't here"),
    Site("Pinterest", "https://www.pinterest.com/{}/",
         not_found_text="Page not found"),
    Site("Medium", "https://medium.com/@{}",
         not_found_text="404"),
    Site("Steam", "https://steamcommunity.com/id/{}",
         not_found_text="The specified profile could not be found"),
    Site("SoundCloud", "https://soundcloud.com/{}"),
    Site("Spotify", "https://open.spotify.com/user/{}"),
    Site("Telegram", "https://t.me/{}",
         not_found_text="If you have Telegram"),
    Site("Vimeo", "https://vimeo.com/{}"),
    Site("Flickr", "https://www.flickr.com/people/{}"),
    Site("Behance", "https://www.behance.net/{}"),
    Site("Dribbble", "https://dribbble.com/{}",
         not_found_text="Whoops, that page is gone"),
    Site("HackerNews", "https://news.ycombinator.com/user?id={}",
         not_found_text="No such user"),
    Site("Keybase", "https://keybase.io/{}",
         not_found_text="User not found"),
    Site("Patreon", "https://www.patreon.com/{}",
         not_found_text="Page Not Found"),
    Site("Kaggle", "https://www.kaggle.com/{}",
         not_found_text="Nothing to see here"),
    Site("Replit", "https://replit.com/@{}"),
    Site("CodePen", "https://codepen.io/{}"),
    Site("NPM", "https://www.npmjs.com/~{}"),
    Site("PyPI", "https://pypi.org/user/{}/"),
    Site("Docker Hub", "https://hub.docker.com/u/{}"),
    Site("LeetCode", "https://leetcode.com/{}"),
    Site("Quora", "https://www.quora.com/profile/{}"),
    Site("Tumblr", "https://{}.tumblr.com", not_found_text="there's nothing here"),
    Site("VK", "https://vk.com/{}"),
    Site("Linktree", "https://linktr.ee/{}",
         not_found_text="isn't on Linktree"),
    Site("About.me", "https://about.me/{}"),
    Site("Trello", "https://trello.com/{}",
         not_found_text="Cannot find"),
    Site("Roblox", "https://www.roblox.com/user.aspx?username={}",
         not_found_text="Page cannot be found"),
]


# ----------------------------------------------------------------------
# Plataformas usadas na busca por NOME (dorking via motor de busca)
# ----------------------------------------------------------------------
# Aqui não existe uma URL de perfil previsível (nome != username), então
# a estratégia é pesquisar "site:dominio "Nome da Pessoa"" e extrair os
# links retornados pelo motor de busca.

NAME_SEARCH_SITES = [
    ("Facebook", "facebook.com"),
    ("Instagram", "instagram.com"),
    ("LinkedIn", "linkedin.com/in"),
    ("Twitter/X", "twitter.com OR site:x.com"),
    ("TikTok", "tiktok.com"),
    ("YouTube", "youtube.com"),
    ("Pinterest", "pinterest.com"),
    ("VK", "vk.com"),
    ("Quora", "quora.com/profile"),
]

MAX_RESULTS_PER_SITE = 5
DUCKDUCKGO_HTML_URL = "https://html.duckduckgo.com/html/"


def _extract_real_url(href: str) -> str:
    """DuckDuckGo às vezes retorna links de redirecionamento
    (duckduckgo.com/l/?uddg=<url-real-encodada>); aqui extraímos a URL real."""
    if "duckduckgo.com/l/" in href:
        qs = parse_qs(urlparse(href).query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def _strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def search_name_on_site(platform: str, domain_query: str, full_name: str,
                         timeout: float, session: requests.Session):
    """Busca 'site:<domain> "Nome Completo"' no DuckDuckGo e extrai resultados."""
    query = f'site:{domain_query} "{full_name}"'
    params = {"q": query}
    headers = {**DEFAULT_HEADERS}

    try:
        resp = session.post(DUCKDUCKGO_HTML_URL, data=params,
                             headers=headers, timeout=timeout)
    except requests.RequestException as e:
        return {"platform": platform, "query": query, "status": "erro",
                "results": [], "detail": str(e)}

    if resp.status_code != 200:
        return {"platform": platform, "query": query, "status": "erro",
                "results": [], "detail": f"HTTP {resp.status_code}"}

    # Extrai blocos <a class="result__a" href="...">Título</a>
    matches = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        resp.text, flags=re.DOTALL,
    )

    results = []
    for href, title_html in matches[:MAX_RESULTS_PER_SITE]:
        results.append({
            "title": _strip_tags(title_html),
            "url": _extract_real_url(href),
        })

    status = "encontrado" if results else "nao_encontrado"
    return {"platform": platform, "query": query, "status": status,
            "results": results, "detail": None}


def run_name_search(full_name: str, timeout: float, threads: int):
    results = []
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {
                pool.submit(search_name_on_site, platform, domain, full_name,
                            timeout, session): platform
                for platform, domain in NAME_SEARCH_SITES
            }
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    order = {p: i for i, (p, _) in enumerate(NAME_SEARCH_SITES)}
    results.sort(key=lambda r: order[r["platform"]])
    return results


def print_name_results(full_name: str, results):
    print(f"\n[Busca por nome] {full_name}\n")
    total_found = 0
    for r in results:
        if r["status"] == "encontrado":
            total_found += len(r["results"])
            print(f"[+] {r['platform']} — {len(r['results'])} resultado(s):")
            for item in r["results"]:
                print(f"      • {item['title']}")
                print(f"        {item['url']}")
        elif r["status"] == "nao_encontrado":
            print(f"[-] {r['platform']} — nenhum resultado encontrado")
        else:
            print(f"[!] {r['platform']} — erro na busca ({r['detail']})")
    print(f"\nTotal: {total_found} resultado(s) encontrados em "
          f"{len(results)} plataforma(s) pesquisadas")
    print("\n[!] Resultados de dorking dependem do índice do motor de busca")
    print("    e podem trazer falsos positivos (homônimos) ou nada, mesmo")
    print("    que o perfil exista. Confira manualmente antes de concluir.")


# ----------------------------------------------------------------------
# Núcleo da checagem por username
# ----------------------------------------------------------------------

def check_site(site: Site, username: str, timeout: float, session: requests.Session):
    url = site.url_template.format(username)
    headers = {**DEFAULT_HEADERS, **site.headers}

    try:
        resp = session.request(
            site.method, url, headers=headers, timeout=timeout,
            allow_redirects=True,
        )
    except requests.RequestException as e:
        return {
            "site": site.name, "url": url, "status": "erro",
            "found": None, "detail": str(e),
        }

    code = resp.status_code

    if code in site.ambiguous_status:
        return {
            "site": site.name, "url": url, "status": "indeterminado",
            "found": None, "detail": f"HTTP {code} (site pode bloquear bots)",
        }

    if code in site.not_found_status:
        return {"site": site.name, "url": url, "status": "nao_encontrado",
                "found": False, "detail": f"HTTP {code}"}

    if site.not_found_text and site.not_found_text.lower() in resp.text.lower():
        return {"site": site.name, "url": url, "status": "nao_encontrado",
                "found": False, "detail": "texto de página inexistente encontrado"}

    if 200 <= code < 300:
        return {"site": site.name, "url": url, "status": "encontrado",
                "found": True, "detail": f"HTTP {code}"}

    return {"site": site.name, "url": url, "status": "indeterminado",
            "found": None, "detail": f"HTTP {code}"}


def run(username: str, timeout: float, threads: int):
    results = []
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {
                pool.submit(check_site, site, username, timeout, session): site
                for site in SITES
            }
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    # Ordena na mesma ordem da lista original de sites
    order = {s.name: i for i, s in enumerate(SITES)}
    results.sort(key=lambda r: order[r["site"]])
    return results


# ----------------------------------------------------------------------
# Saída formatada
# ----------------------------------------------------------------------

def print_banner(username: Optional[str] = None):
    print("╔══════════════════════════════╗")
    print("║          FINDER200           ║")
    print("║   OSINT Username & Name Tool ║")
    print("╚══════════════════════════════╝")
    print("by Luciano Ramone")
    if username:
        print(f"\nUsername: {username}\n")
    else:
        print()


def print_results(results):
    name_width = max(len(r["site"]) for r in results) + 1
    found_count = 0
    for r in results:
        label = r["site"].ljust(name_width)
        if r["status"] == "encontrado":
            found_count += 1
            print(f"[+] {label} ENCONTRADO      {r['url']}")
        elif r["status"] == "nao_encontrado":
            print(f"[-] {label} NÃO ENCONTRADO")
        elif r["status"] == "indeterminado":
            print(f"[?] {label} INDETERMINADO   ({r['detail']})")
        else:
            print(f"[!] {label} ERRO            ({r['detail']})")
    print(f"\nTotal: {found_count} encontrados de {len(results)} verificados")


def main():
    parser = argparse.ArgumentParser(
        description="Finder200 — OSINT Username & Name Tool (por Luciano Ramone)"
    )
    parser.add_argument("username", nargs="?", default=None,
                         help="Nome de usuário a ser pesquisado (opcional se -n for usado)")
    parser.add_argument("-n", "--name", metavar="\"NOME COMPLETO\"", default=None,
                         help="Nome completo da pessoa, para busca por dorking em redes sociais")
    parser.add_argument("--timeout", type=float, default=6.0, help="Timeout por requisição (s)")
    parser.add_argument("--threads", type=int, default=20, help="Nº de requisições paralelas")
    parser.add_argument("--json", metavar="ARQUIVO", help="Salvar resultados em JSON")
    args = parser.parse_args()

    if not args.username and not args.name:
        parser.error("informe um username, --name \"Nome Completo\", ou ambos.")

    output = {}
    start = time.time()

    print_banner(args.username)

    if args.username:
        results = run(args.username, args.timeout, args.threads)
        print_results(results)
        output["username"] = args.username
        output["username_results"] = results

    if args.name:
        name_results = run_name_search(args.name, args.timeout, args.threads)
        print_name_results(args.name, name_results)
        output["name"] = args.name
        output["name_results"] = name_results

    elapsed = time.time() - start
    print(f"\nTempo total: {elapsed:.1f}s")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Resultados salvos em: {args.json}")


if __name__ == "__main__":
    main()
