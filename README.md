# vcpkg-ci-build

GitHub Actions workflow for running `vcpkg ci` across the triplets currently covered by
vcpkg's official CI and collecting each triplet's output in a `failures/<triplet>`
directory that is uploaded as an artifact.
