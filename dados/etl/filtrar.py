"""Filtro do recorte do GENO: ZIPs da Receita -> Parquet (dono: Lucas).

Processa UM ZIP por vez: extrai para dados/raw/tmp, lê o CSV com DuckDB (Latin-1, sem
cabeçalho, linhas malformadas vão para a tabela de rejeitados em vez de derrubar a carga),
filtra, grava Parquet e só então apaga o ZIP e o CSV. Parâmetros vêm de dados/config.yaml.

Etapas (nesta ordem; Empresas e Simples dependem de Estabelecimentos):
  estabelecimentos  UF e CNAE principal ou secundário -> parquet/estabelecimentos/parte_N.parquet
  empresas          raízes de CNPJ do recorte         -> parquet/empresas/parte_N.parquet
  simples           raízes de CNPJ do recorte         -> parquet/simples/parte_0.parquet
  dominio           tabelas de domínio inteiras       -> parquet/dominio/<nome>.parquet

Privacidade (relatório técnico, seções 7 e 12): telefones e fax são descartados já aqui e do
e-mail fica só o domínio (NULL para provedores genéricos). Sócios nunca entra.

Uso, a partir da raiz do repositório:
    python -m dados.etl.filtrar --baixar            # baixa o que faltar, um ZIP por vez
    python -m dados.etl.filtrar --etapa dominio     # só uma etapa
    python -m dados.etl.filtrar --refazer           # reprocessa mesmo se o Parquet existir
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

import duckdb

from dados.etl.baixar import (RAIZ, CONFIG_PADRAO, ErroDownload, abrir_sessao, baixar_arquivo,
                              carregar_config, listar_remoto)

ETAPAS = ("estabelecimentos", "empresas", "simples", "dominio")
EXEMPLOS_REJEITADOS = 20


def q(texto: str) -> str:
    """Literal SQL entre aspas simples."""
    return "'" + str(texto).replace("'", "''") + "'"


def lista_sql(valores: list[str]) -> str:
    return "[" + ", ".join(q(v) for v in valores) + "]"


def cnaes_do_recorte(cfg: dict) -> list[str]:
    r = cfg["recorte"]
    return list(r["cnaes"]) + (list(r["cnaes_opcionais"]) if r.get("incluir_opcionais") else [])


def leitura_csv(csv_path: Path, colunas: list[str], guardar_rejeitados: bool) -> str:
    """Expressão read_csv do DuckDB para os CSVs da Receita."""
    cols = ", ".join(f"{q(c)}: 'VARCHAR'" for c in colunas)
    extra = ", store_rejects=true, rejects_table='rej_t', rejects_scan='rej_s'" if guardar_rejeitados \
        else ", ignore_errors=true"
    return (f"read_csv({q(csv_path.as_posix())}, delim=';', header=false, quote='\"', "
            f"encoding='latin-1', all_varchar=true, columns={{{cols}}}{extra})")


def sql_estabelecimentos(cfg: dict, fonte: str) -> str:
    cols = cfg["colunas"]["estabelecimentos"]
    descartadas = set(cfg["colunas_descartadas"]["estabelecimentos"])
    mantidas = ", ".join(c for c in cols if c not in descartadas)
    lista = cnaes_do_recorte(cfg)
    cnaes_array, cnaes_in = lista_sql(lista), ", ".join(q(c) for c in lista)
    genericos = ", ".join(q(d) for d in cfg["recorte"]["provedores_genericos"])
    # d = parte do e-mail depois do @, em minúsculas; só vale se tiver cara de domínio.
    return f"""
        SELECT cnpj_basico || cnpj_ordem || cnpj_dv AS cnpj, {mantidas},
               CASE WHEN d IS NULL OR d IN ({genericos})
                         OR NOT regexp_matches(d, '^[a-z0-9-]+(\\.[a-z0-9-]+)+$')
                    THEN NULL ELSE d END AS dominio_email
        FROM (
            SELECT *, nullif(lower(trim(regexp_extract(correio_eletronico, '@([^@\\s]+)\\s*$', 1))), '') AS d
            FROM {fonte}
            WHERE uf = {q(cfg['recorte']['uf'])}
              AND (cnae_fiscal_principal IN ({cnaes_in})
                   OR list_has_any(string_split(cnae_fiscal_secundaria, ','), {cnaes_array}))
        )"""


def sql_por_raiz(fonte: str) -> str:
    return f"SELECT * FROM {fonte} WHERE cnpj_basico IN (SELECT cnpj_basico FROM raizes)"


def sql_dominio(fonte: str) -> str:
    return f"SELECT codigo, descricao FROM {fonte}"


def registrar_log(cfg: dict, arquivo: str, lidas: int, filtradas: int, rejeitadas: int, tempo: float) -> None:
    caminho = RAIZ / cfg["caminhos"]["log"]
    novo = not caminho.exists()
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["quando", "arquivo", "linhas_lidas", "linhas_filtradas", "linhas_rejeitadas", "tempo_s"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), arquivo, lidas, filtradas, rejeitadas,
                    f"{tempo:.1f}"])


def registrar_rejeitados(cfg: dict, con: duckdb.DuckDBPyConnection, arquivo: str) -> int:
    """Conta as linhas rejeitadas do arquivo e guarda alguns exemplos para inspeção."""
    n = con.execute("SELECT count(DISTINCT line) FROM rej_t").fetchone()[0]
    if n:
        caminho = RAIZ / cfg["caminhos"]["rejeitados"]
        novo = not caminho.exists()
        exemplos = con.execute(f"SELECT line, error_type, column_name, substr(csv_line, 1, 300), error_message "
                           f"FROM rej_t ORDER BY line LIMIT {EXEMPLOS_REJEITADOS}").fetchall()
        with open(caminho, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if novo:
                w.writerow(["arquivo", "linha", "tipo_erro", "coluna", "linha_csv", "mensagem"])
            for linha, tipo, coluna, csv_linha, msg in exemplos:
                w.writerow([arquivo, linha, tipo, coluna, csv_linha, msg])
    return n


class Processador:
    def __init__(self, cfg: dict, baixar: bool, manter_zip: bool, refazer: bool):
        self.cfg, self.manter_zip, self.refazer = cfg, manter_zip, refazer
        self.raw = RAIZ / cfg["caminhos"]["raw"]
        self.tmp = RAIZ / cfg["caminhos"]["tmp"]
        self.saida = RAIZ / cfg["caminhos"]["parquet"]
        self.con = duckdb.connect()
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.con.execute(f"SET temp_directory = {q(self.tmp.as_posix())}")
        self.con.execute("SET preserve_insertion_order = false")  # menos memória; a ordem não importa
        self.sessao = self.remoto = None
        if baixar:
            self.sessao = abrir_sessao(cfg)
            self.remoto = listar_remoto(self.sessao, cfg)

    def garantir_zip(self, nome: str) -> Path:
        zip_path = self.raw / f"{nome}.zip"
        if self.remoto is not None:
            if nome not in self.remoto:
                raise ErroDownload(f"{nome} não existe no servidor")
            baixar_arquivo(self.sessao, self.cfg, nome, self.remoto[nome])
        if not zip_path.exists():
            raise ErroDownload(f"{zip_path} não existe. Rode dados.etl.baixar ou use --baixar.")
        return zip_path

    def processar(self, nome: str, destino: Path, colunas: list[str], construir_sql) -> None:
        """Um ZIP -> um Parquet."""
        if destino.exists() and not self.refazer:
            print(f"{nome}: {destino.relative_to(RAIZ)} já existe, pulado")
            return
        t0 = time.time()
        zip_path = self.garantir_zip(nome)
        pasta = self.tmp / nome
        shutil.rmtree(pasta, ignore_errors=True)
        pasta.mkdir(parents=True)
        print(f"{nome}: extraindo {zip_path.stat().st_size / 1e6:,.0f} MB ...", flush=True)
        with zipfile.ZipFile(zip_path) as z:
            membros = [m for m in z.namelist() if not m.endswith("/")]
            if len(membros) != 1:
                raise ErroDownload(f"{nome}: esperava 1 arquivo no ZIP, achei {len(membros)}")
            z.extract(membros[0], pasta)
        csv_path = pasta / membros[0]

        destino.parent.mkdir(parents=True, exist_ok=True)
        provisorio = destino.with_name(destino.name + ".tmp")
        provisorio.unlink(missing_ok=True)
        self.con.execute("DROP TABLE IF EXISTS rej_t; DROP TABLE IF EXISTS rej_s;")

        print(f"{nome}: lendo e filtrando ...", flush=True)
        consulta = construir_sql(leitura_csv(csv_path, colunas, guardar_rejeitados=True))
        filtradas = self.con.execute(
            f"COPY ({consulta}) TO {q(provisorio.as_posix())} (FORMAT PARQUET, COMPRESSION ZSTD)"
        ).fetchone()[0]
        rejeitadas = registrar_rejeitados(self.cfg, self.con, nome)
        lidas = self.con.execute(
            f"SELECT count(*) FROM {leitura_csv(csv_path, colunas, guardar_rejeitados=False)}"
        ).fetchone()[0]

        # Valida o Parquet antes de apagar qualquer coisa.
        no_parquet = self.con.execute(f"SELECT count(*) FROM read_parquet({q(provisorio.as_posix())})").fetchone()[0]
        if no_parquet != filtradas:
            raise ErroDownload(f"{nome}: Parquet tem {no_parquet} linhas, esperado {filtradas}. ZIP mantido.")
        if lidas == 0:
            raise ErroDownload(f"{nome}: nenhuma linha lida do CSV. ZIP mantido para inspeção.")
        provisorio.replace(destino)

        tempo = time.time() - t0
        registrar_log(self.cfg, nome, lidas, filtradas, rejeitadas, tempo)
        aviso = " (0 linhas no recorte, registrado)" if filtradas == 0 else ""
        print(f"{nome}: lidas {lidas:,}  filtradas {filtradas:,}{aviso}  rejeitadas {rejeitadas:,}  {tempo:.0f}s")

        shutil.rmtree(pasta)
        if not self.manter_zip:
            zip_path.unlink()
            for sufixo in (".zip.etag", ".zip.part"):
                (self.raw / f"{nome}{sufixo}").unlink(missing_ok=True)

    # ---- etapas ----
    def estabelecimentos(self) -> None:
        cols = self.cfg["colunas"]["estabelecimentos"]
        for nome in self.cfg["arquivos"]["estabelecimentos"]:
            n = nome.removeprefix("Estabelecimentos")
            self.processar(nome, self.saida / "estabelecimentos" / f"parte_{n}.parquet", cols,
                           lambda fonte: sql_estabelecimentos(self.cfg, fonte))

    def _carregar_raizes(self) -> None:
        partes = list((self.saida / "estabelecimentos").glob("parte_*.parquet"))
        esperado = len(self.cfg["arquivos"]["estabelecimentos"])
        if len(partes) != esperado:
            raise ErroDownload(f"Estabelecimentos incompleto: {len(partes)} de {esperado} partes em Parquet. "
                               "Rode a etapa 'estabelecimentos' antes.")
        glob = (self.saida / "estabelecimentos" / "parte_*.parquet").as_posix()
        self.con.execute(f"CREATE OR REPLACE TEMP TABLE raizes AS "
                         f"SELECT DISTINCT cnpj_basico FROM read_parquet({q(glob)})")
        n = self.con.execute("SELECT count(*) FROM raizes").fetchone()[0]
        print(f"Raízes de CNPJ distintas no recorte: {n:,}")

    def empresas(self) -> None:
        self._carregar_raizes()
        cols = self.cfg["colunas"]["empresas"]
        for nome in self.cfg["arquivos"]["empresas"]:
            n = nome.removeprefix("Empresas")
            self.processar(nome, self.saida / "empresas" / f"parte_{n}.parquet", cols, sql_por_raiz)

    def simples(self) -> None:
        self._carregar_raizes()
        cols = self.cfg["colunas"]["simples"]
        for nome in self.cfg["arquivos"]["simples"]:
            self.processar(nome, self.saida / "simples" / "parte_0.parquet", cols, sql_por_raiz)

    def dominio(self) -> None:
        cols = self.cfg["colunas"]["dominio"]
        for nome in self.cfg["arquivos"]["dominio"]:
            self.processar(nome, self.saida / "dominio" / f"{nome.lower()}.parquet", cols, sql_dominio)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ZIPs da Receita -> Parquet do recorte do GENO")
    ap.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    ap.add_argument("--etapa", choices=(*ETAPAS, "todas"), default="todas")
    ap.add_argument("--baixar", action="store_true", help="baixa cada ZIP que faltar, um por vez")
    ap.add_argument("--manter-zip", action="store_true", help="não apaga o ZIP após validar o Parquet")
    ap.add_argument("--refazer", action="store_true", help="reprocessa mesmo se o Parquet já existir")
    args = ap.parse_args(argv)

    cfg = carregar_config(args.config)
    print(f"Recorte: UF={cfg['recorte']['uf']}, CNAEs={', '.join(cnaes_do_recorte(cfg))}")
    try:
        p = Processador(cfg, args.baixar, args.manter_zip, args.refazer)
        for etapa in (ETAPAS if args.etapa == "todas" else (args.etapa,)):
            print(f"\n=== etapa: {etapa}")
            getattr(p, etapa)()
    except ErroDownload as e:
        print(f"\nERRO: {e}", file=sys.stderr)
        return 1
    except duckdb.Error as e:
        print(f"\nERRO do DuckDB: {e}\nOs ZIPs não processados foram mantidos.", file=sys.stderr)
        return 1
    print("\nConcluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
