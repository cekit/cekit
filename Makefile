test: prepare
	tox -- tests

test-py36: prepare
	tox -e py36 -- tests

test-py37: prepare
	tox -e py37 -- tests

test-py38: prepare
	tox -e py38 -- tests

test-py39: prepare
	tox -e py39 -- tests

test-py310: prepare
	tox -e py310 -- tests

test-py311: prepare
	tox -e py311 -- tests

clean:
	@find . -name "*.pyc" -exec rm -rf {} \;
	@rm -rf target

prepare: clean
	@mkdir target

release: clean
	git checkout develop
	git reset --hard origin/develop
	prerelease

	git checkout main
	git reset --hard origin/main
	git merge develop -X theirs --message "Merging develop branch"
	release -v
	git push

	git checkout develop
	postrelease -v --feature
