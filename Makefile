#################################################
#### Automatic Pythonic Developer Experience ####
#################################################
## For why this exists and how it works from a very high level.
##
## If you don't really know what to do, run `make help`.
##
## If you don't have make installed,
## On macOS, run `xcode-select --install` to get a BSD make.
## On Linux, install make through your package manager.
##     N.b. this isn't really setup for Linux, but probably works.
##
## Run `make install-homebrew` to install Homebrew if 'brew' isn't available.
## Run `make deps` to install everything else, run it until it succeeds, generally 2–3x.
## READ OUTPUT CAREFULLY.

## Source location
MODULE_BASE_DIR = src/pyQBnk
TESTS_BASE_DIR = tests

## Set this variable to any value to disable installing pre-commit git hooks
## It can also be passed with `make deps DEPS_NO_PRECOMMIT=1` to disable for one `deps` task run.
## Disable pre-commit hooks only if you accept the massive tech debt doing so may cause.
# DEPS_NO_PRECOMMIT = true

# Set a default target
.DEFAULT_GOAL := help

## Pythonic variables
# These are set to determine some version information and normal paths to tooling.
# Python installation artifacts
PYTHON_VERSION_FILE=.python-version
PYTHON_VERSION_FIRST_LISTED=$(shell head -n 1 $(PYTHON_VERSION_FILE))
ifeq ("$(shell which pyenv)","")
# pyenv isn't installed, guess the path
PYENV_VERSION_DIR ?= $(HOME)/.pyenv/versions/$(PYTHON_VERSION_FIRST_LISTED)
PYTHON_EXEC ?= python3
else
# pyenv is installed
PYENV_VERSION_DIR ?= $(shell pyenv root)/versions/$(PYTHON_VERSION_FIRST_LISTED)
# use just the first
PYTHON_EXEC ?= $(shell pyenv prefix | cut -d: -f1)/bin/python3
endif
POETRY_PATH = $(shell command -v poetry)
ifeq ("$(POETRY_PATH)","")
# poetry is not installed
POETRY_TASK = install-poetry
else
# poetry is installed
POETRY_TASK =
endif

## Python sdist package build flags
# Some Python packages might need to be built from source.
# Those packages may need special flags set, so do that here.
# Common ones are included here already somehow.
# If we're on macos arm64, we might to need to build some packages,
# so set flags appropriately.
FLAGS ?=
ifeq ($(shell uname -m), arm64)
ifeq ($(shell uname -s), Darwin)
# LIBS = odbc libiodbc
F_LDFLAGS = # LDFLAGS="$(shell pkg-config --libs $(LIBS))"
F_CPPFLAGS = # CPPFLAGS="$(shell pkg-config --cflags $(LIBS))"
FLAGS ?= $(F_LDFLAGS) $(F_CPPFLAGS)
endif
endif

## List of programs
# It's a good idea to avoid hardcoding tool executables in a Makefile.
# Setting them with ?= enables override, e.g. `make deps PYENV=path/to/dev/pyenv`
PYENV ?= pyenv
CURRENT_PYTHON ?= python3
POETRY ?= $(FLAGS) poetry
# Use what's provided via poetry if it's declared
ifeq ("$(shell grep '^pre-commit' pyproject.toml >/dev/null && echo 1)","1")
# Switch to this to use Homebrew's pre-commit, which is updated more frequently.
# ifeq ("$(shell command -v pre-commit)","")
PRECOMMIT ?= $(POETRY) run pre-commit
else
PRECOMMIT ?= pre-commit
endif
RUFF ?= $(POETRY) run ruff
MYPY ?= $(POETRY) run mypy
PYTEST ?= $(POETRY) run pytest
PDOC ?= $(POETRY) run pdoc
### Self-contained JAVA_HOME
## This is use for pytest so it can run pyspark tests, which require a JDK.
## Query the OS JDK management system for a JDK with this version.
#JAVA_VERSION ?= 17
## Set JAVA_HOME for the rest of the Make session
#MACOS_JAVA_TOOL = /usr/libexec/java_home
#MACOS_JVM_RES = (test -x $(MACOS_JAVA_TOOL) && $(MACOS_JAVA_TOOL) -v $(JAVA_VERSION))
#BREW_JVM_RES = (command -v brew > /dev/null && brew --prefix openjdk@$(JAVA_VERSION))
#DEB_JVM_RES = (test -d /usr/lib/jvm && (ls /usr/lib/jvm/java-$(JAVA_VERSION)-*-$$(dpkg --print-architecture) | sort -V | tail -n 1))
#JAVA_HOME ?= $(shell $(MACOS_JVM_RES) || $(BREW_JVM_RES) || $(DEB_JVM_RES) || echo '$${JAVA_HOME}')
## To override the JDK used for pytest's pyspark tests, set PYSPARK_JAVA_HOME.
## E.g. place this into your .zshrc or .bashrc:
##     export PRZ_PYSPARK_JAVA_HOME="${JAVA_HOME}"
## Redefine PYTEST to prepend the JAVA_HOME envvar.
#PYTEST := JAVA_HOME="$${PRZ_PYSPARK_JAVA_HOME:-$(JAVA_HOME)}" $(PYTEST)

