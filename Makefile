test: prepare
	tox -- tests

test-py37: prepare
	tox -e py37 -- tests

test-py38: prepare
	tox -e py38 -- tests

test-py39: prepare
	tox -e py39 -- tests

test-py310: prepare
	tox -e py310 -- tests

test-unit: prepare
	tox -- tests/test_unit*

test-integ: prepare
	tox -- tests/test_integ*

ci-publish-junit:
	@mkdir -p ${CIRCLE_TEST_REPORTS}
	@cp target/junit*.xml ${CIRCLE_TEST_REPORTS}

clean:
	@find . -name "*.pyc" -exec rm -rf {} \;
	@rm -rf target
	@rm -rf dist

prepare: clean
	@mkdir target

hook-gitter:
	@curl -s -X POST -H "Content-Type: application/json" -d "{\"payload\":`curl -s -H "Accept: application/json" https://circleci.com/api/v1/project/goldmann/docker-scripts/${CIRCLE_BUILD_NUM}`}" ${GITTER_WEBHOOK_URL}

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
	postrelease -v
