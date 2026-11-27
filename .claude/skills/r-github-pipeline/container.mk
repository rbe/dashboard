# The image targets of a project that delivers a container image.
# sdlc.mk includes project.mk of r-project-setup, then this file.
# templates/Makefile.image shows the settings a project adds.
#
# The language does not matter here. The Containerfile builds the image.
# BUILD_CMD names the language build and then runs `make image-ci`:
#
#   BUILD_CMD = true && $(MAKE) --no-print-directory image-ci
#
# Set before the include:
#   OWNER         GitHub owner. Default: the owner in the URL of the git
#                 remote origin, in lower case. IMAGE defaults to
#                 ghcr.io/OWNER/NAME
#   NAME          image name. Default: the repository name in the URL of
#                 the git remote origin, else the name of the directory
#   IMAGE         ghcr.io/owner/name, no tag. Replaces OWNER and NAME
#   CONTAINERFILE default Containerfile
#   IMAGE_BUILD_ARGS  extra podman build arguments, such as --build-arg X=Y
#   SMOKE_CMD     the one check that the image runs. Default: run the
#                 image with SMOKE_ARGS. A non-zero exit fails build
#   SMOKE_ARGS    arguments of that run, such as --help
#   IMAGE_CONTEXT the build context. Default: .
#   IMAGE_PREPARE shell commands that run before the image build, such as
#                 a copy of the tested artifact into the context
#   PLATFORMS     platforms of the published image. Default
#                 linux/amd64,linux/arm64. Empty: publish the single-arch
#                 image of the build job, as before
#   PUBLISH_PREPARE  shell commands that run before publish-container
#                 pushes. Default: load the saved tar when the image is
#                 not in the local store
#
# What is built where. image and image-ci build one image for the native
# platform, run the smoke check on it, and save the tar. The build job
# tests that image. When PLATFORMS is not empty, publish-container does
# not push that image. It runs IMAGE_PREPARE, builds a manifest list for
# PLATFORMS from IMAGE_CONTEXT with CONTAINERFILE and IMAGE_BUILD_ARGS,
# and pushes it with `podman manifest push --all`, so the published image
# is rebuilt for PLATFORMS at publish time. The version label is the
# publish version. With more than one platform, publish-container first
# runs multiarch-host. On Linux it installs qemu-user-static when the
# kernel has no binfmt entry for a foreign platform. On macOS the Podman
# machine needs nothing. A missing tool stops the target with its name.
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef CONTAINER_MK
CONTAINER_MK := 1

# NAME comes from tools.mk, which project.mk includes before this file.
OWNER ?= $(shell git remote get-url origin 2>/dev/null | sed -n 's|.*github\.com[:/]\([^/]*\)/.*|\1|p' | tr 'A-Z' 'a-z')
IMAGE ?= ghcr.io/$(OWNER)/$(NAME)
CI_IMAGE ?= localhost/$(NAME):ci
CONTAINERFILE ?= Containerfile
IMAGE_BUILD_ARGS ?=
SMOKE_ARGS ?=
SMOKE_CMD ?= podman run --rm "$(CI_IMAGE)" $(SMOKE_ARGS)
IMAGE_CONTEXT ?= .
IMAGE_PREPARE ?= true
PLATFORMS ?= linux/amd64,linux/arm64
MULTIARCH_PACKAGES ?= qemu-user-static binfmt-support
PUBLISH_PREPARE ?= if ! podman image inspect "$(CI_IMAGE)" >/dev/null 2>&1; then \
	  test -f "build/image/$(NAME)-image.tar"; \
	  podman load -i "build/image/$(NAME)-image.tar"; \
	fi

.PHONY: image image-ci publish-container multiarch-host

# help-group: Delivery
image: ## Build the image
	@set -eu; \
	case "$(IMAGE)" in \
	  ghcr.io//*|"") printf '%s\n' "image: set OWNER (the GitHub owner) or IMAGE before the include." >&2; exit 1 ;; \
	esac; \
	$(IMAGE_PREPARE); \
	podman build $(PODMAN_NET_ARGS) -f "$(CONTAINERFILE)" $(IMAGE_BUILD_ARGS) \
		--label org.opencontainers.image.source="https://github.com/$(PACKAGE)" \
		--label org.opencontainers.image.revision="$(or $(GITHUB_SHA),local)" \
		--label org.opencontainers.image.version="$(or $(GITHUB_RUN_NUMBER),local)" \
		-t "$(IMAGE)" -t "$(CI_IMAGE)" "$(IMAGE_CONTEXT)"

