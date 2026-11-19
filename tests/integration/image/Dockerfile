# Both Checkmk versions on Debian 12, from the packages in the build context
# (checkmk_site.py): mounted, not copied, so that the image holds no second copy.
# No site yet: the tests create one per container and version.
FROM docker.io/library/debian:bookworm-slim
RUN --mount=type=bind,target=/tmp/packages \
    apt-get update -qq \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends /tmp/packages/*.deb > /dev/null \
 && rm -rf /var/lib/apt/lists/*
