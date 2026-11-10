# 构建阶段：工具链版本锁定，见附录 A
FROM --platform=$BUILDPLATFORM golang:1.23-bookworm AS builder
WORKDIR /src
COPY go.mod ./
COPY cmd/gateway/main.go ./cmd/gateway/
ARG TARGETOS
ARG TARGETARCH
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH \
    go build -trimpath -ldflags="-s -w" -o /out/gateway ./cmd/gateway

# 运行阶段：非 root、无 shell、无包管理器
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/gateway /gateway
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/gateway"]
