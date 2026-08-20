# Thin provenance wrapper. Never rebuilds the SGLang runtime (see
# runtime/image-provenance.json for the pinned base). FROM carries the
# registry-pinned arm64 manifest digest of the day-0 Lightning image.
FROM lmsysorg/sglang:dev-nemotron3-5-lightning@sha256:6da24ff76c85cf49276c010f8fff4cf88ed668e560b2967629549105e7107e62

ARG REVISION=unknown

LABEL org.opencontainers.image.title="nemotron-3.5-lightning-sglang-dflash-sm121"
LABEL org.opencontainers.image.description="SGLang SM121 serve cell: NVIDIA Nemotron 3.5 Lightning 30B-A3B NVFP4 + official DFlash draft head"
LABEL org.opencontainers.image.source="https://github.com/r0b0tlab/nemotron-3.5-lightning-sglang-dflash-sm121"
LABEL org.opencontainers.image.revision="$REVISION"
LABEL org.opencontainers.image.base.digest="sha256:6da24ff76c85cf49276c010f8fff4cf88ed668e560b2967629549105e7107e62"
LABEL org.opencontainers.image.licenses="MIT"

COPY runtime/entrypoint.sh /usr/local/bin/entrypoint
COPY scripts/wait_ready.sh /usr/local/bin/wait_ready
RUN chmod +x /usr/local/bin/entrypoint /usr/local/bin/wait_ready \
 && sha256sum /usr/local/bin/entrypoint /usr/local/bin/wait_ready > /usr/local/bin/manifest.sha256

ENV MODEL_DIR=/models/target DRAFT_DIR=/models/draft PROFILE=production PORT=30000
ENTRYPOINT ["/usr/local/bin/entrypoint"]
