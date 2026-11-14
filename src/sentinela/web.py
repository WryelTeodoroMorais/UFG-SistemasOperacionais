"""Interface local para executar scripts Python isolados do Sentinela."""
import argparse
import base64
from collections import defaultdict
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from itertools import zip_longest
import json
from pathlib import Path
import random
import tempfile

from . import learning
from .data import digest
from .evaluation import baseline
from .features import extract
from .policy import Budget, authorize
from .sandbox import SandboxUnavailable, run


MIB = 1024**2
MAX_FILE = 8 * MIB
MAX_REQUEST = 24 * MIB
TIERS = {"small": 500, "medium": 1500}
METHODS = {
    "fixed": "Perfil fixo",
    "heuristic": "Heurística",
    "small": "ML · pequeno",
    "medium": "ML · médio",
    "full": "ML · completo",
}
ASSETS = Path(__file__).with_name("web_assets")
ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
LOCAL_INPUTS = {
    "train": "data/train.jsonl",
    "validation": "data/validation.jsonl",
    "test": "data/test.jsonl",
}
PYTHON_EXAMPLES = {
    "jsonl": {"path": "examples/resumir_jsonl.py", "label": "Contar tarefas por família em JSONL"},
}
JSONL_SUMMARY_DESCRIPTION = (
    "Lê o arquivo JSONL selecionado e conta quantas tarefas pertencem a cada família."
)
PYTHON_PRESETS = [
    {"id": "train_summary", "label": "JSONL · treino · 3.300", "script": "jsonl", "input": "train",
     "description": JSONL_SUMMARY_DESCRIPTION},
    {"id": "validation_summary", "label": "JSONL · validação · 100", "script": "jsonl", "input": "validation",
     "description": JSONL_SUMMARY_DESCRIPTION},
    {"id": "test_summary", "label": "JSONL · teste · 850", "script": "jsonl", "input": "test",
     "description": JSONL_SUMMARY_DESCRIPTION},
    {"id": "custom_empty", "label": "Código próprio · sem exemplo", "script": None, "input": "none",
     "description": "Sem arquivo de exemplo. Se o script precisar de dados, carregue um arquivo em Entrada própria."},
]


def training_order(source: Path):
    """Mantém famílias representadas e inclui o subconjunto menor no maior."""
    families = defaultdict(list)
    for line in source.read_text().splitlines():
        families[json.loads(line)["family"]].append(line)
    randomizer = random.Random(336)
    for rows in families.values():
        randomizer.shuffle(rows)
    return [
        line for batch in zip_longest(*(families[name] for name in sorted(families)))
        for line in batch if line is not None
    ]


def model_for(root: Path, tier: str):
    if tier == "full":
        return learning.frozen(root)
    train = root / "data/train.jsonl"
    validation = root / "data/validation.jsonl"
    signature = hashlib.sha256(
        (digest(train) + digest(validation) + digest(Path(learning.__file__))
         + digest(Path(__file__))).encode()
    ).hexdigest()[:16]
    cache = root / ".build/sentinela-web-models"
    target = cache / f"{tier}-{signature}"
    if not target.exists():
        rows = training_order(train)[:TIERS[tier]]
        if len(rows) != TIERS[tier]:
            raise ValueError("O conjunto de treino é pequeno demais para este nível.")
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as stage:
            candidate = Path(stage) / "candidate"
            (candidate / "data").mkdir(parents=True)
            (candidate / "data/train.jsonl").write_text("\n".join(rows) + "\n")
            (candidate / "data/validation.jsonl").write_bytes(validation.read_bytes())
            learning.train(candidate)
            try:
                candidate.rename(target)
            except OSError:
                if not target.is_dir():
                    raise
    return learning.frozen(target)


def upload(data):
    if not isinstance(data, str):
        raise ValueError("Arquivo inválido.")
    decoded = base64.b64decode(data, validate=True)
    if len(decoded) > MAX_FILE:
        raise ValueError("Cada arquivo pode ter até 8 MiB.")
    return decoded


def output_files(result: dict, directory: Path):
    """Inclui os arquivos exportados pelo sandbox, até 4 MiB no total."""
    remaining = 4 * MIB
    files = []
    for name, metadata in sorted(result["outputs"].items()):
        content = None
        if metadata["bytes"] <= remaining:
            content = base64.b64encode((directory / name).read_bytes()).decode("ascii")
            remaining -= metadata["bytes"]
        files.append({"name": name, **metadata, "content": content})
    return files


