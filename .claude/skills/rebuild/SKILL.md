---
name: rebuild
description: Update the current branch, clear bin, rebuild the standalone app and launch it, using rebuild_and_launch.py.
disable-model-invocation: true
allowed-tools: Bash(./rebuild_and_launch.py)
---

Run `./rebuild_and_launch.py` from the root of the current checkout, with a Bash timeout of 600000 ms. Run it once, in the foreground.

If the file doesn't exist on the current branch, say so and stop.

Then report in a few lines:

- the branch that was built;
- whether the script warned about uncommitted changes or about not reaching GitHub;
- whether the app was built and launched.

If the script stopped, quote its error and say what it needs from the user. Don't retry it, change branches, or try to resolve a diverged branch without being asked.
