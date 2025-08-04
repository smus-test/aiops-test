FROM --platform=linux/amd64 amazonlinux:2 AS build_image
ARG version=2.49.0
ARG GH_VERSION=2.65.0

# Essential build requirements
RUN yum install -y \
    autoconf \
    curl-devel \
    expat-devel \
    gettext-devel \
    openssl-devel \
    perl-devel \
    zlib-devel \
    make \
    gcc \
    tar \
    wget \
    perl

# Remove existing git
RUN yum remove git -y
RUN rm -rf /bin/git /usr/libexec/git-core

# Download source
RUN wget https://github.com/git/git/archive/v${version}.tar.gz 
RUN tar xvzf v${version}.tar.gz -C /tmp

RUN mkdir /git

WORKDIR /tmp/git-${version}

# Build with minimal features
RUN make configure
RUN ./configure prefix="/git" \
    --without-tcltk \
    --without-python \
    CFLAGS="-Os -s -DNDEBUG" \
    LDFLAGS="-s" \
    NO_GETTEXT=1 \
    NO_PYTHON=1 \
    NO_TCLTK=1 \
    NO_SVN_TESTS=1 \
    NO_INSTALL_HARDLINKS=1

RUN make -j$(nproc) strip
RUN make install

WORKDIR /
RUN mkdir -p /layer/gh && \
    wget https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz && \
    tar xzf gh_${GH_VERSION}_linux_amd64.tar.gz && \
    cp gh_${GH_VERSION}_linux_amd64/bin/gh /layer/gh/ && \
    rm -rf gh_${GH_VERSION}_linux_amd64*

# Create minimal layer with only necessary commands
# Create layer structure directly (without 'opt' parent)
RUN mkdir -p /layer/git/bin /layer/git/lib/git-core && \
    # Copy main git binary
    cp /git/bin/git /layer/git/bin/ && \
    # Copy only essential git-core commands
    for cmd in git-remote-https git-clone git-push git-config git-init git-add git-commit; do \
        if [ -f "/git/libexec/git-core/$cmd" ]; then \
            cp "/git/libexec/git-core/$cmd" /layer/git/lib/git-core/; \
        fi \
    done && \
    # Copy required shared libraries
    for bin in $(find /layer/git -type f -executable); do \
        for lib in $(ldd $bin 2>/dev/null | grep "=> /" | awk '{print $3}'); do \
            cp -L $lib /layer/git/lib/ 2>/dev/null || true; \
        done; \
    done && \
    # Strip all binaries
    strip /layer/git/bin/* /layer/git/lib/git-core/*

# Show size of final layer
RUN du -sh /layer/git/* /layer/gh/*

# Create archive from layer directory
RUN cd /layer && tar -czf /tmp/git.tar.gz .

CMD cp /tmp/git.tar.gz /output/