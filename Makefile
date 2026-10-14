PYTHON ?= python
T ?=

.PHONY: install demo test check

install:
	$(PYTHON) -m pip install -r requirements.txt

demo:
	$(PYTHON) -m verifier demo

test:
	$(PYTHON) -m pytest -q

check:
	$(PYTHON) -m verifier check $(T) --adapter adapters/mock.yaml