###
### TASKS
###

##@ Utility

.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: debug-make
debug-make: ## Shows ~all runtime-set variables
	@echo $(foreach v, $(.VARIABLES), $(info $(v) = $($(v))))


##@ Development

.PHONY: test
test: test-unittests ## Run required tests
	@echo "$(COLOR_GREEN)$(MAKECMDGOALS) succeeded$(COLOR_RESET)"

.PHONY: test-all
test-all: test-unittests test-integration  ## Run all tests
	@echo "$(COLOR_GREEN)$(MAKECMDGOALS) succeeded$(COLOR_RESET)"

# If you mark tests, you can switch to using the marks by swapping the
# commented lines in the next two tasks.

.PHONY: test-unittests
test-unittests: ## Run unit tests
	$(PYTEST) $(TESTS_BASE_DIR)/unit
# $(PYTEST) tests -m unittest

.PHONY: test-integration
test-integration: ## Run integration tests
	$(PYTEST) $(TESTS_BASE_DIR)/integration
# $(PYTEST) tests -m integration

.PHONY: check
check: check-py-ruff-format check-py-ruff-lint check-notes ## Run all checks

.PHONY: check-py-ruff-lint
check-py-ruff-lint: ## Run ruff linter
	$(RUFF) $(RUFF_OPTS) check $(RUFF_CHECK_OPTS) $(MODULE_BASE_DIR) $(TESTS_BASE_DIR) || \
		(echo "$(COLOR_RED)Run '$(notdir $(MAKE)) check-py-ruff-fix' to fix some of these automatically if [*] appears above, then run '$(notdir $(MAKE)) $(MAKECMDGOALS)' again." && false)

.PHONY: check-py-ruff-fix
check-py-ruff-fix: ## Run ruff linter with automatic fixes
	$(MAKE) check-py-ruff-lint "RUFF_CHECK_OPTS=--fix $(RUFF_CHECK_OPTS)"

.PHONY: check-py-ruff-format
check-py-ruff-format: ## Runs ruff code formatter
	$(RUFF) $(RUFF_OPTS) format --check $(RUFF_FORMAT_OPTS) . || \
	  (echo "$(COLOR_RED)Run '$(notdir $(MAKE)) format-py' to fix, then run '$(notdir $(MAKE)) $(MAKECMDGOALS)' again." && false)

# this keeps check-notes/todo from finding its own code!
COLON = :
NOTES_GREP_OPTS = -n -I --break --threads=0
.PHONY: check-notes
check-notes: ## Look for FIXME and XXX comments and count TODOs
	@echo "$(COLOR_RESET)==> $(COLOR_BLUE)TODOs - address some day… run check-todo to show.$(COLOR_RESET)"
	@git grep -c $(NOTES_GREP_OPTS) "^.*TODO$(COLON)" || true
	@echo "$(COLOR_RESET)==> $(COLOR_ORANGE)FIXMEs - address soon:$(COLOR_RESET)"
	@git grep $(NOTES_GREP_OPTS) "^.*FIXME$(COLON)" || true
	@echo "$(COLOR_RESET)==> $(COLOR_RED)XXXs - address before merging!$(COLOR_RESET)"
	@git grep $(NOTES_GREP_OPTS) --untracked "^.*XXX$(COLON)" || true

