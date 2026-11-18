# This is a Dockerfile intended to be built using `docker buildx`
# for multi-arch support. Building with `docker build` may have unexpected results.

# This file assumes that the frontend has been built using ./scripts/frontend-build

ARG BASE_IMAGE=nginxproxymanager/nginx-full@sha256:e8971bb81500750b867e9800c0419c6d743d5c233f6781d65d03e8bad49da7eb
FROM nginxproxymanager/testca@sha256:872386a37de28a278782b9fa5b997d932bdb7b0b4b8974d54ba50ba92b3de767 AS testca
FROM $BASE_IMAGE

ARG TARGETPLATFORM
ARG BUILD_VERSION
ARG BUILD_COMMIT
ARG BUILD_DATE

# See: https://github.com/just-containers/s6-overlay/blob/master/README.md
ENV SUPPRESS_NO_CONFIG_WARNING=1 \
	S6_BEHAVIOUR_IF_STAGE2_FAILS=1 \
	S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
	S6_FIX_ATTRS_HIDDEN=1 \
	S6_KILL_FINISH_MAXTIME=10000 \
	S6_VERBOSITY=1 \
	NODE_ENV=production \
	NPM_BUILD_VERSION="${BUILD_VERSION}" \
	NPM_BUILD_COMMIT="${BUILD_COMMIT}" \
	NPM_BUILD_DATE="${BUILD_DATE}" \
	NODE_OPTIONS="--openssl-legacy-provider"

RUN echo "fs.file-max = 65535" > /etc/sysctl.conf \
	&& apt-get update \
	&& apt-get install -y --no-install-recommends jq logrotate \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# s6 overlay
COPY docker/scripts/install-s6 /tmp/install-s6
RUN printf '%s\n' '#!/bin/bash -e' '' '# Note: This script is designed to be run inside a Docker Build for a container' '' 'CYAN='"'"'\E[1;36m'"'"'' 'YELLOW='"'"'\E[1;33m'"'"'' 'BLUE='"'"'\E[1;34m'"'"'' 'GREEN='"'"'\E[1;32m'"'"'' 'RESET='"'"'\E[0m'"'"'' '' S6_OVERLAY_VERSION=3.2.3.2 'TARGETPLATFORM=${1:-linux/amd64}' '' '# Determine the correct binary file for the architecture given' 'case $TARGETPLATFORM in' '	linux/arm64)' '		S6_ARCH=aarch64' '		;;' '' '	*)' '		S6_ARCH=x86_64' '		;;' esac '' 'echo -e "${BLUE}❯ ${CYAN}Installing S6-overlay v${S6_OVERLAY_VERSION} for ${YELLOW}${TARGETPLATFORM} (${S6_ARCH})${RESET}"' '' 'curl -L -o '"'"'/tmp/s6-overlay-noarch.tar.xz'"'"' "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz"' 'curl -L -o "/tmp/s6-overlay-${S6_ARCH}.tar.xz" "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6_ARCH}.tar.xz"' 'printf '"'"'%s\n'"'"' '"'"'5379750ed30a84bbd2e2dd74847ba6b5bd29cd0b2e3ea2ec58049b57eb2eda12  /tmp/s6-overlay-noarch.tar.xz'"'"' '"'"'e6befcc96a437a3831386ecfc51808c5d3e939dc5fe3c02ae9284599e8aa2408  /tmp/s6-overlay-x86_64.tar.xz'"'"' | sha256sum -c -' 'tar -C / -Jxpf '"'"'/tmp/s6-overlay-noarch.tar.xz'"'"'' 'tar -C / -Jxpf "/tmp/s6-overlay-${S6_ARCH}.tar.xz"' '' 'rm -rf "/tmp/s6-overlay-${S6_ARCH}.tar.xz"' '' 'echo -e "${BLUE}❯ ${GREEN}S6-overlay install Complete${RESET}"' > /tmp/install-s6 && /tmp/install-s6 "${TARGETPLATFORM}" && rm -f /tmp/install-s6

EXPOSE 80 81 443

COPY backend       /app
COPY frontend/dist /app/frontend
COPY docker/rootfs /

# Copy test CA cert for use in container and add to trusted certs from a self-signed CA
COPY --from=testca /home/step/certs/root_ca.crt /etc/ssl/certs/NginxProxyManager.crt
WORKDIR /etc/ssl/certs
RUN ln -s NginxProxyManager.crt 1d0e3f10.0 && update-ca-certificates

WORKDIR /app
RUN yarn install --frozen-lockfile \
	&& yarn cache clean

# Remove frontend service not required for prod, dev nginx config as well
RUN rm -rf /etc/s6-overlay/s6-rc.d/user/contents.d/frontend /etc/nginx/conf.d/dev.conf \
	&& chmod 644 /etc/logrotate.d/nginx-proxy-manager

VOLUME [ "/data" ]
ENTRYPOINT [ "/init" ]

LABEL org.label-schema.schema-version="1.0" \
	org.label-schema.license="MIT" \
	org.label-schema.name="nginx-proxy-manager" \
	org.label-schema.description="Docker container for managing Nginx proxy hosts with a simple, powerful interface " \
	org.label-schema.url="https://github.com/jc21/nginx-proxy-manager" \
	org.label-schema.vcs-url="https://github.com/jc21/nginx-proxy-manager.git" \
	org.label-schema.cmd="docker run --rm -ti jc21/nginx-proxy-manager:latest"
