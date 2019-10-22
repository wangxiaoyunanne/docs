# Gunrock's Release

We follow the versioning semantics proposed by Tom Preston-Werner (https://semver.org/), and therefore consider the following types of releases:

- Major release
- Minor release
- Patch release

## Release Checklist

1. Switch to development branch: `git checkout dev`
2. Update gunrock's version in [CMakeLists](https://github.com/gunrock/gunrock/blob/master/CMakeLists.txt#L3-L5) and [BaseMakefile](https://github.com/gunrock/gunrock/blob/master/examples/BaseMakefile.mk)
3. (Optional) Update the [JSON schema version](https://github.com/gunrock/gunrock/blob/master/gunrock/util/info_rapidjson.cuh#L220-L221) by changing it to the present date. Only update if any changes were made to the JSON structure
4. Resolve any conflicts between the `master` and the `dev` branch
5. Commit all changes to `dev`, check with githb to see if the build (and code coverage) for the commits passed
6. Create a `pre-release` branch from the `dev` branch to publish changes to: `git branch pre-release`
7. (Optional) Within the `pre-release` branch you can choose to remove code that is not ready for release and therefore should just stay in the `dev` branch
8. Commit all changes after removing the development code from the `pre-release` branch, and create a "ready for release" github pull request from `pre-release` to `master`
9. If all builds (and code coverage) for `pre-release` to `master` pass, merge the pull request
10. [Draft a new release](https://github.com/gunrock/gunrock/releases) on github, following the versioning semantics
11. Add an in-depth change-log, using the exisiting examples for [major](https://github.com/gunrock/gunrock/releases/tag/v1.0), [minor](https://github.com/gunrock/gunrock/releases/tag/v1.1) or [patch](https://github.com/gunrock/gunrock/releases/tag/v0.5.1) release
