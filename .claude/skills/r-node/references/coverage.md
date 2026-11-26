# Coverage and changed tests in a Node project

## What `make coverage` does

1. It runs the lcov or Cobertura output of the test runner through diff-cover.
2. It runs the tests with `NODE_V8_COVERAGE` set to `build/coverage/v8`.
3. It runs `node_cover_map.py` from `r-project-report`. That script writes the coverage map: each test file, and the project files that ran in its process.

`make coverage` and `make test-changed` fail until the first unit test exists.

## What `make test-changed` does

`make test-changed` gives the test files that `changed_tests.py --print` names to the test runner.

## Test runners

- `node --test` and Jest: the coverage map is exact.
- A runner that shares one process between test files: `make test-changed` selects more tests, never fewer.
- Vitest: the workers of Vitest write no V8 coverage. Do these 3 things:
  1. Leave the map step out of `coverage`.
  2. Set the Makefile variable `TEST_CHANGED_CMD` to the value `vitest related --run` with the files in `build/coverage/changed.txt`. Vitest then selects the tests from its module graph.
  3. Ask `r-record` where that choice goes, as a requirement row or an ADR.
