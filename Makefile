.PHONY: test

test:
	. venv/bin/activate; nosetests --rednose --with-cov --cov-config=.coveragerc
