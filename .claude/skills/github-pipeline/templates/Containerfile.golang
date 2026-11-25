# Go image. The build stage compiles a static binary. The final image
# holds the binary and the CA certificates, and nothing else.
# Change cmd/NAME to the main package, and COPY to the directories the
# build needs. make image passes GO_IMAGE when the Makefile sets
# IMAGE_BUILD_ARGS. Set SMOKE_ARGS=--help, or another harmless argument,
# so make image-ci can run the image.
ARG GO_IMAGE=docker.io/library/golang:1.25-bookworm

FROM ${GO_IMAGE} AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download
COPY cmd/ cmd/
COPY internal/ internal/
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/app ./cmd/NAME

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /out/app /app
USER 65534:65534
ENTRYPOINT ["/app"]
