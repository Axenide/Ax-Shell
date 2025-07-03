#!/bin/bash

# Get exit code
uwsm check is-active

if [[ $? == 0 ]]; then
	systemctl --user restart ax-shell.service
else
	killall ax-shell
	$HOME/.local/bin/ax-shell
fi
