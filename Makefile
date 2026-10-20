.PHONY: test test-deployment test-vault
test: test-deployment test-vault
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
test-deployment:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s deploy/slim/tests -p 'test_*.py' -v
test-vault:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s deploy/slim-vault/tests -p 'test_*.py' -v
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s deploy/slim-vault/learning-loop/tests -p 'test_*.py' -v