.PHONY: check-todo
check-todo: ## Look for TODO comments
	@echo "$(COLOR_RESET)==> $(COLOR_BLUE)TODOs - address some day…$(COLOR_RESET)"
	@git grep $(NOTES_GREP_OPTS) "^.*TODO$(COLON)" || true

BUILD_DIR ?= build
DIST_DIR ?= dist
REPORTS_DIR = $(BUILD_DIR)/reports
MYPY_OPTS ?= --show-column-numbers --pretty --html-report $(REPORTS_DIR)/mypy
.PHONY: check-py-mypy
check-py-mypy: ## Run MyPy typechecker
	$(MYPY) $(MYPY_OPTS) $(MODULE_BASE_DIR) $(TESTS_BASE_DIR)

.PHONY: check-py-mypy-ignores
check-py-mypy-ignores: ## Look for "type: ignore" comments
	@echo "$(COLOR_RESET)==> $(COLOR_BLUE)type: ignore - address some day…$(COLOR_RESET)"
	@git grep $(NOTES_GREP_OPTS) "# type: ignore" -- ':!*Makefile' || true

.PHONY: check-precommit
check-precommit: ## Runs pre-commit on all files
	$(PRECOMMIT) run $(PRECOMMIT_OPTS) --all-files

.PHONY: format-py
format-py: ## Runs formatter, makes changes where necessary
	$(RUFF) format $(RUFF_FORMAT_OPTS) .

##@ Building

.PHONY: build
build: clean-dist poetry-build ## Build an artifact

##@ Manual Setup

.PHONY: install-homebrew
install-homebrew: ## Install Homebrew
	curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash -

# file(s) written by pre-commit setup
GIT_HOOKS = .git/hooks/pre-commit
.PHONY: install-precommit
install-precommit: $(GIT_HOOKS) ## Sets up pre-commit hooks
	@echo "$(COLOR_GREEN)Pre-commit configured, will run on future commits!$(COLOR_RESET)"
	@echo "==> If you must disable one or more pre-commit checks for a commit, run 'SKIP=\$$hook_id,\$$hook_id git commit'."
	@echo "==> If you must disable all pre-commit checks for a commit, run 'git commit --no-verify'."
	@echo '==> "Leave the campsite better than you found it."'

.PHONY: git-tag-testing
git-tag-testing: ## Create a test git tag for development
	git tag -f test-tag HEAD

$(GIT_HOOKS): .pre-commit-config.yaml
	(git rev-parse --is-inside-work-tree > /dev/null 2>&1 && $(PRECOMMIT) install) || ( \
		echo "$(COLOR_ORANGE)pre-commit was $(COLOR_BOLD)not actually installed$(COLOR_NORMAL) because you're not in a git repo." && \
		echo "$(COLOR_RED)Run 'make git-tag-testing' if you're testing, or use this from a git repo.")

.PHONY: deps-reqs-versions
deps-reqs-versions: ## Check if shell $PATH has requirements and show their version
	@echo "$(COLOR_BLUE)Checking PATH elements for evidence of required tools. The first in each section is what's used.$(COLOR_RESET)"
	@$(MAKE) paths-version-for-cmd CMD=poetry
	@$(MAKE) paths-version-for-cmd CMD=pyenv
	@$(MAKE) paths-version-for-cmd CMD=brew
	@$(MAKE) paths-version-for-cmd CMD=curl
	@$(MAKE) paths-version-for-cmd CMD=git
	@$(MAKE) paths-version-for-cmd CMD=pre-commit
	@echo "$(COLOR_GREEN)All expected PATH elements found$(COLOR_RESET)"

