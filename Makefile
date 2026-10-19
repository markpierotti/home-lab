.PHONY: test test-deployment
test: test-deployment
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
test-deployment:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s deploy/slim/tests -p 'test_*.py' -v
