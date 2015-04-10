DOCS_MAKE_CMD = html dirhtml latex latexpdf

.PHONY: $(DOCS_MAKE_CMD) docs clean test coverage

docs: $(DOCS_MAKE_CMD)

$(DOCS_MAKE_CMD):
	DJANGO_SETTINGS_MODULE=test_proj.settings $(MAKE) -C docs $@

clean: docs_clean
	$(MAKE) -C docs clean

test:
	tox

coverage:
	coverage run --source='.' test_proj/runtests.py
	coverage html --include="django_states*" --omit="*test*" --directory=.direnv/htmlcov
	coverage report --include="django_states*" --omit="*test*"
