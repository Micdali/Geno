"""Download dos Dados Abertos do CNPJ (dono: Lucas).

Baixa os ZIPs da competência definida em dados/config.yaml, um arquivo por vez, com retomada
(header Range), retries com backoff e barra de progresso. É idempotente: ZIPs já completos
(tamanho igual ao remoto) são pulados. Arquivos de Sócios nunca são baixados (LGPD).

Uso, a partir da raiz do repositório:
    python -m dados.etl.baixar --listar                  # só mostra o que há no servidor
    python -m dados.etl.baixar                           # baixa tudo do config.yaml
    python -m dados.etl.baixar --arquivo Simples Cnaes   # baixa só os arquivos indicados
"""
from __future__ import annotations

import argparse
import random
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import requests
import yaml
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parents[2]
CONFIG_PADRAO = RAIZ / "dados" / "config.yaml"
DAV = "{DAV:}"


class ErroDownload(Exception):
    """Falha que não adianta repetir (erro 4xx, disco cheio, arquivo proibido)."""


def carregar_config(caminho: Path = CONFIG_PADRAO) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def nomes_do_config(cfg: dict) -> list[str]:
    nomes: list[str] = []
    for grupo in cfg["arquivos"].values():
        nomes.extend(grupo)
    return nomes


def abrir_sessao(cfg: dict) -> requests.Session:
    s = requests.Session()
    s.auth = (cfg["fonte"]["share_token"], "")
    s.headers["User-Agent"] = "GENO-Ibmec/0.1 (projeto academico)"
    return s


def url_da_competencia(cfg: dict) -> str:
    f = cfg["fonte"]
    return f"{f['url_base'].rstrip('/')}/{f['competencia']}/"


def listar_remoto(sessao: requests.Session, cfg: dict) -> dict[str, dict]:
    """PROPFIND na pasta da competência: nome -> {tamanho, etag, modificado}."""
    t = (cfg["download"]["timeout_conexao_s"], cfg["download"]["timeout_leitura_s"])
    r = sessao.request("PROPFIND", url_da_competencia(cfg), headers={"Depth": "1"}, timeout=t)
    if r.status_code != 207:
        raise ErroDownload(f"PROPFIND retornou HTTP {r.status_code}: {r.text[:200]}")
    saida: dict[str, dict] = {}
    for resp in ET.fromstring(r.content).findall(f"{DAV}response"):
        href = resp.findtext(f"{DAV}href", "")
        nome = href.rstrip("/").rsplit("/", 1)[-1]
        prop = resp.find(f"{DAV}propstat/{DAV}prop")
        tam = prop.findtext(f"{DAV}getcontentlength") if prop is not None else None
        if not tam or not nome.lower().endswith(".zip"):
            continue
        saida[nome[:-4]] = {
            "tamanho": int(tam),
            "etag": (prop.findtext(f"{DAV}getetag") or "").strip('"'),
            "modificado": prop.findtext(f"{DAV}getlastmodified") or "",
        }
    return saida


def _espera(cfg: dict, tentativa: int) -> float:
    d = cfg["download"]
    base = min(d["espera_inicial_s"] * 2 ** (tentativa - 1), d["espera_maxima_s"])
    return base * (0.5 + random.random() / 2)


def _uma_tentativa(sessao, cfg, url, parcial: Path, info: dict, barra: tqdm) -> None:
    d = cfg["download"]
    timeout = (d["timeout_conexao_s"], d["timeout_leitura_s"])
    inicio = parcial.stat().st_size if parcial.exists() else 0
    cab = {"Range": f"bytes={inicio}-"} if inicio else {}
    with sessao.get(url, headers=cab, stream=True, timeout=timeout) as r:
        if r.status_code == 416:  # já temos tudo ou mais: o laço de fora confere o tamanho
            return
        if r.status_code >= 500 or r.status_code == 429:
            raise requests.ConnectionError(f"HTTP {r.status_code}")
        if r.status_code not in (200, 206):
            raise ErroDownload(f"HTTP {r.status_code} em {url}")
        if inicio and r.status_code == 200:  # servidor ignorou o Range: recomeça do zero
            inicio = 0
            barra.n = 0
            barra.refresh()
        modo = "ab" if inicio else "wb"
        with open(parcial, modo) as f:
            for bloco in r.iter_content(d["bloco_bytes"]):
                f.write(bloco)
                barra.update(len(bloco))