def execute_python(root: Path, payload: dict, directory: Path):
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Informe o código Python.")
    if len(code.encode()) > 128_000:
        raise ValueError("O script pode ter até 128 kB.")
    encoded = payload.get("input")
    input_example = payload.get("input_example", "none")
    if input_example is None:
        input_example = "none"
    if encoded is not None:
        data = upload(encoded)
        use_input = True
    elif input_example == "none":
        data = b""
        use_input = False
    elif isinstance(input_example, str) and input_example in LOCAL_INPUTS:
        data = (root / LOCAL_INPUTS[input_example]).read_bytes()
        use_input = True
    else:
        raise ValueError("Escolha um exemplo de entrada local válido.")
    method = payload.get("method", "full")
    heuristic = payload.get("heuristic", "ast")
    if not isinstance(method, str) or method not in METHODS or heuristic not in ("ast", "size"):
        raise ValueError("Escolha um método e uma heurística válidos.")
    comparing = payload.get("compare") is True
    methods = METHODS if comparing else (method,)
    ceiling = Budget(read_input=use_input)
    features = extract(code, len(data))
    results = []
    for method in methods:
        train_samples = None
        label = METHODS[method]
        if method in ("fixed", "heuristic"):
            recommendation = baseline({"features": features, "input_bytes": len(data)}, method)
            if method == "heuristic":
                label += " · AST + tamanho" if heuristic == "ast" else " · tamanho"
                if heuristic == "size":
                    recommendation.update(read_input=True, write_output=True)
        else:
            package, config = model_for(root, method)
            recommendation = learning.recommend(
                package, features, config["margin"], config["wall_margin"]
            )
            train_samples = config["train_samples"]
        output = directory / method
        measured = run(code, data, authorize(recommendation, ceiling), output)
        files = output_files(measured, output)
        results.append({
            **measured, "method": method, "label": label, "train_samples": train_samples,
            "success": measured["returncode"] == 0 and not measured["timed_out"],
            "files": files,
        })
    reference = results[0]
    for result in results:
        if result["success"] and comparing and reference["success"]:
            result["matches"] = (
                result["outputs"] == reference["outputs"]
                and result["stdout"] == reference["stdout"]
            )
    return {
        "results": results,
        "reference": "fixed" if comparing and reference["success"] else None,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "Sentinela"

    def send_body(self, status, content_type, content):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status, data):
        self.send_body(status, "application/json; charset=utf-8",
                       json.dumps(data).encode())

    def allowed_host(self):
        # O navegador não pode usar um nome remoto apontado para o loopback.
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.allowed_host():
            self.send_json(403, {"error": "Use o endereço local mostrado no terminal."})
        elif self.path in ROUTES:
            name, content_type = ROUTES[self.path]
            self.send_body(200, content_type, (ASSETS / name).read_bytes())
        elif self.path == "/api/example":
            root = self.server.root
            scripts = [
                {"id": identifier, "label": item["label"],
                 "code": (root / item["path"]).read_text()}
                for identifier, item in PYTHON_EXAMPLES.items()
            ]
            self.send_json(200, {
                "scripts": scripts,
                "presets": PYTHON_PRESETS, "default_preset": "validation_summary",
            })
        else:
            self.send_json(404, {"error": "Endereço desconhecido."})

    def do_POST(self):
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if not self.allowed_host() or self.headers.get("Origin", origin) != origin:
            self.send_json(403, {"error": "Origem não autorizada."})
            return
        if self.path != "/api/python":
            self.send_json(404, {"error": "Operação desconhecida."})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Envie uma requisição JSON."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_REQUEST:
                self.send_json(413, {"error": "A requisição excede o limite de tamanho ou está vazia."})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Informe os campos da operação.")
            with tempfile.TemporaryDirectory(prefix="sentinela-web-") as temporary:
                result = execute_python(self.server.root, payload, Path(temporary))
        except (ValueError, SyntaxError, OverflowError) as error:
            self.send_json(400, {"error": str(error)})
        except SandboxUnavailable as error:
            self.send_json(503, {"error": f"Bubblewrap indisponível: {error}"})
        except OSError as error:
            self.send_json(500, {"error": f"Falha ao acessar os arquivos do projeto: {error}"})
        else:
            self.send_json(200, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--prepare-models", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if not (root / "data/train.jsonl").is_file():
        parser.error("Execute na raiz do repositório Sentinela ML.")
    if args.prepare_models:
        for tier in TIERS:
            _, config = model_for(root, tier)
            print(f"{METHODS[tier]}: {config['train_samples']} tarefas", flush=True)
        return
    with HTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.root = root
        print(f"Sentinela ML · http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