image-ci: ## Build the image, run the smoke check, save the image tar
	@set -eu; \
	$(THIS_MAKE) --no-print-directory image; \
	$(SMOKE_CMD); \
	mkdir -p build/image build/summaries; \
	rm -f "build/image/$(NAME)-image.tar"; \
	podman save -o "build/image/$(NAME)-image.tar" "$(CI_IMAGE)"; \
	printf '# build\n\nImage %s saved.\n' "$(CI_IMAGE)" > build/summaries/build.md

publish-container: ## Match CI: push the version, and latest on the default branch
	@$(call SDLC_LOG,publish-container,_publish-container)

# help-group: Delivery
multiarch-host: ## Make the host able to build the foreign platforms of PLATFORMS
	@set -eu; \
	[ "$$(uname -s)" = Linux ] || exit 0; \
	arch=$$(uname -m); \
	need=""; \
	for p in $$(printf '%s' "$(PLATFORMS)" | tr ',' ' '); do \
	  case "$$p" in \
	    linux/amd64) [ "$$arch" = x86_64 ] || need="$$need x86_64" ;; \
	    linux/arm64) case "$$arch" in aarch64|arm64) ;; *) need="$$need aarch64" ;; esac ;; \
	    *) need="$$need $${p#linux/}" ;; \
	  esac; \
	done; \
	missing=""; \
	for a in $$need; do \
	  [ -e "/proc/sys/fs/binfmt_misc/qemu-$$a" ] || missing="$$missing $$a"; \
	done; \
	[ -n "$$missing" ] || exit 0; \
	if command -v sudo >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1; then \
	  sudo apt-get update; \
	  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $(MULTIARCH_PACKAGES); \
	else \
	  printf '%s\n' "multiarch-host: no qemu binfmt entry for$$missing. Install $(MULTIARCH_PACKAGES), or set PLATFORMS= for a single-arch publish." >&2; \
	  exit 1; \
	fi; \
	for a in $$missing; do \
	  [ -e "/proc/sys/fs/binfmt_misc/qemu-$$a" ] || { printf '%s\n' "multiarch-host: qemu-$$a is still not registered in binfmt_misc after the install. Register it, for example with the package binfmt-support." >&2; exit 1; }; \
	done

_publish-container:
	@set -eu; \
	version=$$($(THIS_MAKE) -s --no-print-directory version); \
	mkdir -p build build/summaries; \
	printf '%s\n' "$$version" > build/publish-version.txt; \
	platforms="$(strip $(PLATFORMS))"; \
	if [ -n "$$platforms" ]; then \
	  case "$$platforms" in *,*) $(THIS_MAKE) --no-print-directory multiarch-host ;; esac; \
	  $(IMAGE_PREPARE); \
	  manifest="localhost/$(NAME):publish"; \
	  podman manifest rm "$$manifest" >/dev/null 2>&1 || true; \
	  podman rmi "$$manifest" >/dev/null 2>&1 || true; \
	  podman build $(PODMAN_NET_ARGS) --platform "$$platforms" --manifest "$$manifest" -f "$(CONTAINERFILE)" $(IMAGE_BUILD_ARGS) \
	    --label org.opencontainers.image.source="https://github.com/$(PACKAGE)" \
	    --label org.opencontainers.image.revision="$(or $(GITHUB_SHA),local)" \
	    --label org.opencontainers.image.version="$$version" \
	    "$(IMAGE_CONTEXT)"; \
	else \
	  $(PUBLISH_PREPARE); \
	fi; \
	tags=$$($(THIS_MAKE) -s --no-print-directory publish-tags); \
	for tag in $$tags; do \
	  if [ -n "$$platforms" ]; then podman manifest push --all "$$manifest" "$(IMAGE):$$tag"; \
	  else podman tag "$(CI_IMAGE)" "$(IMAGE):$$tag"; podman push "$(IMAGE):$$tag"; fi; \
	done; \
	shown=$$(printf '%s\n' "$$tags" | sed 's/^/- /'); \
	printf '# publish-container\n\nStatus: pushed\nImage: %s\nPlatforms: %s\nTags:\n%s\n' "$(IMAGE)" "$${platforms:-native}" "$$shown" > build/summaries/publish-container.md

endif
