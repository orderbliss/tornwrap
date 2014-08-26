.PHONY: test

test:
	. venv/bin/activate; nosetests --rednose --with-cov --cov-config=.coveragerc

upload:
	python setup.py sdist upload