CMD_VERSION_FLAG ?= --version
WHICH ?= which
.PHONY: paths-version-for-cmd
paths-version-for-cmd: ## Display version for all executable paths for an executable, set CMD & CMD_VERSION_FLAG
	@( if [ -z "$$(which -a $(CMD))" ]; then \
		 echo "==> $(COLOR_RED)missing $(CMD)$(COLOR_RESET)"; \
	   else \
		 echo "==> $(COLOR_ORANGE)$(CMD) $(COLOR_BLUE)commands' versions are:$(COLOR_RESET)"; \
		 for pth in $$($(WHICH) -a $(CMD)); do \
			   echo "$(COLOR_BLUE)$${pth}$(COLOR_RESET) : $$("$${pth}" $(CMD_VERSION_FLAG))"; \
			 done; \
	   fi )


##@ Dependencies

.PHONY: python-current
python-current: ## Display the version and binary location of python3
	@echo CURRENT_PYTHON = $(shell which $(CURRENT_PYTHON))
	@$(CURRENT_PYTHON) --version
	@echo PYTHON_EXEC = $(PYTHON_EXEC)

.PHONY: install-poetry
install-poetry: ## Installs Poetry to the current Python environment
	@echo "$(COLOR_ORANGE)Running Poetry installer from python-poetry.org with [$(CURRENT_PYTHON) - $(OPTS)]$(COLOR_RESET)"
	curl -sSL https://install.python-poetry.org | $(CURRENT_PYTHON) - $(OPTS)

.PHONY: uninstall-poetry
uninstall-poetry: ## Uninstall Poetry forcefully, used for troubleshooting bugged installs
	$(MAKE) install-poetry OPTS=--uninstall

ifdef DEPS_NO_PRECOMMIT
DEPS_TASKS_PRECOMMIT = deps-precommit-warning
else
DEPS_TASKS_PRECOMMIT = install-precommit
endif

.PHONY: deps-precommit-warning
deps-precommit-warning:
	@echo "$(COLOR_ORANGE)pre-commit was not installed because its install is disabled presently.$(COLOR_RESET)"
	@echo "==> $(COLOR_ORANGE)Reenable it by unsetting DEPS_NO_PRECOMMIT as soon as possible for highest code quality.$(COLOR_RESET)"
	@echo "==> $(COLOR_ORANGE)Use 'git commit --no-verify' to disable pre-commit entirely for just one commit.$(COLOR_RESET)"

.PHONY: deps
deps: deps-brew deps-py $(DEPS_TASKS_PRECOMMIT) ## Installs all dependencies
	@echo "$(COLOR_GREEN)All deps installed!$(COLOR_RESET)"
.PHONY: deps-py
deps-py: install-python $(POETRY_TASK) poetry-use-pyenv poetry-install ## Install Python-based dependencies
	@echo "$(COLOR_GREEN)All Python deps installed!$(COLOR_RESET)"
.PHONY: deps-py-update
deps-py-update: poetry-update ## Update Poetry deps, e.g. after adding a new one manually
	@echo "$(COLOR_GREEN)All Python deps updated!$(COLOR_RESET)"

.PHONY: deps-py-upgrade-python
deps-py-upgrade-python: ## Run after upgrading Python version
	@echo "$(COLOR_ORANGE)Running deps twice with possible poetry-relock…$(COLOR_RESET)"
	$(MAKE) deps || $(MAKE) poetry-relock
	$(MAKE) deps
	@echo "$(COLOR_GREEN)Python version updated! Don't forget to run check and test.$(COLOR_RESET)"

