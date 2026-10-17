.PHONY: install run test check
install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
test:
	python -m pytest -q
check:
	python -m compileall -q app tests
