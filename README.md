# Finder200

**OSINT Username & Name Tool**
Criado por **Luciano Ramone**

Ferramenta em Python para reconhecimento OSINT (Open Source Intelligence) que verifica a presença de um **nome de usuário** em dezenas de redes sociais e plataformas, e/ou pesquisa o **nome completo** de uma pessoa via dorking em motor de busca.

```
╔══════════════════════════════╗
║          FINDER200           ║
║   OSINT Username & Name Tool ║
╚══════════════════════════════╝
by Luciano Ramone
```

---

## ⚠️ Aviso legal e uso responsável

Esta ferramenta faz apenas requisições a **URLs e páginas públicas**, sem burlar autenticação, CAPTCHA ou qualquer mecanismo de proteção. Ainda assim:

- Use apenas para fins legítimos: verificação da própria pegada digital, pesquisa de reputação autorizada, investigações de segurança, jornalismo investigativo, due diligence, etc.
- Respeite os **Termos de Serviço** de cada plataforma e motor de busca.
- Ao lidar com dados de terceiros, observe a **LGPD** (Lei Geral de Proteção de Dados) e legislações equivalentes aplicáveis à sua jurisdição.
- A busca por nome (`-n`) pode retornar **falsos positivos** (homônimos) e **falsos negativos** (perfis privados ou não indexados) — sempre valide manualmente antes de tirar conclusões.
- O autor não se responsabiliza por uso indevido desta ferramenta.

---

## 🔧 Instalação

Requer Python 3.8+.

```bash
pip install requests
```

Baixe o arquivo `finder200.py` e pronto — não há outras dependências.

---

## 🚀 Uso

### Buscar por nome de usuário (username)

Verifica a existência do username em ~37 plataformas, checando status HTTP e trechos de página característicos de "perfil não encontrado".

```bash
python3 finder200.py "luc.ramone"
```

### Buscar por nome completo da pessoa

Realiza dorking (`site:dominio.com "Nome Completo"`) via DuckDuckGo em 9 redes sociais.

```bash
python3 finder200.py -n "Luciano Ramone"
```

### Buscar pelos dois ao mesmo tempo

```bash
python3 finder200.py "luc.ramone" -n "Luciano Ramone"
```

### Opções disponíveis

| Parâmetro | Descrição | Padrão |
|---|---|---|
| `username` | Nome de usuário (posicional, opcional se `-n` for usado) | — |
| `-n`, `--name` | Nome completo da pessoa para busca por dorking | — |
| `--timeout` | Timeout por requisição, em segundos | `6.0` |
| `--threads` | Número de requisições paralelas | `20` |
| `--json ARQUIVO` | Salva todos os resultados em um arquivo JSON | — |

---

## 📋 Exemplo de saída

```
╔══════════════════════════════╗
║          FINDER200           ║
║   OSINT Username & Name Tool ║
╚══════════════════════════════╝
by Luciano Ramone

Username: luc.ramone

[+] GitHub      ENCONTRADO      https://github.com/luc.ramone
[-] Instagram   NÃO ENCONTRADO
[+] Reddit      ENCONTRADO      https://www.reddit.com/user/luc.ramone/about.json
[?] Twitter/X   INDETERMINADO   (HTTP 403 (site pode bloquear bots))
[+] ArtStation  ENCONTRADO      https://www.artstation.com/luc.ramone
[-] Hashnode    NÃO ENCONTRADO

Total: 3 encontrados de 37 verificados

[Busca por nome] Luciano Ramone

[+] LinkedIn — 2 resultado(s):
      • Luciano Ramone - Engenheiro de Software - LinkedIn
        https://www.linkedin.com/in/luciano-ramone
[-] Facebook — nenhum resultado encontrado
[+] Instagram — 1 resultado(s):
      • Luciano Ramone (@luc.ramone) • Fotos e vídeos do Instagram
        https://www.instagram.com/luc.ramone/

Total: 3 resultado(s) encontrados em 9 plataforma(s) pesquisadas

[!] Resultados de dorking dependem do índice do motor de busca
    e podem trazer falsos positivos (homônimos) ou nada, mesmo
    que o perfil exista. Confira manualmente antes de concluir.

Tempo total: 5.8s
```

---

## 🗂️ Plataformas verificadas

### Por username (checagem direta de URL de perfil)

GitHub, GitLab, Reddit, Instagram, Twitter/X, TikTok, Facebook, YouTube, Twitch, ArtStation, Hashnode, DeviantArt, Pinterest, Medium, Steam, SoundCloud, Spotify, Telegram, Vimeo, Flickr, Behance, Dribbble, Hacker News, Keybase, Patreon, Kaggle, Replit, CodePen, NPM, PyPI, Docker Hub, LeetCode, Quora, Tumblr, VK, Linktree, About.me, Trello, Roblox.

### Por nome completo (dorking via DuckDuckGo)

Facebook, Instagram, LinkedIn, Twitter/X, TikTok, YouTube, Pinterest, VK, Quora.

> Ambas as listas podem ser expandidas editando as constantes `SITES` e `NAME_SEARCH_SITES` no código.

---

## 🧠 Como funciona

1. **Checagem por username**: para cada plataforma, monta a URL de perfil (`https://site.com/{username}`), faz a requisição HTTP e classifica o resultado como:
   - `ENCONTRADO` — HTTP 2xx e nenhum texto de "não encontrado" detectado.
   - `NÃO ENCONTRADO` — HTTP 404 ou trecho característico de página inexistente no corpo da resposta (necessário porque vários sites retornam sempre HTTP 200, mesmo para perfis inexistentes).
   - `INDETERMINADO` — a plataforma bloqueou a requisição (ex.: HTTP 403 por proteção anti-bot); requer verificação manual.

2. **Busca por nome**: como redes sociais não oferecem busca pública sem autenticação, a ferramenta usa a técnica de **dorking**, consultando o DuckDuckGo HTML (`site:dominio "Nome Completo"`) e extraindo os links de resultado.

3. As requisições são paralelizadas com `ThreadPoolExecutor` para reduzir o tempo total de execução.

---

## 📦 Saída em JSON

```bash
python3 finder200.py "luc.ramone" -n "Luciano Ramone" --json resultado.json
```

Gera um arquivo estruturado com os campos `username_results` e `name_results`, útil para integração com outras ferramentas ou pipelines de análise.

---

## 📄 Licença

Uso livre para fins pessoais e profissionais legítimos. Sem garantias — utilize com responsabilidade.

---

**Finder200** • por Luciano Ramone
