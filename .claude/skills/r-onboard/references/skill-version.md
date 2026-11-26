# Version of the skill collection

Tell the owner these two things in the reply of step 12 of `r-onboard`, before the last item.

1. A line `ref: <tag>` under that `git:` line in `apm.yml` pins the version of the collection.
2. To take a newer version, the owner or the agent does these steps in order:
   1. Set `ref` to the new tag.
   2. Run `make skills-update`.
   3. Run `make toon` and `make links`.
   4. Run the gates.
   5. Commit `.claude/skills/`, `apm.yml`, and `apm.lock.yaml` together.
