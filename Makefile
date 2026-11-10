PYTHON ?= .venv/bin/python

.PHONY: test integration doctor demo security
test:
	$(PYTHON) -m pytest -q

integration:
	SENTINELA_INTEGRATION=1 $(PYTHON) -m pytest -q

doctor:
	$(PYTHON) -m sentinela.cli doctor

demo:
	$(PYTHON) -m sentinela.cli run examples/analisar.py --input examples/entrada.csv --output demo-output --method supervised

security:
	$(PYTHON) -m sentinela.cli security
