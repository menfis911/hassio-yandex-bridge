ARG BUILD_ARCH
ARG BUILD_VERSION

FROM ghcr.io/home-assistant/base:3.24

ARG BUILD_ARCH
ARG BUILD_VERSION

RUN apk add --no-cache ca-certificates python3

COPY app/ /app/
COPY run.sh /run.sh
RUN chmod 0755 /run.sh

LABEL \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.version="${BUILD_VERSION}" \
    org.opencontainers.image.title="Yandex HA Bridge" \
    org.opencontainers.image.source="https://github.com/menfis911/hassio-yandex-bridge"

CMD ["/run.sh"]
