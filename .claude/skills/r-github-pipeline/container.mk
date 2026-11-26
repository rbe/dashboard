# The image targets of a project that delivers a container image.
# sdlc.mk includes this file and the contract targets of r-project-setup.
# The Node and Gradle makefiles of this skill use these targets too.
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
#   PUBLISH_PREPARE  shell commands that run before publish-container
#                 pushes. Default: load the saved tar when the image is
#                 not in the local store
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef CONTAINER_MK
CONTAINER_MK := 1

# NAME comes from tools.mk, which sdlc.mk includes first.
OWNER ?= $(shell git remote get-url origin 2>/dev/null | sed -n 's|.*github\.com[:/]\([^/]*\)/.*|\1|p' | tr 'A-Z' 'a-z')
IMAGE ?= ghcr.io/$(OWNER)/$(NAME)
CI_IMAGE ?= localhost/$(NAME):ci
CONTAINERFILE ?= Containerfile
IMAGE_BUILD_ARGS ?=
SMOKE_ARGS ?=
SMOKE_CMD ?= podman run --rm "$(CI_IMAGE)" $(SMOKE_ARGS)
IMAGE_CONTEXT ?= .
IMAGE_PREPARE ?= true
PUBLISH_PREPARE ?= if ! podman image inspect "$(CI_IMAGE)" >/dev/null 2>&1; then \
	  test -f "build/image/$(NAME)-image.tar"; \
	  podman load -i "build/image/$(NAME)-image.tar"; \
	fi

.PHONY: image image-ci publish-container

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

_publish-container:
	@set -eu; \
	$(PUBLISH_PREPARE); \
	version=$$($(THIS_MAKE) -s --no-print-directory version); \
	mkdir -p build build/summaries; \
	printf '%s\n' "$$version" > build/publish-version.txt; \
	tags=$$($(THIS_MAKE) -s --no-print-directory publish-tags); \
	for tag in $$tags; do \
	  podman tag "$(CI_IMAGE)" "$(IMAGE):$$tag"; \
	  podman push "$(IMAGE):$$tag"; \
	done; \
	shown=$$(printf '%s\n' "$$tags" | sed 's/^/- /'); \
	printf '# publish-container\n\nStatus: pushed\nImage: %s\nTags:\n%s\n' "$(IMAGE)" "$$shown" > build/summaries/publish-container.md

endif
