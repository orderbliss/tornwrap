.PHONY: test

test:
	. venv/bin/activate; nosetests --rednose --with-cov --cov-config=.coveragerc

deploy:
	git tag -a v$(shell python -c "import tornwrap;print tornwrap.version;") -m ""
	git push origin v$(shell python -c "import tornwrap;print tornwrap.version;")
	python setup.py sdist upload
