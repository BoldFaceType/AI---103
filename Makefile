PYTHON = python

.PHONY: init run test clean

init:
	$(PYTHON) scripts/orchestrator.py --init

run:
	$(PYTHON) scripts/orchestrator.py

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf scripts/__pycache__ tests/__pycache__ .pytest_cache
	find state/sessions -name "*.json" -delete 2>/dev/null || true
	find state/tasks/todo -name "*.json" -delete 2>/dev/null || true
	find _meta -name "*.json" -o -name "audit.log" 2>/dev/null | xargs rm -f || true
	$(PYTHON) -c "p='logs/events.ndjson'; open(p,'w').close() if __import__('os').path.exists(p) else None"
