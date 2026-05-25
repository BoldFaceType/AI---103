PYTHON = python

# log-quiz usage: make log-quiz SCORE=0.72 CONCEPT=vision-services [ID=my-id]
SCORE   ?= 0.0
CONCEPT ?= vision-services
ID      ?=

.PHONY: init run test clean status log-quiz

init:
	$(PYTHON) scripts/orchestrator.py --init

run:
	$(PYTHON) scripts/orchestrator.py

test:
	$(PYTHON) -m pytest tests/ -v

status:
	@$(PYTHON) -c "\
import json, sys; \
from pathlib import Path; \
root = Path('.'); \
km = json.loads((root/'state/learner/knowledge-map.json').read_text()); \
tasks = list((root/'state/tasks/todo').glob('*.json')); \
meta = json.loads((root/'state/learner/meta.json').read_text()); \
habits = json.loads((root/'state/learner/habits.json').read_text()); \
print('\n=== Knowledge Map ==='); \
[print(f'  {c:<22} mastery={v[\"mastery\"]:.0%}  [' + '#'*int(v['mastery']*10) + '.'*(10-int(v['mastery']*10)) + f']  confidence={v[\"confidence\"]:.0%}') for c,v in sorted(km.items(), key=lambda x: x[1]['mastery'])]; \
print(f'\n=== Todo Tasks ({len(tasks)}) ==='); \
[print(f'  {json.loads(t.read_text())[\"objective_ids\"]} — {json.loads(t.read_text())[\"estimated_minutes\"]}m') for t in tasks] or print('  none'); \
print(f'\n=== Habits ==='); \
print(f'  quizzes logged: {habits.get(\"quiz_count\",0)}'); \
print(f'  last quiz:      {habits.get(\"last_quiz_ts\") or \"never\"}'); \
print(f'  events processed: {len(meta.get(\"processed_event_ids\",[]))}'); \
print(); \
"

log-quiz:
	@$(PYTHON) -c "\
import json, sys, uuid; \
from datetime import datetime, timezone; \
from pathlib import Path; \
score = float('$(SCORE)'); \
concept = '$(CONCEPT)'; \
eid = '$(ID)' or 'quiz-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); \
event = {'ts': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'), 'type': 'quiz_completed', 'event_id': eid, 'score': score, 'concepts': [concept]}; \
p = Path('logs/events.ndjson'); \
p.parent.mkdir(parents=True, exist_ok=True); \
existing = p.read_text(encoding='utf-8') if p.exists() else ''; \
p.write_text(existing + json.dumps(event, sort_keys=True) + '\n', encoding='utf-8'); \
print(f'Logged: {concept} score={score:.0%}  id={eid}'); \
"

clean:
	rm -rf scripts/__pycache__ tests/__pycache__ .pytest_cache
	find state/sessions -name "*.json" -delete 2>/dev/null || true
	find state/tasks/todo -name "*.json" -delete 2>/dev/null || true
	find _meta -name "*.json" -o -name "audit.log" 2>/dev/null | xargs rm -f || true
	$(PYTHON) -c "p='logs/events.ndjson'; open(p,'w').close() if __import__('os').path.exists(p) else None"
