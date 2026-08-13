#!/bin/sh
set -eu
envsubst '${FOCUS_API_BASE} ${FOCUS_AUTH_MODE} ${FOCUS_ENTRA_CLIENT_ID} ${FOCUS_ENTRA_TENANT_ID} ${FOCUS_ENTRA_API_SCOPE}' < /usr/share/nginx/html/config.js.template > /usr/share/nginx/html/config.js
envsubst '${API_INTERNAL_SCHEME} ${API_INTERNAL_HOST}' < /etc/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
exec /docker-entrypoint.sh nginx -g 'daemon off;'
