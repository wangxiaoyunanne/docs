# Gunrock Release Notes

Gunrock release 0.5 is a feature (minor) release that adds:

- New primitives and better support for existing primitives.
- New operator: Intersection.
- Unit-testing support through [Googletest ](https://github.com/google/googletest) infrastructure.
- CPU reference code for correctness checking for some of the primitives.
- Support for central integration (Jenkins) and code-coverage.
- Overall bug fixes and support for new CUDA architectures.

## v0.5 Changelog
All notable changes to gunrock for v0.5 are documented below:

### Added
- New primitives:
    - A* 
    - Weighted Label Propagation (LP) 
    - Minimum Spanning Tree (MST)
    - Random Walk (RW)
    - Triangle Counting (TC)
- Operator:
    - Intersection operator (for example, see TC)
- Unit-testing:
    - Googletest support (see `unittests` directory)
- Docs
    - Support using Slate (see https://github.com/gunrock/docs)
- CPU reference code
- Run scripts for all primitives
- Clang-format based on Google style
    - see commit aac9add (revert for diff)
- Support for Volta and Turing architectures
- Regression tests to `ctest` for better code-coverage
- Memset kernels
- Multi-gpu testing through Jenkins

### Removed
- Subgraph matching and join operator removed due to race conditions (SM is not added to the future release)
- Plots generation python scripts removed (see https://github.com/gunrock/io)
- MaxFlow primitive removed, wasn't fully implemented for a release (implementation exists in the new API for future release)
- Outdated documentation


### Fixed
- HITS now produces correct results
- Illegal memory access fixed for label propagation (LP) primitive
- WTF Illegal memory access fixed for frontier queue (see known issues for problems with this)
- Other minor bug fixes

### Changed
- Updated README and other docs
- Moved previously `tests` directory to `examples`
- Doesn't require `CMakeLists.txt` (or `cmake`) to run `make`
- Moved all docs to Slate

## Known Issues:
- WTF has illegal memory access (https://github.com/gunrock/gunrock/issues/503).
- A* sometimes outputs the wrong path randomly (https://github.com/gunrock/gunrock/issues/502).
- Random Walk uses custom kernels within gunrock, this is resolved for future releases.
- CPU Reference code not implemented for SALSA, TC and LP (https://github.com/gunrock/gunrock/issues/232).
