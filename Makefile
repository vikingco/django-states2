DOCS_MAKE_CMD = html dirhtml latex latexpdf

.PHONY: $(DOCS_MAKE_CMD) docs clean

docs: $(DOCS_MAKE_CMD)

$(DOCS_MAKE_CMD):
	DJANGO_SETTINGS_MODULE=test_proj.settings $(MAKE) -C docs $@

clean:
	$(MAKE) -C docs clean
