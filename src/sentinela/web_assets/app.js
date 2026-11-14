const byId = id => document.getElementById(id);
const status = byId("status");
const results = byId("results");
const resultsBody = byId("results-body");
const MAX_FILE = 8 * 1024 ** 2;
let busy = false;
let scriptExamples = new Map();
let pythonPresets = new Map();
let activePythonInput = "validation";

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function showStatus(message, error = false) {
  status.hidden = !message;
  status.textContent = message;
  status.classList.toggle("error", error);
}

function setBusy(value) {
  busy = value;
  for (const button of document.querySelectorAll("form button")) {
    button.disabled = value;
  }
}

async function request(path, payload) {
  const options = payload === undefined ? undefined : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Falha ao acessar o servidor.");
  return data;
}

function encodedFile(file) {
  if (file.size > MAX_FILE) throw new Error("Cada arquivo pode ter até 8 MiB.");
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",", 2)[1]);
    reader.onerror = () => reject(new Error("Falha ao ler " + file.name));
    reader.readAsDataURL(file);
  });
}

function format(value, decimals = 2) {
  return value == null ? "—" : value.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  });
}

function table(columns, rows) {
  const wrapper = element("div", undefined, "table-scroll");
  const grid = element("table");
  const header = grid.createTHead().insertRow();
  for (const column of columns) {
    const cell = element("th", column);
    cell.scope = "col";
    header.append(cell);
  }
  const body = grid.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const [index, value] of row.entries()) {
      const cell = element(index === 0 ? "th" : "td");
      if (index === 0) cell.scope = "row";
      cell.append(value);
      tr.append(cell);
    }
  }
  wrapper.append(grid);
  return wrapper;
}

function download(file) {
  const data = Uint8Array.from(atob(file.content), character => character.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([data], { type: "application/octet-stream" }));
  const link = element("a");
  link.href = url;
  link.download = file.name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function details(label, result) {
  const view = element("details", undefined, "details");
  view.append(element("summary", label));
  const { budget, stdout, stderr, files } = result;
  if (budget) {
    const input = budget.read_input ? "permitida" : "bloqueada";
    const output = budget.write_output ? "permitida" : "bloqueada";
    view.append(element("p", "Leitura da entrada " + input + " · Escrita na saída " + output, "hint"));
  }
  if (stdout) {
    view.append(element("p", "Saída padrão", "hint"), element("pre", stdout));
  }
  if (stderr) {
    view.append(element("p", "Mensagens de erro", "hint"), element("pre", stderr));
  }
  if (!stdout && !stderr && !files.length) {
    view.append(element("p", "A execução não gerou mensagens ou arquivos.", "hint"));
  }
  const list = element("div", undefined, "file-list");
  for (const file of files) {
    if (file.content === null) {
      list.append(element("span", file.name + " · excedeu o limite de download", "hint"));
      continue;
    }
    const button = element("button", "Baixar " + file.name, "secondary");
    button.type = "button";
    button.addEventListener("click", () => download(file));
    list.append(button);
  }
  view.append(list);
  return view;
}

function renderPython(data) {
  const rows = data.results.map(result => {
    const label = result.timed_out ? "Tempo esgotado" : result.success ? "Concluiu" : "Falhou";
    const match = result.matches === true ? "Confere" : result.matches === false ? "Diverge" : "—";
    return [
      result.label,
      format(result.train_samples, 0),
      element("span", label, result.success ? "ok" : "warn"),
      match,
      format(result.budget.memory_mb, 0),
      format(result.budget.wall_seconds, 3),
      format(result.wall_seconds, 3),
      format(result.peak_rss_mb),
    ];
  });
  resultsBody.append(table([
    "Método", "Treino", "Execução", "Saída", "Limite virtual (MiB)", "Limite (s)",
    "Tempo observado (s)", "Pico RSS (MiB)",
  ], rows));
  if (data.reference) {
    resultsBody.append(element("p", "Referência para a coluna Saída: saída do perfil fixo.", "hint"));
  }
  for (const result of data.results) {
    const view = details("Detalhes · " + result.label, result);
    view.open = data.results.length === 1;
    resultsBody.append(view);
  }
}

async function execute(path, progress, payload, render) {
  if (busy) return;
  setBusy(true);
  results.hidden = true;
  resultsBody.replaceChildren();
  showStatus(progress);
  try {
    render(await request(path, await payload()));
    results.hidden = false;
    showStatus("Resultados disponíveis.");
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function loadExample() {
  setBusy(true);
  try {
    const data = await request("/api/example");
    scriptExamples = new Map(data.scripts.map(example => [example.id, example.code]));
    pythonPresets = new Map(data.presets.map(preset => [preset.id, preset]));
    const presetSelect = byId("python-example-preset");
    presetSelect.replaceChildren();
    for (const preset of data.presets) {
      const option = element("option", preset.label);
      option.value = preset.id;
      presetSelect.append(option);
    }
    presetSelect.value = data.default_preset;
    const defaultPreset = pythonPresets.get(data.default_preset);
    byId("python-example-description").textContent = defaultPreset.description;
    activePythonInput = defaultPreset.input;
    byId("code").value = scriptExamples.get(defaultPreset.script);
    byId("script-file").value = "";
    byId("script-input").value = "";
    showStatus("");
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    setBusy(false);
  }
}

byId("example").addEventListener("click", loadExample);
byId("python-example-preset").addEventListener("change", event => {
  const preset = pythonPresets.get(event.target.value);
  if (!preset) return;
  byId("python-example-description").textContent = preset.description;
  activePythonInput = preset.input;
  if (preset.script) {
    byId("code").value = scriptExamples.get(preset.script);
  } else {
    byId("code").value = "";
  }
  byId("script-file").value = "";
  byId("script-input").value = "";
});
byId("script-input").addEventListener("change", event => {
  const [file] = event.target.files;
  const preset = pythonPresets.get(byId("python-example-preset").value);
  byId("python-example-description").textContent = file
    ? "Entrada própria selecionada; o script receberá esse arquivo."
    : preset?.description || "";
});
byId("script-file").addEventListener("change", async event => {
  const [file] = event.target.files;
  if (!file) return;
  if (file.size > 128_000) {
    event.target.value = "";
    showStatus("O script pode ter até 128 kB.", true);
    return;
  }
  try {
    byId("code").value = await file.text();
    showStatus("");
  } catch {
    showStatus("Falha ao ler o script.", true);
  }
});
function updateMethodFields() {
  const method = byId("method").value;
  byId("tier").disabled = method !== "full";
  byId("heuristic").disabled = method !== "heuristic";
}

byId("method").addEventListener("change", updateMethodFields);
updateMethodFields();

byId("python-form").addEventListener("submit", event => {
  event.preventDefault();
  const compare = event.submitter?.value === "compare";
  const method = byId("method").value === "full" ? byId("tier").value : byId("method").value;
  const progress = compare || ["small", "medium"].includes(method)
    ? "Executando. A primeira execução pode preparar os modelos locais."
    : "Executando o script no Bubblewrap.";
  execute("/api/python", progress, async () => {
    const [file] = byId("script-input").files;
    return {
      code: byId("code").value,
      input_example: activePythonInput,
      input: file ? await encodedFile(file) : null,
      method,
      heuristic: byId("heuristic").value,
      compare,
    };
  }, renderPython);
});

loadExample();
