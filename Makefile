.PHONY: test

test:
	. venv/bin/activate; nosetests --rednose --with-cov --cov-config=.coveragerc

upload:
	. venv/bin/activate; git tag -a v$(shell python -c "import tornwrap;print tornwrap.version;") -m ""
	. venv/bin/activate; git push origin v$(shell python -c "import tornwrap;print tornwrap.version;")
	. venv/bin/activate; python setup.py sdist upload