def baixar_arquivo(sessao, cfg, nome: str, info: dict) -> str:
    """Baixa um ZIP. Retorna 'pulado' ou 'baixado'."""
    if nome.lower().startswith("socios"):
        raise ErroDownload(f"{nome}: Sócios não é baixado (minimização de dados, LGPD)")

    pasta = RAIZ / cfg["caminhos"]["raw"]
    pasta.mkdir(parents=True, exist_ok=True)
    final, parcial, marca = pasta / f"{nome}.zip", pasta / f"{nome}.zip.part", pasta / f"{nome}.zip.etag"
    tamanho = info["tamanho"]

    if final.exists() and final.stat().st_size == tamanho:
        return "pulado"
    if final.exists():  # tamanho diferente do remoto: arquivo velho ou corrompido
        final.unlink()

    # Se o arquivo remoto mudou desde o download parcial, o parcial não serve.
    if parcial.exists():
        etag_antigo = marca.read_text().strip() if marca.exists() else ""
        if etag_antigo != info["etag"] or parcial.stat().st_size > tamanho:
            parcial.unlink()
    marca.write_text(info["etag"])

    ja_tem = parcial.stat().st_size if parcial.exists() else 0
    livre = shutil.disk_usage(pasta).free
    precisa = tamanho - ja_tem + cfg["download"]["folga_disco_gb"] * 1024**3
    if livre < precisa:
        raise ErroDownload(
            f"{nome}: espaço insuficiente. Livre {livre / 1e9:.1f} GB, "
            f"necessário {precisa / 1e9:.1f} GB (inclui folga de {cfg['download']['folga_disco_gb']} GB)"
        )

    url = url_da_competencia(cfg) + quote(f"{nome}.zip")
    tentativas = cfg["download"]["tentativas"]
    barra = tqdm(total=tamanho, initial=ja_tem, unit="B", unit_scale=True, unit_divisor=1024,
                 desc=nome, leave=True)
    try:
        for n in range(1, tentativas + 1):
            try:
                _uma_tentativa(sessao, cfg, url, parcial, info, barra)
            except ErroDownload:
                raise
            except (requests.RequestException, OSError) as e:
                if n == tentativas:
                    raise ErroDownload(f"{nome}: falhou após {tentativas} tentativas: {e}") from e
                espera = _espera(cfg, n)
                barra.write(f"  {nome}: {type(e).__name__}: {e}. Tentativa {n}/{tentativas}, "
                            f"retomando em {espera:.0f}s do byte {parcial.stat().st_size if parcial.exists() else 0}")
                time.sleep(espera)
                continue
            atual = parcial.stat().st_size if parcial.exists() else 0
            if atual == tamanho:
                break
            if atual > tamanho:
                parcial.unlink()
                barra.n = 0
                barra.refresh()
            if n == tentativas:
                raise ErroDownload(f"{nome}: tamanho final {atual} != remoto {tamanho}")
            time.sleep(_espera(cfg, n))
        parcial.replace(final)
        marca.unlink(missing_ok=True)
    finally:
        barra.close()
    return "baixado"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Baixa os Dados Abertos do CNPJ definidos em dados/config.yaml")
    ap.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    ap.add_argument("--listar", action="store_true", help="só lista o servidor, sem baixar")
    ap.add_argument("--arquivo", nargs="+", metavar="NOME",
                    help="baixa só estes (ex.: Estabelecimentos3 Simples); padrão: todos do config")
    args = ap.parse_args(argv)

    cfg = carregar_config(args.config)
    sessao = abrir_sessao(cfg)
    try:
        remoto = listar_remoto(sessao, cfg)
    except (requests.RequestException, ErroDownload) as e:
        print(f"ERRO ao listar {url_da_competencia(cfg)}: {e}", file=sys.stderr)
        return 1

    alvo = args.arquivo or nomes_do_config(cfg)
    ausentes = [n for n in alvo if n not in remoto]
    if ausentes:
        print(f"ERRO: não existem no servidor ({cfg['fonte']['competencia']}): {', '.join(ausentes)}",
              file=sys.stderr)
        return 1

    total = sum(remoto[n]["tamanho"] for n in alvo)
    print(f"Competência {cfg['fonte']['competencia']}: {len(alvo)} arquivos, {total / 1e9:.2f} GB")
    if args.listar:
        for n in alvo:
            print(f"  {n:22s} {remoto[n]['tamanho']:>14,d} bytes  {remoto[n]['modificado']}")
        return 0

    resultado = {"baixado": 0, "pulado": 0}
    for n in alvo:
        try:
            resultado[baixar_arquivo(sessao, cfg, n, remoto[n])] += 1
        except ErroDownload as e:
            print(f"\nERRO: {e}", file=sys.stderr)
            print(f"Parado em {n}. Rode de novo para retomar.", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrompido. Rode de novo para retomar de onde parou.", file=sys.stderr)
            return 130
    print(f"\nConcluído: {resultado['baixado']} baixados, {resultado['pulado']} já completos (pulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
