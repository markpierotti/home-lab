.PHONY: test test-deployment
test: test-deployment
test-deployment:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s deploy/slim/tests -p 'test_*.py' -v
