# The list that `make help` prints. project.mk and the sdlc.mk of
# r-github-pipeline both include this file, and the recipe of their
# help target runs $(HELP_LIST). Every project therefore shows the same
# groups in the same order.
#
# HELP_LIST reads $(MAKEFILE_LIST) with awk. It lists each target that
# has a ## comment, and the first definition of a target wins. The line
# `# help-group: <Name>` in a makefile puts the targets that follow it,
# up to the next marker, in that group. The first line of each file
# starts in the group Project, so a target of the product Makefile
# lands there. HELP_GROUPS is the order of the groups. A group that
# HELP_GROUPS does not name prints after them, in the order it appears.
# A group with no target prints no heading.
#
# `# help-docs` and `# help-login` hide the target that follows when
# RENDER_DOCS or PUBLISH_IMAGE is not 1. An `endif` line ends the hiding.
#
# The awk is POSIX awk, so it runs on the awk of macOS and of Debian. In
# a Make variable a # is written \# and a shell $ is $$.
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef HELP_MK
HELP_MK := 1

HELP_GROUPS ?= Gates Project Board Delivery Tools

HELP_LIST ?= awk -v docs="$(RENDER_DOCS)" -v login="$(PUBLISH_IMAGE)" -v groups="$(HELP_GROUPS)" \
	'BEGIN { FS = ":.*\#\# "; fixed_count = split(groups, fixed, " ") } \
	FNR == 1 { group = "Project"; skip = 0 } \
	/^\# help-group: / { group = substr($$0, 15); sub(/ +$$/, "", group); next } \
	/^\# help-docs$$/ { skip = (docs != "1"); next } \
	/^\# help-login$$/ { skip = (login != "1"); next } \
	/^endif$$/ { skip = 0; next } \
	skip { next } \
	/^[a-zA-Z][a-zA-Z0-9_-]*:.*\#\# / && !seen[$$1]++ { \
	  if (!(group in known)) { known[group] = 1; seen_count++; seen_group[seen_count] = group } \
	  rows[group]++; line[group, rows[group]] = sprintf("  %-32s %s", $$1, $$2) } \
	END { \
	  for (i = 1; i <= fixed_count; i++) order[++total] = fixed[i]; \
	  for (i = 1; i <= seen_count; i++) order[++total] = seen_group[i]; \
	  for (i = 1; i <= total; i++) { \
	    name = order[i]; \
	    if (printed[name] || !rows[name]) continue; \
	    printed[name] = 1; print ""; print name ":"; \
	    for (j = 1; j <= rows[name]; j++) print line[name, j] \
	  } \
	}' $(MAKEFILE_LIST)

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