COLOR_ORANGE = \033[33m
COLOR_BLUE = \033[34m
COLOR_RED = \033[31m
COLOR_GREEN = \033[32m
COLOR_RESET = \033[0m
COLOR_BOLD = \033[;1m
COLOR_NORMAL = \033[;0m

.PHONY: deps-brew
deps-brew: ## Installs development dependencies from Homebrew
	brew bundle install $(BREW_BUNDLE_OPTS) --verbose --file=Brewfile
	@test -n "$(PYENV_SHELL)" || ( \
		echo "$(COLOR_ORANGE)PYENV_SHELL is empty so pyenv may not be setup.$(COLOR_RESET)" && \
		echo "$(COLOR_ORANGE)Ensure that pyenv is setup in your shell config, e.g. in ~/.bashrc.$(COLOR_RESET)" && \
		echo "$(COLOR_ORANGE)It should have something like this:$(COLOR_RESET)" && \
		echo "$(COLOR_BLUE)\teval \"\$$(pyenv init --path)\"$(COLOR_RESET)" && \
		echo "$(COLOR_BLUE)\teval \"\$$(pyenv init -)\"$(COLOR_RESET)" && \
		echo "$(COLOR_BLUE)\teval \"\$$(pyenv virtualenv-init -)\"$(COLOR_RESET)" && \
		echo "$(COLOR_ORANGE)You may want to wrap them inside of a check for pyenv.$(COLOR_RESET)" \
    )
	@echo "$(COLOR_ORANGE)There may be formula caveats requiring action to activate.$(COLOR_RESET)" && \
		echo "$(COLOR_ORANGE)Please read the 'brew info <pkg>' for each package carefully.$(COLOR_RESET)"
	@command -v $(PYENV) > /dev/null || \
		echo "$(COLOR_RED)Run your make command again after adding the above so that $(PYENV) is available.$(COLOR_RESET)"

.PHONY: install-python
install-python: $(PYTHON_EXEC) ## Installs appropriate Python version
	@echo "$(COLOR_GREEN)Python installed to $(PYTHON_EXEC)$(COLOR_RESET)"

# Pyenv already automatically uses Homebrew's libraries if available on macOS
ifeq ($(shell uname -s), Darwin)
PYENV_FLAGS =
endif
# Force use of Homebrew's libraries in Linux
# Pyenv discourages this, preferring use of distro-provided libraries.
# We want to link against Homebrew for dev workstation use, but rely on
# distro Python in CI, which is why deps-ci doesn't install Python!
ifeq ($(shell uname -s), Linux)
PYENV_FLAGS = CFLAGS="$(shell pkg-config --cflags libffi ncurses readline)" \
		LDFLAGS="$(shell pkg-config --libs libffi ncurses readline)" \
		CC="$(firstword $(wildcard $(shell brew --prefix gcc)/bin/gcc-*))"
endif

$(PYTHON_EXEC): $(PYTHON_VERSION_FILE)
	@echo "$(COLOR_BLUE)Installing Pythons from $(PYTHON_VERSION_FILE) using $(PYENV):$(COLOR_ORANGE)"
	@grep ^[^\n#] $(PYTHON_VERSION_FILE) | sed -e 's/^/\t/'
	@echo "$(COLOR_RESET)"

	grep ^[^\n#] $(PYTHON_VERSION_FILE) | while read -r py ; do \
		$(PYENV_FLAGS) $(PYENV) install --verbose --skip-existing "$${py}" ; \
	done

##@ Poetry

.PHONY: poetry-install
poetry-install: ## Run poetry install with any environment-required flags
	$(POETRY) install

.PHONY: poetry-update
poetry-update: ## Run poetry update with any environment-required flags, pass PKGS=pkg to update only pkg
	time $(POETRY) update -v $(PKGS)

.PHONY: poetry-relock
poetry-relock: pyproject.toml ## Run poetry lock w/o updating deps, use after changing pyproject.toml trivially
	$(POETRY) lock

.PHONY: poetry-build
poetry-build: clean-dist ## Run poetry build with any environment-required flags
	$(POETRY) build

# For release builds, pass this e.g. ARTIFACT_VERSION=${CI_BUILD_TAG}
ifndef ARTIFACT_VERSION
ARTIFACT_VERSION = $(shell $(POETRY) version | cut -d ' ' -f 2)
endif
# For test builds, set TEST_VERSION. This tries to force PEP 440 resolvers to choose the newer test version.
TEST_VERSION ?= 1
ifndef ARTIFACT_TEST_VERSION
ARTIFACT_TEST_VERSION = $(shell git describe --tags | awk -F '-' '{print $$1 ".post" $$2 ".dev$(TEST_VERSION)" "+" $$3 "-$(shell whoami)" }')
endif


EXPORTED_REQUIREMENTS_TXT = $(DIST_DIR)/requirements.txt

.PHONY: poetry-export
poetry-export: $(EXPORTED_REQUIREMENTS_TXT) ## Export a requirements.txt for use with pip
	@echo "$(COLOR_GREEN)Dependencies exported.$(COLOR_RESET)"

$(EXPORTED_REQUIREMENTS_TXT): poetry.lock pyproject.toml
	@mkdir -p $(DIST_DIR)
	$(POETRY) export --verbose --format requirements.txt --output "$@"

.PHONY: poetry-debug
poetry-debug: ## Shows Poetry debug include any envvars passed to Poetry
	@echo POETRY=$(POETRY)
	$(POETRY) debug

.PHONY: poetry-use-pyenv
poetry-use-pyenv: $(PYTHON_VERSION_FILE) ## Configure Poetry to use the expected base Python for its virtualenv
	@echo "$(COLOR_BLUE)Configuring Poetry to use $(PYTHON_EXEC) for its virtualenv$(COLOR_RESET)"
	$(POETRY) env use $(PYTHON_EXEC)

.PHONY: poetry-implode-venv
poetry-implode-venv: ## Destroys the Poetry-managed virtualenv
	sleep 2 && rm -rf $$($(POETRY) env info --path)

.PHONY: poetry-venv-path
poetry-venv-path: ## Shows the path to the currently active Poetry-managed virtualenv
	@$(POETRY) env list --full-path | grep Activated | cut -f 1 -d ' '

.PHONY: fix-poetry-conflicts
fix-poetry-conflicts: ## Attempts to fix Poetry merge/rebase conflicts by choosing theirs and locking again
	git checkout --theirs poetry.lock
	$(MAKE) poetry-relock

.PHONY: fix-poetry-conflicts-2
fix-poetry-conflicts-2: ## Another way to try to fix Poetry merge/rebase conflicts
	git restore --staged --worktree poetry.lock
	$(MAKE) poetry-relock

##@ Docker tasks for getting started

.PHONY: install-colima
install-colima: ## Install Colima for Docker with Target configuration
	brew tap --verbose | grep 'tgt\/brewhouse' || brew tap tgt/brewhouse git@git.target.com:brew/house.git
	brew install tgt-docker_helper_scripts
	tgt-install-colima.sh

.PHONY: colima-minimum
colima-minimum: ## Starts a Colima VM with minimum resources necessary
	colima start --cpu 2 --memory 4 --arch x86_64 --disk 80

.PHONY: colima-force-reset
colima-force-reset: ## Forcibly reset Colima by stopping and removing the VM. Warning: this will destroy unpushed containers.
	@echo "$(COLOR_ORANGE)This will delete your Colima VM. You'll lose any containers on it. Continuing in 10 seconds… or hit Ctrl+C to abort$(COLOR_RESET)"
	sleep 10
	colima stop || true
	@echo "$(COLOR_ORANGE)Last chance to Ctrl+C to abort, waiting 5 seconds…$(COLOR_RESET)"
	sleep 5
	limactl delete colima


DOCKER_BUILD_ENV ?= dev

DOCKER_AUTO_TAGS_USER ?= -$(shell whoami)
DOCKER_SAFE_ARTIFACT_VERSION ?= $(shell echo $(ARTIFACT_VERSION) | tr '+' '_')$(DOCKER_AUTO_TAGS_USER)


##@ Documentation
DOCS_DIR = $(DIST_DIR)/docs
DOCS_INDEX = $(DOCS_DIR)/index.html
ALL_PY_FILES = $(shell git ls-files '*.py')

.PHONY: docs
docs: $(DOCS_INDEX) ## Build API documentation

$(DOCS_INDEX): $(ALL_PY_FILES)
	$(PDOC) $(PDOC_OPTS) $(MODULE_BASE_DIR) -o $(DOCS_DIR)

##@ Miscellaneous

.PHONY: all
all:

.PHONY: clean-dist
clean-dist: ## Clean poetry dist artifacts
	rm -rf $(DIST_DIR)/*.whl $(DIST_DIR)/*.tar.gz

.PHONY: clean-build
clean-build: ## Clean artifacts from build directories
	rm -rf $(BUILD_DIR)

.PHONY: clean
clean: clean-dist clean-build ## Clean artifacts from build and dist directories
